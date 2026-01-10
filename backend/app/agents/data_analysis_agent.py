"""
Data Analysis Agent

Specialized CodingAgent for data cleaning, analysis, and visualization.
Uses the existing CodingAgent base class and executor infrastructure.
"""

from typing import Any, AsyncGenerator

import pandas as pd
from app.agents.base.base_agent import CodingAgent
from app.prompts.manager import get_prompt_manager
from app.shared.llm import LLMService
from app.shared.logging import get_logger
from app.shared.models import AgentStatus

logger = get_logger(__name__)


class DataAnalysisAgent(CodingAgent):
    """
    Agent specialized for data analysis tasks.

    Features:
    - Workspace-aware: knows about session files
    - DataFrame context injection
    - Visualization output handling
    """

    def __init__(
        self,
        llm_service: LLMService | None = None,
        executor_type: str | None = None,
        model: str | None = None,
    ):
        # Extended authorized imports for data analysis
        authorized_imports = [
            "pandas",
            "numpy",
            "matplotlib",
            "matplotlib.pyplot",
            "seaborn",
            "plotly",
            "plotly.express",
            "plotly.graph_objects",
            "scipy",
            "sklearn",
            "datetime",
            "json",
            "re",
            "math",
            "statistics",
            "collections",
            "itertools",
            "PIL",
            "io",
        ]

        # Initialize LLM service with specific model if provided
        if model and llm_service is None:
            llm_service = LLMService(model=model)

        super().__init__(
            llm_service=llm_service,
            executor_type=executor_type,
            authorized_imports=authorized_imports,
        )
        self.prompt_manager = get_prompt_manager()
        self._workspace_files: list[dict] = []

    @property
    def system_prompt(self) -> str:
        """Return system prompt from Jinja2 template with workspace context."""
        return self.prompt_manager.render(
            "coding/data_analysis.jinja2",
            context={"workspace_files": self._workspace_files},
        )

    async def execute_with_workspace(
        self,
        user_prompt: str,
        session_id: str,
        workspace_files: list[dict],
        dataframes: dict[str, pd.DataFrame] | None = None,
        workspace_tools: dict[str, Any] | None = None,
        max_iterations: int = 5,
    ) -> AsyncGenerator[AgentStatus, None]:
        """
        Execute with workspace context.

        Args:
            user_prompt: User's request
            session_id: Session ID for context
            workspace_files: List of files in the workspace
            dataframes: Pre-loaded DataFrames to inject into execution context
            workspace_tools: Dictionary of workspace I/O functions
            max_iterations: Maximum number of reasoning iterations

        Yields:
            AgentStatus updates for real-time frontend display
        """

        # Store cleaned workspace files for system prompt rendering
        # We only want to show the basename to the agent so it matches what tools expect
        cleaned_files = []
        for f in workspace_files:
            clean_f = f.copy()
            clean_f["name"] = f["name"].split("/")[-1]
            cleaned_files.append(clean_f)
        self._workspace_files = cleaned_files

        logger.debug(
            "Workspace files injected into prompt",
            count=len(self._workspace_files),
            files=[f["name"] for f in self._workspace_files],
        )

        # Build context with workspace information
        context = {
            "session_id": session_id,
            "workspace_files": self._workspace_files,
            "available_dataframes": list(dataframes.keys()) if dataframes else [],
        }

        # Merge dataframes into context so they're available during execution
        # The executor will inject these as global variables
        if dataframes:
            logger.info(
                "Adding dataframes to context", total_dataframes=len(dataframes)
            )
            context.update(dataframes)

        # Merge workspace tools into context
        if workspace_tools:
            logger.debug(
                "Adding workspace tools to context", total_tools=len(workspace_tools)
            )
            context.update(workspace_tools)

        async for status in self.execute_stream(
            user_prompt=user_prompt,
            context=context,
            max_iterations=max_iterations,
            session_id=session_id,
            include_context=True,
        ):
            yield status
