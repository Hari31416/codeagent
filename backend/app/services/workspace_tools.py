"""
Workspace tools for agent execution context.

These functions are injected into the agent's execution environment to allow
interaction with session workspace files (MinIO).
"""

import asyncio
from typing import Callable, Union
from uuid import UUID

import pandas as pd
from app.services.workspace_service import WorkspaceService
from app.shared.logging import get_logger

logger = get_logger(__name__)


def create_workspace_tools(
    session_id: UUID,
    workspace_service: WorkspaceService,
    project_id: UUID | None = None,
) -> dict[str, Callable]:
    """
    Create a dictionary of workspace tools bound to a specific session.

    These functions are designed to be used directly by the agent's generated code.
    They handle the async/sync bridge since the agent code runs synchronously
    but the workspace service is async.
    """

    def _run_async(coro):
        """Helper to run async code synchronously."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # If we're already in a loop (e.g. during testing or nested execution),
            # we can't use run_until_complete.
            import nest_asyncio

            nest_asyncio.apply()

        return loop.run_until_complete(coro)

    # -------------------------------------------------------------------------
    # Low-level File I/O
    # -------------------------------------------------------------------------

    def list_files() -> list[str]:
        """List all files in the current workspace (including project files)."""
        # Get session files
        files = _run_async(workspace_service.list_workspace_files(session_id))
        file_names = {f["name"].split("/")[-1] for f in files}

        # Get project files if available
        if project_id:
            project_files = _run_async(workspace_service.list_project_files(project_id))
            project_file_names = {f["name"].split("/")[-1] for f in project_files}
            file_names.update(project_file_names)

        return sorted(list(file_names))

    def _download_file_data(filename: str) -> bytes:
        """Helper to download file from session or project workspace."""
        try:
            # Try session workspace first
            return _run_async(workspace_service.download_file(session_id, filename))
        except Exception as e:
            # If failed and we have a project, try project workspace
            if project_id:
                try:
                    return _run_async(
                        workspace_service.download_project_file(project_id, filename)
                    )
                except Exception:
                    # If both fail, raise the original error (likely file not found)
                    pass
            raise e

    def read_file(filename: str, as_text: bool = True) -> Union[str, bytes]:
        """
        Read a file from the workspace.

        Args:
            filename: Name of the file to read
            as_text: If True, decode as UTF-8 string. If False, return bytes.
        """
        data = _download_file_data(filename)
        if as_text:
            return data.decode("utf-8")
        return data

    def write_file(filename: str, content: Union[str, bytes]) -> str:
        """
        Write content to a file in the workspace.

        Args:
            filename: Name of the file to write
            content: String or bytes content

        Returns:
            The filename that was written
        """
        if isinstance(content, str):
            data = content.encode("utf-8")
        else:
            data = content

        _run_async(workspace_service.upload_file(session_id, filename, data))
        return filename

    # -------------------------------------------------------------------------
    # High-level Helpers (Pandas/Plotting)
    # -------------------------------------------------------------------------

    def read_csv(filename: str, **kwargs) -> pd.DataFrame:
        """
        Read a CSV file from the workspace into a DataFrame.

        Args:
            filename: Name of the CSV file
            **kwargs: Arguments passed to pd.read_csv
        """
        from io import BytesIO

        data = _download_file_data(filename)
        return pd.read_csv(BytesIO(data), **kwargs)

    def read_excel(filename: str, **kwargs) -> pd.DataFrame:
        """
        Read an Excel file from the workspace into a DataFrame.

        Args:
            filename: Name of the file
            **kwargs: Arguments passed to pd.read_excel
        """
        from io import BytesIO

        data = _download_file_data(filename)
        return pd.read_excel(BytesIO(data), **kwargs)

    def save_csv(df: pd.DataFrame, filename: str, **kwargs) -> str:
        """
        Save a DataFrame to the workspace as a CSV file.

        Args:
            df: DataFrame to save
            filename: Target filename
            **kwargs: Arguments passed to df.to_csv

        Returns:
            The filename
        """
        # Default index=False if not specified
        if "index" not in kwargs:
            kwargs["index"] = False

        content = df.to_csv(**kwargs)
        write_file(filename, content)
        return filename

    def save_figure(fig, filename: str, **kwargs) -> str:
        """
        Save a matplotlib figure to the workspace.

        Args:
            fig: Matplotlib figure object
            filename: Target filename (e.g., 'plot.png')
            **kwargs: Arguments passed to fig.savefig
        """
        from io import BytesIO

        buf = BytesIO()
        fig.savefig(buf, **kwargs)
        buf.seek(0)

        _run_async(workspace_service.upload_file(session_id, filename, buf))
        return filename

    return {
        "list_files": list_files,
        "read_file": read_file,
        "write_file": write_file,
        "read_csv": read_csv,
        "read_excel": read_excel,
        "save_csv": save_csv,
        "save_figure": save_figure,
    }
