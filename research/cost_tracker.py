"""Azure OpenAI cost tracking and budget enforcement.

Tracks token usage and estimated costs across the research pipeline,
enforcing a configurable budget limit to prevent runaway spending.

Pricing (Azure OpenAI, pay-as-you-go, as of 2025):
  GPT-4o:                  $2.50 / 1M input tokens,  $10.00 / 1M output tokens
  text-embedding-3-small:  $0.02 / 1M tokens
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default pricing per 1M tokens (USD)
PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
}

DEFAULT_BUDGET_USD = 10.00  # $10 default budget


class BudgetExceededError(Exception):
    """Raised when the cost budget is exceeded."""

    def __init__(self, spent: float, budget: float):
        self.spent = spent
        self.budget = budget
        super().__init__(
            f"Budget exceeded: ${spent:.2f} spent of ${budget:.2f} limit. "
            f"Increase RESEARCH_BUDGET_USD in .env or config to continue."
        )


@dataclass
class UsageRecord:
    """A single API call's token usage."""

    timestamp: float
    model: str
    operation: str  # e.g. "vision_extraction", "graphrag_entity", "embedding"
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class CostTracker:
    """Tracks cumulative Azure OpenAI costs across the pipeline.

    Usage:
        tracker = CostTracker(budget_usd=10.0)
        tracker.record("gpt-4o", "vision_extraction", input_tokens=1500, output_tokens=800)
        tracker.check_budget()  # raises BudgetExceededError if over budget
        print(tracker.summary())
    """

    budget_usd: float = DEFAULT_BUDGET_USD
    records: list[UsageRecord] = field(default_factory=list)
    _state_path: Optional[str] = None

    def __post_init__(self):
        # Load budget from env if set
        env_budget = os.environ.get("RESEARCH_BUDGET_USD")
        if env_budget:
            try:
                self.budget_usd = float(env_budget)
            except ValueError:
                pass

        # Set default state path
        if self._state_path is None:
            from research.config import ResearchConfig
            cfg = ResearchConfig()
            self._state_path = os.path.join(cfg.output_dir, "cost_tracker.json")

        # Resume from saved state
        self._load_state()

    def record(
        self,
        model: str,
        operation: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> float:
        """Record token usage from an API call. Returns estimated cost in USD."""
        cost = self._estimate_cost(model, input_tokens, output_tokens)

        rec = UsageRecord(
            timestamp=time.time(),
            model=model,
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )
        self.records.append(rec)

        logger.debug(
            "Cost: $%.4f (%s, %s, %d in / %d out tokens). Total: $%.4f / $%.2f",
            cost, model, operation, input_tokens, output_tokens,
            self.total_cost, self.budget_usd,
        )

        # Auto-save after each record
        self._save_state()

        return cost

    def record_from_response(self, response, model: str, operation: str) -> float:
        """Record usage directly from an OpenAI API response object."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return 0.0
        return self.record(
            model=model,
            operation=operation,
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0),
        )

    def check_budget(self) -> None:
        """Raise BudgetExceededError if total cost exceeds budget."""
        if self.total_cost > self.budget_usd:
            raise BudgetExceededError(self.total_cost, self.budget_usd)

    @property
    def total_cost(self) -> float:
        """Total estimated cost in USD."""
        return sum(r.cost_usd for r in self.records)

    @property
    def total_input_tokens(self) -> int:
        return sum(r.input_tokens for r in self.records)

    @property
    def total_output_tokens(self) -> int:
        return sum(r.output_tokens for r in self.records)

    @property
    def remaining_budget(self) -> float:
        return max(0.0, self.budget_usd - self.total_cost)

    def summary(self) -> dict:
        """Return a cost summary breakdown by operation."""
        by_operation: dict[str, dict] = {}
        for r in self.records:
            if r.operation not in by_operation:
                by_operation[r.operation] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                }
            entry = by_operation[r.operation]
            entry["calls"] += 1
            entry["input_tokens"] += r.input_tokens
            entry["output_tokens"] += r.output_tokens
            entry["cost_usd"] += r.cost_usd

        return {
            "budget_usd": self.budget_usd,
            "total_cost_usd": round(self.total_cost, 4),
            "remaining_usd": round(self.remaining_budget, 4),
            "total_calls": len(self.records),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "by_operation": {
                k: {kk: round(vv, 4) if isinstance(vv, float) else vv for kk, vv in v.items()}
                for k, v in by_operation.items()
            },
        }

    def print_summary(self) -> None:
        """Print a formatted cost summary to the logger."""
        s = self.summary()
        logger.info("=" * 50)
        logger.info("COST SUMMARY")
        logger.info("=" * 50)
        logger.info("Budget:    $%.2f", s["budget_usd"])
        logger.info("Spent:     $%.4f", s["total_cost_usd"])
        logger.info("Remaining: $%.4f", s["remaining_usd"])
        logger.info("API calls: %d", s["total_calls"])
        logger.info("Tokens:    %d input, %d output",
                     s["total_input_tokens"], s["total_output_tokens"])
        for op, data in s["by_operation"].items():
            logger.info(
                "  %-25s %d calls, $%.4f",
                op, data["calls"], data["cost_usd"],
            )
        logger.info("=" * 50)

    def _estimate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimate cost in USD for a given model and token counts."""
        model_key = model.lower()
        # Match model key (handle deployment names like "gpt-4o")
        pricing = None
        for key in PRICING:
            if key in model_key:
                pricing = PRICING[key]
                break

        if pricing is None:
            # Unknown model — use GPT-4o pricing as safe upper bound
            logger.warning("Unknown model '%s', using GPT-4o pricing", model)
            pricing = PRICING["gpt-4o"]

        cost = (
            (input_tokens / 1_000_000) * pricing["input"]
            + (output_tokens / 1_000_000) * pricing["output"]
        )
        return cost

    def _save_state(self) -> None:
        """Persist tracker state to disk for resumability."""
        if not self._state_path:
            return
        try:
            os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
            data = {
                "budget_usd": self.budget_usd,
                "records": [asdict(r) for r in self.records],
            }
            with open(self._state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save cost tracker state: %s", e)

    def _load_state(self) -> None:
        """Load previous tracker state from disk."""
        if not self._state_path or not os.path.exists(self._state_path):
            return
        try:
            with open(self._state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.records = [UsageRecord(**r) for r in data.get("records", [])]
            if self.records:
                logger.info(
                    "Resumed cost tracker: $%.4f spent across %d calls",
                    self.total_cost, len(self.records),
                )
        except Exception as e:
            logger.warning("Failed to load cost tracker state: %s", e)

    def reset(self) -> None:
        """Reset all tracked usage (useful for new experiments)."""
        self.records.clear()
        self._save_state()
        logger.info("Cost tracker reset")
