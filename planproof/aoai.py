"""
Azure OpenAI wrapper for LLM-based resolution and validation.
"""

from typing import List, Dict, Any, Optional

import openai

AzureOpenAI = openai.AzureOpenAI
from openai.types.chat import ChatCompletion

from planproof.config import get_settings


class AzureOpenAIClient:
    """Wrapper around Azure OpenAI for LLM operations."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        deployment: Optional[str] = None
    ):
        """Initialize Azure OpenAI client."""
        settings = get_settings()
        endpoint = endpoint or settings.azure_openai_endpoint
        api_key = api_key or settings.azure_openai_api_key
        api_version = api_version or settings.azure_openai_api_version
        deployment = deployment or settings.azure_openai_chat_deployment

        self.client = openai.AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        self.deployment = deployment
        self._call_count = 0  # Track LLM calls for metrics

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatCompletion:
        """
        Create a chat completion.

        Args:
            messages: List of message dictionaries with "role" and "content"
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the API call

        Returns:
            ChatCompletion response
        """
        self._call_count += 1
        return self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    def get_call_count(self) -> int:
        """Get the current LLM call count for this client instance."""
        return self._call_count
    
    def reset_call_count(self):
        """Reset the LLM call counter (useful for per-run tracking)."""
        self._call_count = 0

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
