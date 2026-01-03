"""
Rule dependency graph for targeted revalidation.

This module enables smart impact detection for modification submissions (V1+),
reducing unnecessary revalidation by analyzing which rules are actually affected
by field changes.
"""

from typing import Dict, List, Set, Optional
import logging

LOGGER = logging.getLogger(__name__)


class RuleDependencyGraph:
    """
    Manages rule dependencies for intelligent impact analysis.

    Enables targeted revalidation by understanding which rules depend on which fields
    and how rule failures cascade to other rules.
    """

    def __init__(self, rule_catalog: List[Dict]):
        """
        Initialize dependency graph from rule catalog.

        Args:
            rule_catalog: List of rule dictionaries from rule_catalog.json
        """
        self.rules = {r["rule_id"]: r for r in rule_catalog}
        self._build_graph()

    def _build_graph(self):
        """Build bidirectional dependency graph from rule catalog."""
        self.forward_deps = {}  # rule_id -> [dependent_rule_ids]
        self.backward_deps = {}  # rule_id -> [triggering_rule_ids]

        for rule_id, rule in self.rules.items():
            # Forward dependencies (this rule triggers these rules)
            self.forward_deps[rule_id] = rule.get("triggers_rules", [])

            # Backward dependencies (this rule is triggered by these rules)
            for triggered_rule in rule.get("triggers_rules", []):
                if triggered_rule not in self.backward_deps:
                    self.backward_deps[triggered_rule] = []
                self.backward_deps[triggered_rule].append(rule_id)

    def get_impacted_rules(
        self,
        changed_fields: List[str],
        significance_threshold: float = 0.3
    ) -> Set[str]:
        """
        Get all rules impacted by field changes, including cascading dependencies.

        This implements smart impact detection:
        1. Find rules that directly depend on changed fields
        2. Filter by impact level (critical/high/medium/low)
        3. Cascade to rules triggered by impacted rules

        Args:
            changed_fields: List of field names that changed (e.g., ["site_address", "proposed_height"])
            significance_threshold: Minimum impact score to trigger revalidation (0.0-1.0)

        Returns:
            Set of rule IDs that need revalidation

        Example:
            >>> graph = RuleDependencyGraph(rule_catalog)
            >>> impacted = graph.get_impacted_rules(["site_address"], 0.3)
            >>> # Returns: {"PROX_001", "SETBACK_001", "CONSTRAINT_ZONE_001"}
        """
        impacted = set()
        to_process = []

        # Step 1: Find directly impacted rules
        for rule_id, rule in self.rules.items():
            for field in changed_fields:
                dependent_fields = rule.get("dependent_fields", {})

                # Check if this field is a dependency for this rule
                if field in dependent_fields:
                    impact_level = dependent_fields[field].get("impact_level", "low")
                    impact_score = self._impact_level_to_score(impact_level)

                    if impact_score >= significance_threshold:
                        impacted.add(rule_id)
                        to_process.append(rule_id)
                        LOGGER.info(
                            f"Rule {rule_id} impacted by {field} change "
                            f"(level: {impact_level}, score: {impact_score})"
                        )

                # Also check legacy required_fields for backward compatibility
                elif field in rule.get("required_fields", []):
                    # Default to medium impact if not in dependent_fields
                    if 0.5 >= significance_threshold:
                        impacted.add(rule_id)
                        to_process.append(rule_id)
                        LOGGER.info(
                            f"Rule {rule_id} impacted by {field} change "
                            f"(legacy required_fields match)"
                        )

        # Step 2: Cascade to dependent rules (BFS traversal)
        visited = set()
        while to_process:
            current_rule = to_process.pop(0)
            if current_rule in visited:
                continue
            visited.add(current_rule)

            # Add rules triggered by this rule
            for triggered_rule in self.forward_deps.get(current_rule, []):
                if triggered_rule not in impacted:
                    impacted.add(triggered_rule)
                    to_process.append(triggered_rule)
                    LOGGER.info(f"Rule {triggered_rule} cascaded from {current_rule}")

        return impacted

    @staticmethod
    def _impact_level_to_score(level: str) -> float:
        """
        Convert impact level string to numeric score.

        Args:
            level: Impact level (critical/high/medium/low)

        Returns:
            Numeric score between 0.0 and 1.0
        """
        return {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.5,
            "low": 0.2
        }.get(level, 0.2)

    def get_rule_dependencies(self, rule_id: str) -> Dict[str, any]:
        """
        Get complete dependency information for a specific rule.

        Args:
            rule_id: Rule ID to analyze

        Returns:
            Dictionary with forward deps, backward deps, and impact fields
        """
        if rule_id not in self.rules:
            return {}

        rule = self.rules[rule_id]
        return {
            "rule_id": rule_id,
            "triggers_rules": self.forward_deps.get(rule_id, []),
            "triggered_by_rules": self.backward_deps.get(rule_id, []),
            "dependent_fields": rule.get("dependent_fields", {}),
            "required_fields": rule.get("required_fields", [])
        }

    def visualize_dependencies(self, rule_id: str, depth: int = 2) -> str:
        """
        Generate a text visualization of rule dependencies.

        Args:
            rule_id: Root rule ID
            depth: How many levels deep to traverse

        Returns:
            ASCII tree visualization
        """
        lines = []
        self._visualize_recursive(rule_id, 0, depth, lines, set())
        return "\n".join(lines)

    def _visualize_recursive(
        self,
        rule_id: str,
        current_depth: int,
        max_depth: int,
        lines: List[str],
        visited: Set[str]
    ):
        """Recursive helper for visualize_dependencies."""
        if current_depth > max_depth or rule_id in visited:
            return

        visited.add(rule_id)
        indent = "  " * current_depth
        lines.append(f"{indent}{rule_id}")

        # Show triggered rules
        for triggered in self.forward_deps.get(rule_id, []):
            self._visualize_recursive(triggered, current_depth + 1, max_depth, lines, visited)
