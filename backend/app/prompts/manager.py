"""
Prompt Manager

Centralized management for Jinja2 prompt templates.
"""

import threading
from pathlib import Path
from typing import Any

import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = structlog.get_logger(__name__)

# Singleton instance
_prompt_manager: "PromptManager | None" = None
_prompt_manager_lock = threading.Lock()


class PromptManager:
    """
    Manages Jinja2 prompt templates.

    Templates are loaded from the /prompts/templates/ directory.

    Usage:
        pm = get_prompt_manager()
        prompt = pm.render("cleaner/system.jinja2", {"file_name": "sales.csv"})
    """

    def __init__(self, templates_dir: Path | None = None):
        """
        Initialize the prompt manager.

        Args:
            templates_dir: Path to templates directory
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "templates"

        self.templates_dir = templates_dir

        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(default=False),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self._register_filters()

        logger.info("Prompt manager initialized", templates_dir=str(templates_dir))

    def _register_filters(self):
        """Register custom Jinja2 filters."""

        def truncate_list(items: list[Any], max_items: int = 10) -> list[Any]:
            """Truncate a list to max items."""
            if len(items) <= max_items:
                return items
            return items[:max_items]

        def format_columns(columns: list[str], max_show: int = 15) -> str:
            """Format column list for display."""
            if len(columns) <= max_show:
                return ", ".join(columns)
            return (
                ", ".join(columns[:max_show]) + f"... (+{len(columns) - max_show} more)"
            )

        self.env.filters["truncate_list"] = truncate_list
        self.env.filters["format_columns"] = format_columns

    def render(self, template_name: str, context: dict[str, Any] | None = None) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Path to template (e.g., "cleaner/system.jinja2")
            context: Variables to pass to the template

        Returns:
            Rendered template string
        """
        context = context or {}

        try:
            template = self.env.get_template(template_name)
            rendered = template.render(**context)

            logger.debug(
                "Rendered prompt template",
                template=template_name,
                context_keys=list(context.keys()),
            )

            return rendered

        except Exception as e:
            logger.error(
                "Failed to render prompt template",
                template=template_name,
                error=str(e),
                exc_info=True,
            )
            raise

    def get_template_names(self) -> list[str]:
        """Get list of all available template names."""
        return self.env.list_templates()


def get_prompt_manager() -> PromptManager:
    """Get the singleton prompt manager instance."""
    global _prompt_manager

    if _prompt_manager is None:
        with _prompt_manager_lock:
            if _prompt_manager is None:
                _prompt_manager = PromptManager()

    return _prompt_manager
