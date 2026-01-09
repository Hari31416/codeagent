"""
CodingAgent LLM Service

Unified LLM interface using LiteLLM with robust error handling,
JSON parsing/fixing, and usage tracking.
"""

import json
import re
from typing import Any, AsyncGenerator

import structlog
from litellm import acompletion, completion_cost
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = structlog.get_logger(__name__)


class LLMService:
    """
    LLM service wrapper using LiteLLM.

    Provides:
    - Unified interface for multiple LLM providers
    - Robust JSON parsing with auto-fixing and retries
    - Usage tracking (tokens, cost estimation)
    - Error handling with exponential backoff
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        """
        Initialize LLM service.

        Args:
            model: Model name (e.g., 'gpt-4o-mini', 'claude-3-5-sonnet-20241022')
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
        """
        self.model = model or settings.llm_model
        self.temperature = temperature or settings.llm_temperature
        self.max_tokens = max_tokens or settings.llm_max_tokens

        # Usage tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.call_count = 0

    async def simple_call(
        self,
        messages: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
        json_mode: bool = False,
        temperature: float | None = None,
        max_retries: int = 3,
    ) -> str | dict[str, Any]:
        """
        Make a simple LLM call with optional JSON mode.

        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}]
            system_prompt: System prompt (alternative to messages)
            user_prompt: User prompt (alternative to messages)
            json_mode: If True, force JSON response and validate
            temperature: Override default temperature
            max_retries: Number of retry attempts for JSON parsing

        Returns:
            String response or parsed JSON dict

        Raises:
            ValueError: If neither messages nor system/user prompts provided
            Exception: If LLM call fails after retries
        """
        # Build messages list
        if messages is None:
            if system_prompt is None or user_prompt is None:
                raise ValueError(
                    "Either 'messages' or both 'system_prompt' and 'user_prompt' must be provided"
                )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

        temp = temperature if temperature is not None else self.temperature

        # Call LLM with retry logic
        response_text = await self._call_with_retry(
            messages=messages,
            temperature=temp,
            json_mode=json_mode,
        )

        # Parse JSON if needed
        if json_mode:
            parsed = self._parse_json_response(response_text, max_retries=max_retries)
            if parsed is None:
                # If still can't parse after fixing, try one more LLM call with error feedback
                logger.warning(
                    "Failed to parse JSON after fixing, retrying with error feedback"
                )
                error_message = {
                    "role": "user",
                    "content": f"Your previous response was not valid JSON. Please return ONLY valid JSON without any markdown formatting or explanations.\n\nYour previous response:\n{response_text}",
                }
                # Create a new list for retry to avoid mutating the original
                retry_messages = messages + [error_message]
                response_text = await self._call_with_retry(
                    messages=retry_messages,
                    temperature=0.0,  # Use temperature 0 for retry
                    json_mode=json_mode,
                )
                parsed = self._parse_json_response(response_text, max_retries=1)
                if parsed is None:
                    raise ValueError(
                        f"Failed to get valid JSON response after retries: {response_text}"
                    )
            return parsed

        return response_text

    @retry(
        retry=retry_if_exception_type((Exception,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _call_with_retry(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        json_mode: bool = False,
    ) -> str:
        """
        Call LLM with automatic retries on failure.

        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            json_mode: If True, use JSON response format

        Returns:
            Response text from LLM
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.max_tokens,
        }

        # Add JSON mode if supported by the model
        if json_mode:
            # For OpenAI models
            if "gpt" in self.model.lower():
                kwargs["response_format"] = {"type": "json_object"}
            # For others, add instruction to system message
            elif messages and messages[0]["role"] == "system":
                # Create a deep copy of messages to avoid mutation
                messages = [m.copy() for m in messages]
                messages[0][
                    "content"
                ] += "\n\nYou MUST respond with valid JSON only. Do not include any markdown formatting or explanations."
                kwargs["messages"] = messages
            else:
                # Create a deep copy of messages to avoid mutation
                messages = [m.copy() for m in messages]
                messages.insert(
                    0,
                    {
                        "role": "system",
                        "content": "You MUST respond with valid JSON only. Do not include any markdown formatting or explanations.",
                    },
                )
                kwargs["messages"] = messages

        try:
            response = await acompletion(**kwargs)

            # Track usage
            self._track_usage(response)

            # Extract response text
            content = response.choices[0].message.content

            logger.info(
                "LLM call successful",
                model=self.model,
                input_tokens=(
                    response.usage.prompt_tokens if hasattr(response, "usage") else 0
                ),
                output_tokens=(
                    response.usage.completion_tokens
                    if hasattr(response, "usage")
                    else 0
                ),
            )

            return content

        except Exception as e:
            logger.error(
                "LLM call failed",
                model=self.model,
                error=str(e),
                exc_info=True,
            )
            raise

    async def streaming_call(
        self,
        messages: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
        temperature: float | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Make a streaming LLM call.

        Args:
            messages: List of message dicts
            system_prompt: System prompt (alternative to messages)
            user_prompt: User prompt (alternative to messages)
            temperature: Override default temperature

        Yields:
            Response chunks as they arrive
        """
        # Build messages list
        if messages is None:
            if system_prompt is None or user_prompt is None:
                raise ValueError(
                    "Either 'messages' or both 'system_prompt' and 'user_prompt' must be provided"
                )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

        temp = temperature if temperature is not None else self.temperature

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": self.max_tokens,
            "stream": True,
        }

        try:
            response = await acompletion(**kwargs)

            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            logger.info("Streaming LLM call completed", model=self.model)

        except Exception as e:
            logger.error(
                "Streaming LLM call failed",
                model=self.model,
                error=str(e),
                exc_info=True,
            )
            raise

    def _parse_json_response(
        self,
        response_text: str,
        max_retries: int = 3,
    ) -> dict[str, Any] | None:
        """
        Parse JSON response with automatic fixing attempts.

        Args:
            response_text: Raw response text from LLM
            max_retries: Number of fix attempts

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        # Try direct parsing first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code blocks
        extracted = self._extract_json_from_markdown(response_text)
        if extracted:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                response_text = extracted  # Use extracted text for fixing attempts

        # Try fixing common JSON errors
        for attempt in range(max_retries):
            fixed = self._fix_json(response_text)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError as e:
                logger.debug(
                    "JSON fix attempt failed",
                    attempt=attempt + 1,
                    error=str(e),
                )
                response_text = fixed  # Use previous fix for next attempt

        logger.error("Failed to parse JSON after all attempts", response=response_text)
        return None

    def _extract_json_from_markdown(self, text: str) -> str | None:
        """
        Extract JSON from markdown code blocks.

        Args:
            text: Text that may contain markdown-wrapped JSON

        Returns:
            Extracted JSON string or None
        """
        # Match ```json ... ``` or ``` ... ```
        patterns = [
            r"```json\s*\n(.*?)\n```",
            r"```\s*\n(.*?)\n```",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()

        return None

    def _fix_json(self, text: str) -> str:
        """
        Attempt to fix common JSON errors.

        Args:
            text: Potentially malformed JSON string

        Returns:
            Fixed JSON string
        """
        # Remove trailing commas before closing brackets/braces
        text = re.sub(r",\s*([}\]])", r"\1", text)
        # Remove any leading/trailing whitespace
        text = text.strip()

        # Try to find the JSON object boundaries if embedded in text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

        return text

    def _track_usage(self, response: Any) -> None:
        """
        Track token usage and cost from LLM response.

        Args:
            response: LiteLLM response object
        """
        if not hasattr(response, "usage"):
            return

        usage = response.usage
        self.total_input_tokens += usage.prompt_tokens
        self.total_output_tokens += usage.completion_tokens
        self.call_count += 1

        # Estimate cost
        try:
            cost = completion_cost(completion_response=response)
            if cost:
                self.total_cost += cost
        except Exception as e:
            logger.debug("Failed to calculate cost", error=str(e))

    def get_usage_stats(self) -> dict[str, Any]:
        """
        Get current usage statistics.

        Returns:
            Dict with token counts, cost, and call count
        """
        return {
            "model": self.model,
            "call_count": self.call_count,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "estimated_cost_usd": round(self.total_cost, 6),
        }

    def reset_usage_stats(self) -> None:
        """Reset usage tracking counters."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.call_count = 0


async def log_llm_usage(
    user_id: str,
    agent_name: str | None,
    model_name: str,
    operation: str,
    input_tokens: int,
    output_tokens: int,
    estimated_cost: float | None = None,
) -> None:
    """
    Log LLM usage to the database for cost monitoring and analytics.

    Args:
        user_id: User UUID as string
        agent_name: Name of the agent (e.g., 'dba', 'analyst', 'librarian')
        model_name: LLM model name used
        operation: Description of the operation (e.g., 'query_processing')
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        estimated_cost: Estimated cost in USD (optional)
    """
    from uuid import UUID

    from app.db.pool import get_system_db

    try:
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        async with get_system_db() as conn:
            await conn.execute(
                """
                INSERT INTO llm_usage_logs (
                    user_id, agent_name, model_name, operation,
                    input_tokens, output_tokens, estimated_cost
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                user_uuid,
                agent_name,
                model_name,
                operation,
                input_tokens,
                output_tokens,
                estimated_cost,
            )
        logger.debug(
            "LLM usage logged",
            user_id=user_id,
            agent=agent_name,
            tokens=input_tokens + output_tokens,
        )
    except Exception as e:
        # Don't fail the main operation if logging fails
        logger.warning("Failed to log LLM usage", error=str(e))
