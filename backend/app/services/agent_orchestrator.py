"""
Agent Orchestrator

Coordinates agent execution with workspace, session state, and artifact management.
"""

from io import BytesIO
from typing import Any, AsyncGenerator
from uuid import UUID

import pandas as pd
from app.agents.data_analysis_agent import DataAnalysisAgent
from app.db.pool import get_system_db
from app.db.session_db import ArtifactRepository, MessageRepository, SessionRepository
from app.services.session_state_service import SessionStateService
from app.services.workspace_service import WorkspaceService
from app.services.workspace_tools import create_workspace_tools
from app.shared.logging import get_logger
from app.shared.models import AgentStatus, AgentStatusType
from app.shared.stream_models import StreamEvent, StreamEventType, TypedDataKind

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

    def __init__(self, model: str | None = None):
        self.workspace_service = WorkspaceService()
        self.session_state = SessionStateService()
        self.artifact_repo = ArtifactRepository()
        self.message_repo = MessageRepository()
        self.session_repo = SessionRepository()
        self.model = model

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

            # Get project_id for this session to enable shared artifacts
            # We'll need this for workspace tools
            project_id = None
            async with get_system_db() as conn:
                session = await self.session_repo.get_session(conn, session_id)
                if session and session.get("project_id"):
                    project_id = session["project_id"]

            # Add project files to workspace_files so they appear in context
            if project_id:
                project_files = await self.workspace_service.list_project_files(
                    project_id
                )
                workspace_files.extend(project_files)

            # Load DataFrames for relevant files
            dataframes = await self._load_dataframes(session_id, file_ids)

            # Initialize agent
            agent = DataAnalysisAgent(model=self.model)

            # Create workspace tools for this session (with project context)
            workspace_tools = create_workspace_tools(
                session_id, self.workspace_service, project_id=project_id
            )

            # Execute with streaming
            final_result = None
            async for status in agent.execute_with_workspace(
                user_prompt=user_query,
                session_id=str(session_id),
                workspace_files=workspace_files,
                dataframes=dataframes,
                workspace_tools=workspace_tools,
            ):
                # Track final result
                if status.status_type == AgentStatusType.COMPLETED:
                    final_result = status.data
                    # Don't yield agent completion; we'll yield an enriched one at the end
                    continue

                # Convert AgentStatus to StreamEvent
                yield self._status_to_event(status)

            # Capture any new artifacts created
            new_artifacts = await self._capture_new_artifacts(
                session_id, workspace_files
            )

            # Get usage stats from agent
            usage_stats = agent.get_usage_stats()

            # Save to chat history
            user_msg = None
            async with get_system_db() as conn:
                user_msg = await self.message_repo.add_message(
                    conn=conn,
                    session_id=session_id,
                    role="user",
                    content=user_query,
                )
                # Ensure content is always a string for database storage
                result_content = ""
                if final_result:
                    result_value = final_result.get("result", "")
                    if isinstance(result_value, (dict, list)):
                        import json

                        try:
                            result_content = json.dumps(
                                result_value, indent=2, default=str
                            )
                        except Exception:
                            result_content = str(result_value)
                    elif result_value is not None:
                        result_content = str(result_value)

                # Serialize iterations for storage in metadata
                serialized_iterations = None
                try:
                    if final_result and final_result.get("code_history"):
                        # We need to process iterations to ensure 'output' is in TypedData format
                        # similar to how we do in _status_to_event
                        processed_iterations = []
                        for iter_data in final_result["code_history"]:
                            # Create a copy to avoid modifying original
                            processed_iter = iter_data.copy()

                            # Serialize output to TypedData
                            if "output" in processed_iter:
                                processed_iter["output"] = (
                                    self._serialize_to_typed_data(
                                        processed_iter["output"]
                                    )
                                )

                            # Serialize final_result to TypedData (user-defined answer)
                            if (
                                "final_result" in processed_iter
                                and processed_iter["final_result"] is not None
                            ):
                                processed_iter["final_result"] = (
                                    self._serialize_to_typed_data(
                                        processed_iter["final_result"]
                                    )
                                )

                            processed_iterations.append(processed_iter)

                        serialized_iterations = self._serialize_data(
                            processed_iterations
                        )
                except Exception as e:
                    logger.error(f"Failed to serialize iterations for metadata: {e}")
                    # Continue without iterations in metadata to ensures message is still saved
                    serialized_iterations = None

                await self.message_repo.add_message(
                    conn=conn,
                    session_id=session_id,
                    role="assistant",
                    content=result_content,
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
                    metadata=(
                        {
                            "iterations": serialized_iterations,
                            "usage": usage_stats,
                        }
                        if serialized_iterations
                        else {"usage": usage_stats}
                    ),
                )

            # Prepare final data
            response_data = {
                "artifact_ids": [str(a["artifact_id"]) for a in new_artifacts],
                "artifacts": [],
                "usage": usage_stats,
                "user_created_at": (
                    user_msg["created_at"].isoformat() if user_msg else None
                ),
            }

            # Generate presigned URLs for new artifacts
            for artifact in new_artifacts:
                try:
                    url = await self.workspace_service.get_presigned_url(
                        session_id=session_id,
                        file_name=artifact["file_name"],
                    )
                    response_data["artifacts"].append(
                        {
                            "artifact_id": str(artifact["artifact_id"]),
                            "file_name": artifact["file_name"],
                            "file_type": artifact["file_type"],
                            "url": url,
                        }
                    )
                except Exception as e:
                    logger.warning(
                        "failed_to_generate_presigned_url",
                        artifact_id=str(artifact["artifact_id"]),
                        error=str(e),
                    )

            if final_result:
                # Extract the actual result (answer/dataframe) and serialize it
                # distinct from the full internal state
                response_data["result"] = self._serialize_data(
                    final_result.get("result")
                )
                response_data["code_history"] = self._serialize_data(
                    final_result.get("code_history")
                )
                response_data["iterations"] = self._serialize_data(
                    final_result.get("iterations")
                )

            yield StreamEvent(
                type="completed",
                event_type=StreamEventType.COMPLETED,
                agent_name="data_analysis",
                message="Analysis complete",
                data=response_data,
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

        event_type = event_type_map.get(status.status_type, StreamEventType.THINKING)

        # Serialize data
        serialized_data = None
        if status.data:
            # If it's an iteration complete event, we want to structure it as IterationOutput
            if status.status_type == AgentStatusType.ITERATION_COMPLETE:
                # The data from base agent currently has {success, output, final_answer, etc}
                # We need to ensure 'output' is typed
                raw_output = status.data.get("output")
                typed_output = self._serialize_to_typed_data(raw_output)

                # Serialize final_result if present (user-defined direct answer)
                raw_final_result = status.data.get("final_result")
                typed_final_result = (
                    self._serialize_to_typed_data(raw_final_result)
                    if raw_final_result is not None
                    else None
                )

                # Copy other fields
                serialized_data = {
                    "iteration": status.iteration,
                    "thought": status.data.get("thought"),
                    "code": status.data.get("code"),
                    "execution_logs": status.data.get("execution_logs"),
                    "output": typed_output,
                    "final_result": typed_final_result,  # User-defined direct answer
                    "success": status.data.get("success", False),
                    "error": status.data.get("error"),
                    "final_answer": status.data.get("final_answer", False),
                }
            else:
                # For other events, use legacy serialization or pass through if simple
                serialized_data = self._serialize_data(status.data)

        return StreamEvent(
            type=(
                "status"
                if status.status_type != AgentStatusType.COMPLETED
                else "completed"
            ),
            event_type=event_type,
            agent_name="data_analysis",
            message=status.message,
            data=serialized_data,
            iteration=status.iteration,
            total_iterations=status.total_iterations,
        )

    def _serialize_to_typed_data(self, data: Any) -> dict | None:
        """
        Serialize data to TypedData format for frontend rendering.

        Wraps raw data with type metadata (kind=table, image, etc).
        """
        if data is None:
            return None

        # Return if already serialized as typed data
        if isinstance(data, dict) and "kind" in data and "data" in data:
            return data

        # Handle tuples/lists containing multiple DataFrames or mixed types
        # e.g., (df1, df2)
        if isinstance(data, (tuple, list)) and len(data) > 0:
            # Check if any item is a DataFrame - if so, serialize as MULTI
            has_dataframe = any(isinstance(item, pd.DataFrame) for item in data)
            if has_dataframe:
                items = []
                for idx, item in enumerate(data):
                    serialized_item = self._serialize_to_typed_data(item)
                    if serialized_item:
                        # Add index metadata for frontend display
                        if "metadata" not in serialized_item:
                            serialized_item["metadata"] = {}
                        serialized_item["metadata"]["index"] = idx
                        items.append(serialized_item)
                return {
                    "kind": TypedDataKind.MULTI,
                    "data": items,
                    "metadata": {
                        "count": len(items),
                        "original_type": type(data).__name__,
                    },
                }

        # Handle dicts containing DataFrames as values
        # e.g., {'sex_survival': df1, 'sex_age_survival': df2}
        if isinstance(data, dict) and len(data) > 0:
            # Check if any value is a DataFrame - if so, serialize as MULTI with named items
            has_dataframe = any(isinstance(v, pd.DataFrame) for v in data.values())
            if has_dataframe:
                items = []
                for idx, (key, value) in enumerate(data.items()):
                    serialized_item = self._serialize_to_typed_data(value)
                    if serialized_item:
                        # Add key name and index metadata for frontend display
                        if "metadata" not in serialized_item:
                            serialized_item["metadata"] = {}
                        serialized_item["metadata"]["index"] = idx
                        serialized_item["metadata"]["name"] = str(key)
                        items.append(serialized_item)
                return {
                    "kind": TypedDataKind.MULTI,
                    "data": items,
                    "metadata": {
                        "count": len(items),
                        "original_type": "dict",
                        "has_names": True,
                    },
                }

        # Handle Pandas DataFrames -> Table
        if isinstance(data, pd.DataFrame):
            # Limit rows for performance if needed, but for now send full
            # Frontend handles pagination/rendering
            return {
                "kind": TypedDataKind.TABLE,
                "data": {
                    "headers": list(data.columns),
                    "rows": data.astype(object).fillna("").values.tolist(),
                },
                "metadata": {
                    "rows": len(data),
                    "columns": len(data.columns),
                    "dtypes": {str(k): str(v) for k, v in data.dtypes.items()},
                },
            }

        # Handle Matplotlib Figure (from legacy internal state or fresh)
        if hasattr(data, "savefig") or (
            isinstance(data, dict)
            and data.get("type") == "matplotlib_figure"
            and "data" in data
        ):
            # If it's already our dict format
            if isinstance(data, dict):
                return {
                    "kind": TypedDataKind.IMAGE,
                    "data": data["data"],  # base64 string
                    "metadata": {"format": "png"},
                }

            # If it's a live figure object (should be caught by agent before here, but safety)
            # This part mirrors base_agent logic but wraps in TypedData
            try:
                import base64

                buf = BytesIO()
                data.savefig(buf, format="png", bbox_inches="tight")
                buf.seek(0)
                img_base64 = base64.b64encode(buf.read()).decode("utf-8")
                buf.close()
                return {
                    "kind": TypedDataKind.IMAGE,
                    "data": img_base64,
                    "metadata": {"format": "png"},
                }
            except Exception:
                pass

        # Handle Pandas Series -> Table (Index, Value)
        if isinstance(data, pd.Series):
            return {
                "kind": TypedDataKind.TABLE,
                "data": {
                    "headers": ["Index", data.name or "Value"],
                    "rows": [[i, v] for i, v in zip(data.index, data.values)],
                },
                "metadata": {
                    "rows": len(data),
                    "columns": 2,
                    "dtypes": {
                        "Index": str(data.index.dtype),
                        "Value": str(data.dtype),
                    },
                },
            }

        # Handle Plotly Figure
        # Check specifically for to_plotly_json to avoid matching pandas objects
        if hasattr(data, "to_plotly_json") or (
            isinstance(data, dict) and data.get("type") == "plotly_figure"
        ):
            if isinstance(data, dict):
                return {
                    "kind": TypedDataKind.PLOTLY,
                    "data": data["data"],
                    "metadata": {},
                }

            # If live object
            try:
                return {
                    "kind": TypedDataKind.PLOTLY,
                    "data": data.to_plotly_json(),
                    "metadata": {},
                }
            except Exception:
                pass

        # Handle basic types -> Text
        if isinstance(data, (str, int, float, bool)):
            return {
                "kind": TypedDataKind.TEXT,
                "data": str(data),
                "metadata": {},
            }

        # Handle dict/list -> JSON
        if isinstance(data, (dict, list)):
            # Recursively serialize contents if needed, but for JSON view just dump
            return {
                "kind": TypedDataKind.JSON,
                "data": self._serialize_data(data),  # Use existing recursive cleaner
                "metadata": {},
            }

        # Fallback -> Text
        return {
            "kind": TypedDataKind.TEXT,
            "data": str(data),
            "metadata": {"original_type": type(data).__name__},
        }

    def _serialize_data(self, data: Any) -> Any:
        """
        Recursively serialize data to ensure JSON compatibility.

        Handles:
        - pandas.DataFrame -> dict (orient='split')
        - PrintContainer -> string value
        - litellm response objects -> dict/string
        - Pydantic models -> dict
        - Functions/callables -> string representation
        """
        if data is None:
            return None

        # Handle basic JSON-serializable types first
        if isinstance(data, (str, int, float, bool)):
            return data

        # Get type name early for type-based checks
        type_name = type(data).__name__

        # Debug logging for DataFrames
        if "DataFrame" in type_name or isinstance(data, pd.DataFrame):
            logger.info(
                f"Serializing potential DataFrame: {type_name}, isinstance={isinstance(data, pd.DataFrame)}"
            )

        # Handle pandas DataFrame and Series EARLY (before callable check)
        # DataFrames/Series must be caught before other checks
        if type_name == "DataFrame" or isinstance(data, pd.DataFrame):
            try:
                # Kept for backward compatibility but wrapped in TypedData usually preferable
                return data.to_dict(orient="records")
            except Exception:
                return str(data)

        if type_name == "Series":
            try:
                return data.to_list()
            except Exception:
                return str(data)

        # Handle callables (functions, lambdas, methods) EARLY - before dict/list recursion
        # This prevents functions from being passed through to Pydantic
        if callable(data):
            func_name = getattr(data, "__name__", None) or type_name
            return f"<function {func_name}>"

        # Handle PrintContainer from smolagents executor (check before hasattr on 'logs')
        # Use specific duck typing that won't trigger property accessors
        type_name = type(data).__name__
        if type_name == "PrintContainer":
            return str(data)

        # Handle litellm response objects by type name (avoid importing litellm types)
        if type_name in (
            "ModelResponse",
            "Message",
            "Choices",
            "StreamingChoices",
            "Delta",
        ):
            # Convert to dict if possible, otherwise string
            if hasattr(data, "model_dump"):
                try:
                    return data.model_dump()
                except Exception:
                    pass
            if hasattr(data, "dict"):
                try:
                    return data.dict()
                except Exception:
                    pass
            # Fallback to string representation
            return str(data)

        # Handle Pydantic models (have model_dump method)
        if hasattr(data, "model_dump") and callable(getattr(data, "model_dump")):
            try:
                return self._serialize_data(data.model_dump())
            except Exception:
                return str(data)

        # Handle dicts recursively
        if isinstance(data, dict):
            return {k: self._serialize_data(v) for k, v in data.items()}

        # Handle lists recursively
        if isinstance(data, list):
            return [self._serialize_data(item) for item in data]

        # Handle tuples recursively
        if isinstance(data, tuple):
            return tuple(self._serialize_data(item) for item in data)

        # Handle numpy arrays
        if hasattr(data, "tolist") and type_name == "ndarray":
            try:
                return data.tolist()
            except Exception:
                return str(data)

        # Fallback: try to convert to string for unknown types
        try:
            # Check if it's a known simple type that json can handle
            import json

            json.dumps(data)
            return data
        except (TypeError, ValueError):
            # Not JSON serializable, convert to string
            return str(data)
