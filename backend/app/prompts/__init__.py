"""
Datara Prompt Management

Centralized prompt management using Jinja2 templates.
"""

from app.prompts.manager import PromptManager, get_prompt_manager

__all__ = ["PromptManager", "get_prompt_manager"]
