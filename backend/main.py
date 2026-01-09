"""
CodingAgent Backend Entry Point

Runs the FastAPI application with uvicorn.
"""

import uvicorn
from app.config import settings


def main():
    """Run the FastAPI application."""
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers if not settings.reload else 1,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
