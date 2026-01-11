"""
Query processing API with Server-Sent Events (SSE) streaming.
"""

from uuid import UUID

from app.core.deps import CurrentActiveUser
from app.db.pool import get_system_db
from app.db.session_db import SessionRepository
from app.services.agent_orchestrator import AgentOrchestrator
from app.shared.logging import get_logger
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["query"])

session_repo = SessionRepository()


@router.post("/sessions/{session_id}/query")
async def process_query(
    session_id: UUID,
    current_user: CurrentActiveUser,
    request: Request,
):
    """
    Process a user query with streaming response.

    Uses Server-Sent Events (SSE) for real-time updates.
    """
    # Verify session ownership
    async with get_system_db() as conn:
        session = await session_repo.get_session(conn, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session["user_id"] != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

    body = await request.json()
    user_query = body.get("query")
    file_ids = body.get("file_ids", [])
    model = body.get("model")

    if not user_query:
        raise HTTPException(status_code=400, detail="Query is required")

    # Validate custom model prefix
    if model and not model.startswith("openrouter/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid model format. Custom models must start with 'openrouter/'",
        )

    # Convert file_ids to UUIDs
    file_uuid_list = [UUID(fid) for fid in file_ids] if file_ids else None

    orchestrator = AgentOrchestrator(model=model)

    async def event_generator():
        async for event in orchestrator.process_query(
            session_id=session_id,
            user_query=user_query,
            file_ids=file_uuid_list,
        ):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
