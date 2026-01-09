"""
CodingAgent Streaming Models

Models for WebSocket streaming and cancellation support.
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StreamEventType(str, Enum):
    """Types of streaming events from agents."""

    STARTED = "started"
    THINKING = "thinking"
    GENERATING_CODE = "generating_code"
    EXECUTING = "executing"
    ITERATION_COMPLETE = "iteration_complete"
    AGENT_SWITCH = "agent_switch"
    ERROR = "error"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    CLARIFICATION_REQUIRED = "clarification_required"


class StreamEvent(BaseModel):
    """
    Streaming event sent over WebSocket.

    Used for real-time updates during agent execution.
    """

    type: str = "status"  # "status", "completed", "error", "cancelled"
    event_type: StreamEventType | None = None
    agent_name: str
    message: str
    data: dict[str, Any] | None = None
    iteration: int | None = None
    total_iterations: int | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CancellationToken:
    """
    Cooperative cancellation token for async operations.

    Allows cancelling long-running agent operations mid-stream.

    Usage:
        token = CancellationToken()

        # In WebSocket handler
        async for event in orchestrator.process_query_stream(..., token):
            if token.is_cancelled:
                break
            await websocket.send_json(event.model_dump())

        # When client sends cancel
        token.cancel()
    """

    def __init__(self):
        self._event = asyncio.Event()

    def cancel(self) -> None:
        """Signal cancellation."""
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._event.is_set()

    def reset(self) -> None:
        """Reset the token for reuse."""
        self._event.clear()


# WebSocket message types for type hints
class WSQueryMessage(BaseModel):
    """Client query message."""

    type: str = "query"
    query: str
    conversation_id: str | None = None
    file_id: str | None = None
    connection_id: str | None = None
    skip_visualization: bool = False
    theme: str | None = None


class WSCancelMessage(BaseModel):
    """Client cancel message."""

    type: str = "cancel"


class WSErrorResponse(BaseModel):
    """Error response message."""

    type: str = "error"
    message: str
    code: str | None = None
