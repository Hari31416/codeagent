"""
Export service for generating session and project exports.

Generates JSON metadata and structured markdown files with embedded artifacts.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from app.db.pool import get_system_db
from app.db.session_db import (
    ArtifactRepository,
    MessageRepository,
    ProjectRepository,
    SessionRepository,
)
from app.services.workspace_service import WorkspaceService
from app.shared.logging import get_logger
from pydantic import BaseModel

logger = get_logger(__name__)


class ExportResult(BaseModel):
    """Result of an export operation."""

    metadata_json: dict[str, Any]
    markdown_content: str
    session_count: int
    filename: str


class ExportService:
    """Service for exporting sessions and projects to JSON and markdown formats."""

    def __init__(self):
        self.message_repo = MessageRepository()
        self.session_repo = SessionRepository()
        self.project_repo = ProjectRepository()
        self.artifact_repo = ArtifactRepository()
        self.workspace_service = WorkspaceService()

    async def export_session(self, session_id: UUID) -> ExportResult:
        """
        Export a single session as JSON metadata and markdown.

        Args:
            session_id: UUID of the session to export

        Returns:
            ExportResult with metadata, markdown content, and filename
        """
        async with get_system_db() as conn:
            # Get session details
            session = await self.session_repo.get_session(conn, session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            # Get all messages for the session
            messages = await self.message_repo.get_messages_by_session(
                conn, session_id, limit=1000
            )

        # Build metadata
        metadata = {
            "session_id": str(session_id),
            "session_name": session["name"],
            "project_id": str(session["project_id"]),
            "created_at": session["created_at"].isoformat(),
            "updated_at": session["updated_at"].isoformat(),
            "exported_at": datetime.utcnow().isoformat(),
            "message_count": len(messages),
        }

        # Generate markdown content
        markdown = await self._generate_session_markdown(session, messages, session_id)

        # Create filename
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")
        safe_name = "".join(
            c if c.isalnum() or c in (" ", "_", "-") else "_" for c in session["name"]
        )
        filename = f"{safe_name}_{timestamp}.md"

        return ExportResult(
            metadata_json=metadata,
            markdown_content=markdown,
            session_count=1,
            filename=filename,
        )

    async def export_project(self, project_id: UUID) -> ExportResult:
        """
        Export all sessions in a project as JSON metadata and markdown.

        Args:
            project_id: UUID of the project to export

        Returns:
            ExportResult with metadata, markdown content, and filename
        """
        async with get_system_db() as conn:
            # Get project details
            project = await self.project_repo.get_project(conn, project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Get all sessions for the project
            sessions = await self.session_repo.list_sessions_by_project(
                conn, project_id, limit=1000
            )

        # Build metadata
        metadata = {
            "project_id": str(project_id),
            "project_name": project["name"],
            "project_description": project.get("description"),
            "created_at": project["created_at"].isoformat(),
            "updated_at": project["updated_at"].isoformat(),
            "exported_at": datetime.utcnow().isoformat(),
            "session_count": len(sessions),
            "sessions": [],
        }

        # Generate markdown for all sessions
        markdown_parts = [f"# Project Export: {project['name']}\n"]
        if project.get("description"):
            markdown_parts.append(f"\n{project['description']}\n")

        markdown_parts.append(f"\n**Exported:** {datetime.utcnow().isoformat()}")
        markdown_parts.append(f"\n**Sessions:** {len(sessions)}\n")
        markdown_parts.append("\n---\n")

        for session in sessions:
            session_id = session["session_id"]

            # Get messages for this session
            async with get_system_db() as conn:
                messages = await self.message_repo.get_messages_by_session(
                    conn, session_id, limit=1000
                )

            # Add session metadata
            metadata["sessions"].append(
                {
                    "session_id": str(session_id),
                    "session_name": session["name"],
                    "created_at": session["created_at"].isoformat(),
                    "message_count": len(messages),
                }
            )

            # Generate session markdown
            session_md = await self._generate_session_markdown(
                session, messages, session_id
            )
            markdown_parts.append(session_md)
            markdown_parts.append("\n---\n")

        markdown = "\n".join(markdown_parts)

        # Create filename
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")
        safe_name = "".join(
            c if c.isalnum() or c in (" ", "_", "-") else "_" for c in project["name"]
        )
        filename = f"{safe_name}_export_{timestamp}.md"

        return ExportResult(
            metadata_json=metadata,
            markdown_content=markdown,
            session_count=len(sessions),
            filename=filename,
        )

    async def _generate_session_markdown(
        self, session: dict, messages: list[dict], session_id: UUID
    ) -> str:
        """Generate markdown content for a single session."""
        parts = [f"\n## Session: {session['name']}\n"]
        parts.append(
            f"**Created:** {session['created_at'].strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

        # Process message pairs (user query + assistant response)
        i = 0
        while i < len(messages):
            msg = messages[i]

            if msg["role"] == "user":
                # User query
                parts.append("\n### Query\n")
                parts.append(f"\n{msg['content']}\n")

                # Check if there's an assistant response
                if i + 1 < len(messages) and messages[i + 1]["role"] == "assistant":
                    i += 1
                    assistant_msg = messages[i]

                    # Parse metadata to get iterations
                    metadata = assistant_msg.get("metadata") or {}
                    if isinstance(metadata, str):
                        import json

                        try:
                            metadata = json.loads(metadata)
                        except Exception:
                            metadata = {}

                    iterations = metadata.get("iterations", [])

                    # Filter to successful iterations only
                    successful_iterations = [
                        iter_data
                        for iter_data in iterations
                        if isinstance(iter_data, dict) and iter_data.get("success")
                    ]

                    if successful_iterations:
                        parts.append("\n### Agent Response\n")

                        # Process each successful iteration
                        for idx, iter_data in enumerate(successful_iterations, 1):
                            if len(successful_iterations) > 1:
                                parts.append(
                                    f"\n#### Iteration {iter_data.get('iteration', idx)}\n"
                                )

                            # Thought process
                            thought = iter_data.get("thought") or iter_data.get(
                                "thoughts"
                            )
                            if thought:
                                parts.append(f"\n**Thought:**\n\n{thought}\n")

                            # Code
                            code = iter_data.get("code")
                            if code:
                                parts.append(f"\n**Code:**\n\n```python\n{code}\n```\n")

                            # Execution logs
                            logs = iter_data.get("execution_logs")
                            if logs:
                                parts.append(
                                    f"\n**Execution Log:**\n\n```\n{logs}\n```\n"
                                )

                            # Output (embedded artifacts)
                            output = iter_data.get("output")
                            final_result = iter_data.get("final_result")

                            # Prefer final_result if available (on last iteration)
                            display_output = (
                                final_result
                                if final_result and idx == len(successful_iterations)
                                else output
                            )

                            if display_output:
                                output_md = await self._embed_artifact(
                                    display_output, session_id
                                )
                                if output_md:
                                    label = (
                                        "**Answer:**"
                                        if final_result
                                        and idx == len(successful_iterations)
                                        else "**Result:**"
                                    )
                                    parts.append(f"\n{label}\n\n{output_md}\n")

                        # No successful iterations, show content if available
                        if assistant_msg["content"]:
                            parts.append("\n### Response\n")
                            parts.append(f"\n{assistant_msg['content']}\n")

                    mime_map = {
                        "png": "image/png",
                        "jpg": "image/jpeg",
                        "jpeg": "image/jpeg",
                        "svg": "image/svg+xml",
                        "gif": "image/gif",
                        "webp": "image/webp",
                    }

                    # Check for artifacts registered in the message
                    artifact_ids = assistant_msg.get("artifact_ids") or []
                    if artifact_ids:
                        parts.append("\n### Artifacts\n")
                        async with get_system_db() as conn:
                            for a_id in artifact_ids:
                                artifact = await self.artifact_repo.get_artifact(
                                    conn, a_id
                                )
                                if artifact:
                                    f_type = artifact["file_type"].lower().strip(".")
                                    # Embedding images specifically
                                    if f_type in mime_map:
                                        try:
                                            file_content = await self.workspace_service.download_file(
                                                session_id=session_id,
                                                file_name=artifact["file_name"],
                                            )
                                            import base64

                                            img_base64 = base64.b64encode(
                                                file_content
                                            ).decode("utf-8")
                                            mime = mime_map.get(f_type, "image/png")
                                            parts.append(
                                                f"\n**{artifact['file_name']}**\n"
                                            )
                                            parts.append(
                                                f"![{artifact['file_name']}](data:{mime};base64,{img_base64})\n"
                                            )
                                        except Exception as e:
                                            logger.warning(
                                                f"Failed to embed artifact {a_id}: {e}"
                                            )

                                    elif f_type == "json":
                                        # Check if it's a Plotly figure saved as JSON
                                        try:
                                            file_content = await self.workspace_service.download_file(
                                                session_id=session_id,
                                                file_name=artifact["file_name"],
                                            )
                                            import json

                                            data = json.loads(file_content)

                                            # If it looks like a plotly figure, try to render it
                                            if isinstance(data, dict) and (
                                                data.get("data") or data.get("layout")
                                            ):
                                                output_md = await self._embed_artifact(
                                                    {"kind": "plotly", "data": data},
                                                    session_id,
                                                )
                                                if output_md:
                                                    parts.append(
                                                        f"\n**{artifact['file_name']} (Plotly Chart):**\n"
                                                    )
                                                    parts.append(f"\n{output_md}\n")
                                            else:
                                                parts.append(
                                                    f"\n**[File: {artifact['file_name']}](/api/v1/artifacts/{artifact['artifact_id']}/download)** (JSON Data - click to download)\n"
                                                )
                                        except Exception:
                                            parts.append(
                                                f"\n**[File: {artifact['file_name']}](/api/v1/artifacts/{artifact['artifact_id']}/download)** (JSON File - click to download)\n"
                                            )

                                    elif f_type == "html":
                                        parts.append(
                                            f"\n**[Interactive Artifact: {artifact['file_name']}](/api/v1/artifacts/{artifact['artifact_id']}/download)** (HTML File - click to download/view)\n"
                                        )

                                    elif f_type == "csv":
                                        parts.append(
                                            f"\n**[File: {artifact['file_name']}](/api/v1/artifacts/{artifact['artifact_id']}/download)** (CSV Data - click to download)\n"
                                        )

            i += 1

        return "\n".join(parts)

    async def _embed_artifact(
        self, typed_data: dict[str, Any] | None, session_id: UUID
    ) -> str:
        """
        Convert TypedData to embedded markdown representation.

        Args:
            typed_data: TypedData dict with 'kind' and 'data' fields
            session_id: Session ID for artifact retrieval

        Returns:
            Markdown string with embedded content
        """
        if not typed_data or not isinstance(typed_data, dict):
            return ""

        kind = typed_data.get("kind")
        data = typed_data.get("data")

        if kind == "text":
            return str(data)

        elif kind == "table":
            # Convert table to markdown table
            if not isinstance(data, dict):
                return str(data)

            headers = data.get("headers", [])
            rows = data.get("rows", [])

            if not headers or not rows:
                return ""

            # Build markdown table
            lines = []
            # Header row
            lines.append("| " + " | ".join(str(h) for h in headers) + " |")
            # Separator
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
            # Data rows (limit to 100 for export)
            for row in rows[:100]:
                lines.append("| " + " | ".join(str(cell) for cell in row) + " |")

            if len(rows) > 100:
                lines.append(f"\n*({len(rows) - 100} more rows not shown)*\n")

            return "\n" + "\n".join(lines) + "\n"

        elif kind == "image":
            # Image is already base64 encoded
            format_type = typed_data.get("metadata", {}).get("format", "png")
            mime = "image/svg+xml" if format_type == "svg" else f"image/{format_type}"
            return f"\n![Artifact](data:{mime};base64,{data})\n"

        elif kind == "plotly":
            # Convert Plotly to static image
            try:
                import plotly.graph_objects as go
                import plotly.io as pio

                # Data should be plotly JSON
                fig = go.Figure(data)

                # Convert to PNG using kaleido
                import base64

                img_bytes = pio.to_image(fig, format="png")
                img_base64 = base64.b64encode(img_bytes).decode("utf-8")

                return f"![Plotly Chart](data:image/png;base64,{img_base64})"

            except Exception as e:
                logger.warning(f"Failed to convert Plotly to image: {e}")
                # Fallback: show as JSON
                import json

                return f"```json\n{json.dumps(data, indent=2)}\n```"

        elif kind == "json":
            # Display as formatted JSON
            import json

            return f"```json\n{json.dumps(data, indent=2)}\n```"

        elif kind == "multi":
            # Multiple outputs
            if not isinstance(data, list):
                return str(data)

            parts = []
            for idx, item in enumerate(data):
                item_metadata = (
                    item.get("metadata", {}) if isinstance(item, dict) else {}
                )
                name = item_metadata.get("name", f"Output {idx + 1}")
                parts.append(f"\n**{name}:**\n")
                item_md = await self._embed_artifact(item, session_id)
                parts.append(item_md)

            return "\n".join(parts)

        else:
            # Unknown type, return as string
            return str(data)
