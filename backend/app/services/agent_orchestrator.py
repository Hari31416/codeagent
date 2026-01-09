"""
Agent Orchestrator

Coordinates agent execution with workspace, session state, and artifact management.
"""

from io import BytesIO
from typing import AsyncGenerator
from uuid import UUID

import pandas as pd
from app.agents.data_analysis_agent import DataAnalysisAgent
from app.db.pool import get_system_db
from app.db.session_db import ArtifactRepository, MessageRepository
from app.services.session_state_service import SessionStateService
from app.services.workspace_service import WorkspaceService
from app.shared.logging import get_logger
from app.shared.models import AgentStatus, AgentStatusType
from app.shared.stream_models import StreamEvent, StreamEventType

logger = get_logger(__name__)


class AgentOrchestrator:
    """
    Orchestrates the full agent execution flow:

    1. Acquire session lock
    2. Load workspace files
    3. Execute agent with ReAct loop
    4. Capture output artifacts
    5. Save chat history
    6. Release lock
    """

    def __init__(self):
        self.workspace_service = WorkspaceService()
        self.session_state = SessionStateService()
        self.artifact_repo = ArtifactRepository()
        self.message_repo = MessageRepository()

    async def process_query(
        self,
        session_id: UUID,
        user_query: str,
        file_ids: list[UUID] | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Process a user query through the agent pipeline.

        Yields StreamEvents for real-time frontend updates.
        """
        # Check if session is busy
        if not await self.session_state.acquire_lock(session_id):
            yield StreamEvent(
                type="error",
                event_type=StreamEventType.ERROR,
                agent_name="orchestrator",
                message="Session is currently busy. Please wait.",
            )
            return

        try:
            # Yield started event
            yield StreamEvent(
                type="status",
                event_type=StreamEventType.STARTED,
                agent_name="data_analysis",
                message="Processing your request...",
            )

            # Load workspace files
            workspace_files = await self.workspace_service.list_workspace_files(
                session_id
            )

            # Load DataFrames for relevant files
            dataframes = await self._load_dataframes(session_id, file_ids)

            # Initialize agent
            agent = DataAnalysisAgent()

            # Execute with streaming
            final_result = None
            async for status in agent.execute_with_workspace(
                user_prompt=user_query,
                session_id=str(session_id),
                workspace_files=workspace_files,
                dataframes=dataframes,
            ):
                # Convert AgentStatus to StreamEvent
                yield self._status_to_event(status)

                # Track final result
                if status.status_type == AgentStatusType.COMPLETED:
                    final_result = status.data

            # Capture any new artifacts created
            new_artifacts = await self._capture_new_artifacts(
                session_id, workspace_files
            )

            # Save to chat history
            async with get_system_db() as conn:
                await self.message_repo.add_message(
                    conn=conn,
                    session_id=session_id,
                    role="user",
                    content=user_query,
                )
                await self.message_repo.add_message(
                    conn=conn,
                    session_id=session_id,
                    role="assistant",
                    content=final_result.get("result", "") if final_result else "",
                    code=(
                        final_result["code_history"][-1]["code"]
                        if final_result and final_result.get("code_history")
                        else None
                    ),
                    thoughts=(
                        final_result["code_history"][-1]["thoughts"]
                        if final_result and final_result.get("code_history")
                        else None
                    ),
                    artifact_ids=[a["artifact_id"] for a in new_artifacts],
                )

            # Yield completion with artifact IDs
            yield StreamEvent(
                type="completed",
                event_type=StreamEventType.COMPLETED,
                agent_name="data_analysis",
                message="Analysis complete",
                data={
                    "result": final_result,
                    "artifact_ids": [str(a["artifact_id"]) for a in new_artifacts],
                },
            )

        except Exception as e:
            logger.error(
                "agent_execution_failed",
                session_id=str(session_id),
                error=str(e),
                exc_info=True,
            )
            yield StreamEvent(
                type="error",
                event_type=StreamEventType.ERROR,
                agent_name="orchestrator",
                message=f"Error: {str(e)}",
            )

        finally:
            await self.session_state.release_lock(session_id)

    async def _load_dataframes(
        self,
        session_id: UUID,
        file_ids: list[UUID] | None,
    ) -> dict[str, pd.DataFrame]:
        """Load relevant files as DataFrames."""
        dataframes = {}

        if not file_ids:
            return dataframes

        # Get artifact info
        async with get_system_db() as conn:
            # Load CSV files as DataFrames
            for file_id in file_ids:
                artifact = await self.artifact_repo.get_artifact(conn, file_id)
                if artifact and artifact["file_type"] in ("csv", "xlsx", "xls"):
                    try:
                        file_content = await self.workspace_service.download_file(
                            session_id=session_id,
                            file_name=artifact["file_name"],
                        )
                        if artifact["file_type"] == "csv":
                            df = pd.read_csv(BytesIO(file_content))
                        else:
                            df = pd.read_excel(BytesIO(file_content))

                        # Use clean name as variable
                        var_name = artifact["file_name"].rsplit(".", 1)[0]
                        var_name = "df" if not var_name else var_name.replace(" ", "_")
                        dataframes[var_name] = df

                    except Exception as e:
                        logger.warning(
                            "failed_to_load_dataframe",
                            file_id=str(file_id),
                            error=str(e),
                        )

        return dataframes

    async def _capture_new_artifacts(
        self,
        session_id: UUID,
        original_files: list[dict],
    ) -> list[dict]:
        """Compare workspace files and register any new artifacts."""
        current_files = await self.workspace_service.list_workspace_files(session_id)
        original_names = {f["name"] for f in original_files}

        new_artifacts = []
        async with get_system_db() as conn:
            for file_info in current_files:
                if file_info["name"] not in original_names:
                    # New file created by agent
                    file_name = file_info["name"].split("/")[-1]
                    artifact = await self.artifact_repo.create_artifact(
                        conn=conn,
                        session_id=session_id,
                        file_name=file_name,
                        file_type=(
                            file_name.rsplit(".", 1)[-1]
                            if "." in file_name
                            else "unknown"
                        ),
                        mime_type="application/octet-stream",
                        size_bytes=file_info.get("size", 0),
                        minio_object_key=file_info["name"],
                    )
                    new_artifacts.append(artifact)

        return new_artifacts

    def _status_to_event(self, status: AgentStatus) -> StreamEvent:
        """Convert AgentStatus to StreamEvent."""
        event_type_map = {
            AgentStatusType.STARTED: StreamEventType.STARTED,
            AgentStatusType.THINKING: StreamEventType.THINKING,
            AgentStatusType.GENERATING_CODE: StreamEventType.GENERATING_CODE,
            AgentStatusType.EXECUTING: StreamEventType.EXECUTING,
            AgentStatusType.ITERATION_COMPLETE: StreamEventType.ITERATION_COMPLETE,
            AgentStatusType.COMPLETED: StreamEventType.COMPLETED,
            AgentStatusType.ERROR: StreamEventType.ERROR,
        }
        return StreamEvent(
            type=(
                "status"
                if status.status_type != AgentStatusType.COMPLETED
                else "completed"
            ),
            event_type=event_type_map.get(status.status_type, StreamEventType.THINKING),
            agent_name="data_analysis",
            message=status.message,
            data=status.data,
            iteration=status.iteration,
            total_iterations=status.total_iterations,
        )
