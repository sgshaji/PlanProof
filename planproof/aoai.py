"""
Azure OpenAI wrapper for LLM-based resolution and validation.
"""

from typing import List, Dict, Any, Optional
import logging
import time
from datetime import datetime, timezone

import openai
from openai import APIError, APITimeoutError, RateLimitError, APIConnectionError

AzureOpenAI = openai.AzureOpenAI
from openai.types.chat import ChatCompletion

from planproof.config import get_settings

LOGGER = logging.getLogger(__name__)


class AzureOpenAIClient:
    """Wrapper around Azure OpenAI for LLM operations."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        deployment: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        """Initialize Azure OpenAI client.

        Args:
            endpoint: Azure OpenAI endpoint URL
            api_key: Azure OpenAI API key
            api_version: API version to use
            deployment: Deployment name for chat completions
            timeout: Timeout in seconds for API calls (default: 60.0)
        """
        settings = get_settings()
        endpoint = endpoint or settings.azure_openai_endpoint
        api_key = api_key or settings.azure_openai_api_key
        api_version = api_version or settings.azure_openai_api_version
        deployment = deployment or settings.azure_openai_chat_deployment

        self.client = openai.AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
            timeout=timeout or 60.0  # Default 60 second timeout
        )
        self.deployment = deployment
        self.timeout = timeout or 60.0
        self._call_count = 0  # Track LLM calls for metrics
        self._last_call_metadata: Optional[Dict[str, Any]] = None
        self._call_history: List[Dict[str, Any]] = []

        # Cost tracking
        self.total_tokens = 0
        self.total_cost = 0.0
        # GPT-4 pricing (adjust based on actual model)
        # https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/
        self.cost_per_1k_tokens = 0.03  # $0.03 per 1K tokens (GPT-4 average)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatCompletion:
        """
        Create a chat completion with proper error handling and cost tracking.

        Args:
            messages: List of message dictionaries with "role" and "content"
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the API call

        Returns:
            ChatCompletion response

        Raises:
            RuntimeError: If API call fails after retries or times out
        """
        self._call_count += 1
        call_started_at = time.monotonic()
        call_timestamp = datetime.now(timezone.utc).isoformat()

        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            # Track tokens and cost
            response_time_ms = int((time.monotonic() - call_started_at) * 1000)
            tokens_used = 0
            if hasattr(response, 'usage') and response.usage:
                tokens_used = response.usage.total_tokens or 0
                cost = (tokens_used / 1000) * self.cost_per_1k_tokens

                self.total_tokens += tokens_used
                self.total_cost += cost

                LOGGER.info(
                    f"LLM call #{self._call_count}: {tokens_used} tokens, "
                    f"${cost:.4f} (total: ${self.total_cost:.4f})"
                )

                # Budget alert threshold: $5.00
                if self.total_cost > 5.0:
                    LOGGER.warning(
                        f"⚠️  LLM cost exceeded ${self.total_cost:.2f}! "
                        f"Consider reducing calls or checking for runaway usage."
                    )

            call_metadata = {
                "timestamp": call_timestamp,
                "tokens_used": tokens_used,
                "model": getattr(response, "model", None) or self.deployment,
                "response_time_ms": response_time_ms,
            }
            self._last_call_metadata = call_metadata
            self._call_history.append(call_metadata)

            return response

        except APITimeoutError as e:
            error_msg = f"Azure OpenAI API timeout after {self.timeout}s: {str(e)}"
            LOGGER.error(error_msg)
            raise RuntimeError(error_msg) from e
        except RateLimitError as e:
            error_msg = f"Azure OpenAI rate limit exceeded: {str(e)}"
            LOGGER.error(error_msg)
            raise RuntimeError(error_msg) from e
        except APIConnectionError as e:
            error_msg = f"Azure OpenAI connection error: {str(e)}"
            LOGGER.error(error_msg)
            raise RuntimeError(error_msg) from e
        except APIError as e:
            error_msg = f"Azure OpenAI API error: {str(e)}"
            LOGGER.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error calling Azure OpenAI: {str(e)}"
            LOGGER.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
    
    def get_call_count(self) -> int:
        """Get the current LLM call count for this client instance."""
        return self._call_count
    
    def reset_call_count(self):
        """Reset the LLM call counter and cost tracking (useful for per-run tracking)."""
        self._call_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self._last_call_metadata = None
        self._call_history = []

    def get_last_call_metadata(self) -> Optional[Dict[str, Any]]:
        """Get metadata for the most recent LLM call."""
        return self._last_call_metadata

    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get metadata for all LLM calls on this client."""
        return list(self._call_history)

    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive cost and usage summary.

        Returns:
            Dictionary with cost metrics including:
            - total_calls: Number of LLM calls made
            - total_tokens: Total tokens used
            - total_cost_usd: Total cost in USD
            - avg_tokens_per_call: Average tokens per call
            - cost_per_call: Average cost per call
        """
        avg_tokens = self.total_tokens / max(self._call_count, 1)
        avg_cost = self.total_cost / max(self._call_count, 1)

        return {
            "total_calls": self._call_count,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 4),
            "avg_tokens_per_call": round(avg_tokens, 2),
            "cost_per_call_usd": round(avg_cost, 4),
            "budget_threshold_usd": 5.00,
            "budget_remaining_usd": round(5.00 - self.total_cost, 2),
            "over_budget": self.total_cost > 5.00
        }

    def resolve_field_conflict(
        self,
        field_name: str,
        extracted_value: str,
        context: str,
        validation_issue: str
    ) -> Dict[str, Any]:
        """
        Use LLM to resolve a field conflict or missing value.

        Args:
            field_name: Name of the field being validated
            extracted_value: Value that was extracted (may be None or conflicting)
            context: Relevant context from the document
            validation_issue: Description of the validation issue

        Returns:
            Dictionary with:
            - resolved_value: The resolved value
            - confidence: Confidence score (0.0 to 1.0)
            - reasoning: Explanation of why this value was chosen
        """
        system_prompt = """You are a planning validation assistant. Your task is to resolve field extraction conflicts or missing values by analyzing document context.

Provide a JSON response with:
- resolved_value: The best value for the field (or null if truly not found)
- confidence: A confidence score between 0.0 and 1.0
- reasoning: A brief explanation of your decision

Be precise and only extract information that is clearly present in the document."""

        user_prompt = f"""Field: {field_name}
Extracted value: {extracted_value or "NOT FOUND"}
Validation issue: {validation_issue}

Document context:
{context}

Please resolve this field and provide your reasoning."""

        response = self.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,  # Lower temperature for more deterministic results
            response_format={"type": "json_object"}  # Request JSON response
        )

        # Parse the response
        content = response.choices[0].message.content
        import json as jsonlib
        try:
            result = jsonlib.loads(content)
            return {
                "resolved_value": result.get("resolved_value"),
                "confidence": float(result.get("confidence", 0.5)),
                "reasoning": result.get("reasoning", "")
            }
        except jsonlib.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "resolved_value": content.strip() if content else None,
                "confidence": 0.5,
                "reasoning": "LLM response could not be parsed as JSON"
            }

    def validate_with_llm(
        self,
        field_name: str,
        extracted_value: Any,
        validation_rules: str,
        document_context: str
    ) -> Dict[str, Any]:
        """
        Use LLM to validate a field against rules when deterministic validation is insufficient.

        Args:
            field_name: Name of the field
            extracted_value: Value that was extracted
            validation_rules: Description of validation rules
            document_context: Relevant document context

        Returns:
            Dictionary with:
            - is_valid: Boolean indicating if validation passed
            - confidence: Confidence score
            - reasoning: Explanation
            - suggested_value: Optional corrected value
        """
        system_prompt = """You are a planning validation assistant. Validate extracted fields against planning requirements.

Provide a JSON response with:
- is_valid: Boolean indicating if the field passes validation
- confidence: Confidence score between 0.0 and 1.0
- reasoning: Explanation of the validation result
- suggested_value: Optional corrected value if validation fails but a correction is possible"""

        user_prompt = f"""Field: {field_name}
Extracted value: {extracted_value}

Validation rules:
{validation_rules}

Document context:
{document_context}

Please validate this field and provide your assessment."""

        response = self.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        import json as jsonlib
        try:
            result = jsonlib.loads(content)
            return {
                "is_valid": result.get("is_valid", False),
                "confidence": float(result.get("confidence", 0.5)),
                "reasoning": result.get("reasoning", ""),
                "suggested_value": result.get("suggested_value")
            }
        except jsonlib.JSONDecodeError:
            return {
                "is_valid": False,
                "confidence": 0.3,
                "reasoning": "LLM response could not be parsed",
                "suggested_value": None
            }

    def chat_json(self, payload: dict) -> dict:
        """
        Call AOAI with a JSON-structured prompt and return parsed JSON response.

        Args:
            payload: Dictionary containing the task/request to send to LLM

        Returns:
            Parsed JSON dictionary from LLM response
        """
        system_prompt = """You are a planning validation assistant. Analyze the provided task and return a valid JSON response following the specified schema.

Be precise and only extract information that is clearly present in the evidence provided."""

        import json as jsonlib
        user_prompt = jsonlib.dumps(payload, indent=2)

        response = self.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        import json as jsonlib
        try:
            return jsonlib.loads(content)
        except jsonlib.JSONDecodeError:
            return {
                "error": "LLM response could not be parsed as JSON",
                "raw_response": content
            }

    def chat_json_with_metadata(self, payload: dict) -> Dict[str, Any]:
        """
        Call AOAI with a JSON-structured prompt and return parsed JSON with metadata.

        Args:
            payload: Dictionary containing the task/request to send to LLM

        Returns:
            Dictionary with parsed response data and call metadata.
        """
        system_prompt = """You are a planning validation assistant. Analyze the provided task and return a valid JSON response following the specified schema.

Be precise and only extract information that is clearly present in the evidence provided."""

        import json as jsonlib
        user_prompt = jsonlib.dumps(payload, indent=2)

        response = self.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        try:
            parsed = jsonlib.loads(content)
        except jsonlib.JSONDecodeError:
            parsed = {
                "error": "LLM response could not be parsed as JSON",
                "raw_response": content
            }

        return {
            "data": parsed,
            "metadata": self.get_last_call_metadata()
        }
