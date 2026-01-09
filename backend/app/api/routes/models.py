"""
Models API routes.
"""

import json
from pathlib import Path

from app.shared.logging import get_logger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["models"])


class ModelInfo(BaseModel):
    """Model information."""

    id: str
    name: str
    provider: str
    slug: str
    context_length: int
    description: str | None = None


@router.get("/models")
async def get_available_models() -> list[ModelInfo]:
    """Return list of available models for selection."""
    try:
        # Load models from json file
        # In a real app, this might come from DB or external service
        models_file = Path("app/models.json")
        if not models_file.exists():
            # Fallback if file not found (e.g. running from different dir)
            models_file = Path(__file__).parent.parent.parent / "models.json"

        if not models_file.exists():
            logger.warning("models.json not found")
            return []

        with open(models_file, "r") as f:
            data = json.load(f)
            return [ModelInfo(**m) for m in data.get("models", [])]

    except Exception as e:
        logger.error("Failed to load models", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to load models")
