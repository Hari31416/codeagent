# Backend Implementation Guide

This document provides detailed instructions for implementing the AI Coding & Data Analysis Agent backend as described in `overview.md`.

---

## Table of Contents

1. [Existing Codebase Overview](#existing-codebase-overview)
2. [Phase 1: Infrastructure & Storage](#phase-1-infrastructure--storage)
3. [Phase 2: The Agent & Execution](#phase-2-the-agent--execution)
4. [Phase 4: Persistence & Optimization](#phase-4-persistence--optimization)
5. [Files to Update/Extend](#files-to-updateextend)
6. [Coding Guidelines](#coding-guidelines)

---

## Existing Codebase Overview

The backend already has the following foundational components that **MUST be reused**:

### Core Services (DO NOT RECREATE)

| File | Purpose | Reuse Instructions |
|------|---------|-------------------|
| `app/core/storage.py` | MinIO object storage service | Use `get_storage_service()` for all file operations |
| `app/core/cache.py` | Redis async cache service | Use the `cache` singleton for session state |
| `app/shared/llm.py` | LLM service with LiteLLM | Use `LLMService` class for all LLM calls |
| `app/shared/logging.py` | Structured logging with structlog | Use `get_logger(__name__)` in all new files |
| `app/prompts/manager.py` | Jinja2 template manager | Use `get_prompt_manager().render()` for prompts |

### Agents (DO NOT RECREATE)

| File | Purpose |
|------|---------|
| `app/agents/base/base_agent.py` | Contains `BaseAgent`, `SimpleLLMAgent`, and `CodingAgent` classes |
| `app/agents/base/rich_coding_agent.py` | `RichCodingAgent` with terminal output |
| `app/agents/executors/executor.py` | Executor abstraction with `ExecutorFactory` |
| `app/agents/executors/smolagents_executor.py` | Sandboxed Python execution |
| `app/agents/executors/daytona_executor.py` | Cloud-based execution option |

### Configuration

| File | Purpose |
|------|---------|
| `config.py` | Pydantic Settings with all env vars (MinIO, Redis, Postgres, LLM) |

---

## Phase 1: Infrastructure & Storage

### 1.1 Database Schema (PostgreSQL)

Create a new file: `app/db/models.py`

```python
"""
Database models for sessions, artifacts, and chat history.
Uses asyncpg for async PostgreSQL operations.
"""
```

**Required Tables:**

#### sessions
```sql
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    workspace_prefix VARCHAR(255) NOT NULL,  -- MinIO prefix: "sessions/{session_id}/"
    name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
```

#### artifacts
```sql
CREATE TABLE artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(message_id) ON DELETE SET NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,  -- 'csv', 'png', 'json', 'py', etc.
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    minio_object_key VARCHAR(512) NOT NULL,  -- Full path in MinIO
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb  -- Store column info, preview data, etc.
);
CREATE INDEX idx_artifacts_session ON artifacts(session_id);
CREATE INDEX idx_artifacts_message ON artifacts(message_id);
CREATE INDEX idx_artifacts_type ON artifacts(file_type);
```

#### messages (Chat History)
```sql
CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    code TEXT,  -- Agent-generated code (if any)
    thoughts TEXT,  -- Agent's reasoning (if any)
    artifact_ids UUID[] DEFAULT '{}',  -- References to artifacts created
    execution_logs TEXT,
    is_error BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_messages_created ON messages(created_at);
```

### 1.2 Database Service

Create: `app/db/session_db.py`

```python
"""
Session and artifact database operations.
"""
from uuid import UUID
from typing import Any

import structlog
from asyncpg import Connection

from app.shared.logging import get_logger

logger = get_logger(__name__)


class SessionRepository:
    """Repository for session CRUD operations."""
    
    async def create_session(
        self,
        conn: Connection,
        user_id: UUID,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Create a new session with workspace prefix."""
        ...
    
    async def get_session(
        self,
        conn: Connection,
        session_id: UUID,
    ) -> dict[str, Any] | None:
        """Get session by ID."""
        ...


class ArtifactRepository:
    """Repository for artifact CRUD operations."""
    
    async def create_artifact(
        self,
        conn: Connection,
        session_id: UUID,
        file_name: str,
        file_type: str,
        mime_type: str,
        size_bytes: int,
        minio_object_key: str,
        message_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Register a new artifact in the database."""
        ...
    
    async def get_artifacts_by_session(
        self,
        conn: Connection,
        session_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get all artifacts for a session."""
        ...


class MessageRepository:
    """Repository for chat message CRUD operations."""
    
    async def add_message(
        self,
        conn: Connection,
        session_id: UUID,
        role: str,
        content: str,
        code: str | None = None,
        thoughts: str | None = None,
        artifact_ids: list[UUID] | None = None,
        execution_logs: str | None = None,
        is_error: bool = False,
    ) -> dict[str, Any]:
        """Add a message to the chat history."""
        ...
    
    async def get_messages_by_session(
        self,
        conn: Connection,
        session_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get chat history for a session (for replay feature)."""
        ...
```

### 1.3 Workspace Service

Create: `app/services/workspace_service.py`

```python
"""
Workspace service - manages MinIO workspaces for sessions.

Uses the existing StorageService from app/core/storage.py
"""
from uuid import UUID
from typing import BinaryIO

import structlog

from app.core.storage import get_storage_service, StorageError
from app.shared.logging import get_logger

logger = get_logger(__name__)


class WorkspaceService:
    """
    Manages session workspaces in MinIO.
    
    Each session has a dedicated folder: sessions/{session_id}/
    """
    
    def __init__(self):
        self.storage = get_storage_service()
    
    def get_workspace_prefix(self, session_id: UUID) -> str:
        """Get the MinIO prefix for a session's workspace."""
        return f"sessions/{session_id}/"
    
    async def upload_file(
        self,
        session_id: UUID,
        file_name: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload a file to the session workspace.
        
        Returns:
            The MinIO object key
        """
        object_key = f"{self.get_workspace_prefix(session_id)}{file_name}"
        self.storage.upload(object_key, data, content_type)
        logger.info(
            "file_uploaded_to_workspace",
            session_id=str(session_id),
            file_name=file_name,
        )
        return object_key
    
    async def download_file(
        self,
        session_id: UUID,
        file_name: str,
    ) -> bytes:
        """Download a file from the session workspace."""
        object_key = f"{self.get_workspace_prefix(session_id)}{file_name}"
        return self.storage.download(object_key)
    
    async def get_presigned_url(
        self,
        session_id: UUID,
        file_name: str,
        expires_hours: int = 1,
    ) -> str:
        """Get a presigned URL for temporary file access."""
        from datetime import timedelta
        object_key = f"{self.get_workspace_prefix(session_id)}{file_name}"
        return self.storage.get_presigned_url(
            object_key, 
            expires=timedelta(hours=expires_hours)
        )
    
    async def list_workspace_files(
        self,
        session_id: UUID,
    ) -> list[dict]:
        """List all files in a session's workspace."""
        prefix = self.get_workspace_prefix(session_id)
        return self.storage.list_objects(prefix=prefix, recursive=True)
    
    async def delete_workspace(
        self,
        session_id: UUID,
    ) -> int:
        """Delete all files in a session's workspace. Returns count deleted."""
        prefix = self.get_workspace_prefix(session_id)
        files = self.storage.list_objects(prefix=prefix, recursive=True)
        for file_info in files:
            self.storage.delete(file_info["name"])
        logger.info(
            "workspace_deleted",
            session_id=str(session_id),
            files_deleted=len(files),
        )
        return len(files)
```

### 1.4 Session State Service (Redis)

Create: `app/services/session_state_service.py`

```python
"""
Session state service using Redis.

Uses the existing CacheService from app/core/cache.py
"""
from uuid import UUID
from typing import Any

from app.core.cache import cache  # Singleton CacheService instance
from app.shared.logging import get_logger

logger = get_logger(__name__)


class SessionState:
    """Represents the current state of a session."""
    
    def __init__(
        self,
        session_id: UUID,
        is_busy: bool = False,
        current_operation: str | None = None,
        last_code: str | None = None,
        last_output: str | None = None,
        console_buffer: list[str] | None = None,
    ):
        self.session_id = session_id
        self.is_busy = is_busy
        self.current_operation = current_operation
        self.last_code = last_code
        self.last_output = last_output
        self.console_buffer = console_buffer or []


class SessionStateService:
    """
    Manages transient session state in Redis.
    
    Tracks:
    - busy/idle status (to prevent race conditions)
    - console output buffer for real-time streaming
    - temporary computation results
    """
    
    BUSY_KEY_PREFIX = "session:busy:"
    CONSOLE_KEY_PREFIX = "session:console:"
    STATE_KEY_PREFIX = "session:state:"
    LOCK_TTL = 300  # 5 minutes
    CONSOLE_TTL = 3600  # 1 hour
    
    async def acquire_lock(self, session_id: UUID) -> bool:
        """
        Try to acquire a lock for a session (mark as busy).
        Returns True if lock acquired, False if session is already busy.
        
        Uses Redis SETNX for atomic operation.
        """
        key = f"{self.BUSY_KEY_PREFIX}{session_id}"
        client = await cache.get_client()
        # SETNX + EXPIRE atomically
        acquired = await client.set(key, "1", nx=True, ex=self.LOCK_TTL)
        if acquired:
            logger.debug("session_lock_acquired", session_id=str(session_id))
        else:
            logger.debug("session_already_busy", session_id=str(session_id))
        return bool(acquired)
    
    async def release_lock(self, session_id: UUID) -> None:
        """Release the busy lock for a session."""
        key = f"{self.BUSY_KEY_PREFIX}{session_id}"
        await cache.delete(key)
        logger.debug("session_lock_released", session_id=str(session_id))
    
    async def is_busy(self, session_id: UUID) -> bool:
        """Check if a session is currently busy."""
        key = f"{self.BUSY_KEY_PREFIX}{session_id}"
        return await cache.exists(key)
    
    async def append_console_output(
        self,
        session_id: UUID,
        output: str,
    ) -> None:
        """Append output to the console buffer for real-time streaming."""
        key = f"{self.CONSOLE_KEY_PREFIX}{session_id}"
        client = await cache.get_client()
        await client.rpush(key, output)
        await client.expire(key, self.CONSOLE_TTL)
    
    async def get_console_output(
        self,
        session_id: UUID,
        start: int = 0,
        end: int = -1,
    ) -> list[str]:
        """Get console output from the buffer."""
        key = f"{self.CONSOLE_KEY_PREFIX}{session_id}"
        client = await cache.get_client()
        outputs = await client.lrange(key, start, end)
        return outputs
    
    async def clear_console_output(self, session_id: UUID) -> None:
        """Clear the console output buffer."""
        key = f"{self.CONSOLE_KEY_PREFIX}{session_id}"
        await cache.delete(key)
    
    async def set_state(
        self,
        session_id: UUID,
        state: dict[str, Any],
        ttl: int = 3600,
    ) -> None:
        """Store session state as JSON."""
        key = f"{self.STATE_KEY_PREFIX}{session_id}"
        await cache.set_json(key, state, ttl_seconds=ttl)
    
    async def get_state(self, session_id: UUID) -> dict[str, Any] | None:
        """Retrieve session state."""
        key = f"{self.STATE_KEY_PREFIX}{session_id}"
        return await cache.get_json(key)
```

### 1.5 Upload API Endpoint

Create: `app/api/routes/upload.py`

```python
"""
File upload API endpoints.

Handles file uploads to MinIO with atomic database registration.
"""
from uuid import UUID

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.services.workspace_service import WorkspaceService
from app.db.session_db import ArtifactRepository
from app.db.pool import get_system_db  # Existing DB pool
from app.shared.logging import get_logger
from app.shared.models import BaseResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["upload"])

workspace_service = WorkspaceService()
artifact_repo = ArtifactRepository()


def get_file_type(filename: str) -> str:
    """Extract file type from filename."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
    return ext


def get_mime_type(file_type: str) -> str:
    """Get MIME type from file extension."""
    mime_map = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
        "json": "application/json",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "py": "text/x-python",
        "txt": "text/plain",
        "md": "text/markdown",
    }
    return mime_map.get(file_type, "application/octet-stream")


@router.post("/sessions/{session_id}/upload")
async def upload_file(
    session_id: UUID,
    file: UploadFile = File(...),
) -> JSONResponse:
    """
    Upload a file to a session's workspace.
    
    1. Saves file to MinIO under sessions/{session_id}/
    2. Creates artifact record in PostgreSQL
    3. Returns artifact_id and presigned URL
    """
    try:
        # Read file content
        content = await file.read()
        file_name = file.filename or "untitled"
        file_type = get_file_type(file_name)
        mime_type = get_mime_type(file_type)
        
        # Upload to MinIO
        object_key = await workspace_service.upload_file(
            session_id=session_id,
            file_name=file_name,
            data=content,
            content_type=mime_type,
        )
        
        # Register in database
        async with get_system_db() as conn:
            artifact = await artifact_repo.create_artifact(
                conn=conn,
                session_id=session_id,
                file_name=file_name,
                file_type=file_type,
                mime_type=mime_type,
                size_bytes=len(content),
                minio_object_key=object_key,
            )
        
        # Generate presigned URL for immediate access
        presigned_url = await workspace_service.get_presigned_url(
            session_id=session_id,
            file_name=file_name,
        )
        
        logger.info(
            "file_upload_complete",
            session_id=str(session_id),
            artifact_id=str(artifact["artifact_id"]),
            file_name=file_name,
            size_bytes=len(content),
        )
        
        return JSONResponse(
            content={
                "success": True,
                "data": {
                    "artifact_id": str(artifact["artifact_id"]),
                    "file_name": file_name,
                    "file_type": file_type,
                    "size_bytes": len(content),
                    "presigned_url": presigned_url,
                },
            },
            status_code=201,
        )
        
    except Exception as e:
        logger.error(
            "file_upload_failed",
            session_id=str(session_id),
            file_name=file.filename,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Phase 2: The Agent & Execution

### 2.1 Data Analysis Agent

Create: `app/agents/data_analysis_agent.py`

This agent extends the existing `CodingAgent` for data analysis tasks.

```python
"""
Data Analysis Agent

Specialized CodingAgent for data cleaning, analysis, and visualization.
Uses the existing CodingAgent base class and executor infrastructure.
"""
from typing import Any, AsyncGenerator

import structlog
import pandas as pd

from app.agents.base.base_agent import CodingAgent, AgentStatus, AgentStatusType
from app.shared.llm import LLMService
from app.prompts.manager import get_prompt_manager
from app.shared.logging import get_logger

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
        super().__init__(
            llm_service=llm_service,
            executor_type=executor_type,
            authorized_imports=authorized_imports,
        )
        self.prompt_manager = get_prompt_manager()
    
    @property
    def system_prompt(self) -> str:
        """Return system prompt from Jinja2 template."""
        return self.prompt_manager.render("coding/data_analysis.jinja2")
    
    async def execute_with_workspace(
        self,
        user_prompt: str,
        session_id: str,
        workspace_files: list[dict],
        dataframes: dict[str, pd.DataFrame] | None = None,
        max_iterations: int = 5,
    ) -> AsyncGenerator[AgentStatus, None]:
        """
        Execute with workspace context.
        
        Args:
            user_prompt: User's request
            session_id: Session ID for context
            workspace_files: List of files in the workspace
            dataframes: Pre-loaded DataFrames to inject into execution context
            max_iterations: Maximum number of reasoning iterations
        
        Yields:
            AgentStatus updates for real-time frontend display
        """
        # Build context with workspace information
        context = {
            "session_id": session_id,
            "workspace_files": workspace_files,
            "available_dataframes": list(dataframes.keys()) if dataframes else [],
        }
        
        # Inject dataframes into executor globals
        globals_dict = dataframes or {}
        
        async for status in self.execute_stream(
            user_prompt=user_prompt,
            context=context,
            max_iterations=max_iterations,
        ):
            yield status
```

### 2.2 Create New Prompt Template

Create: `app/prompts/templates/coding/data_analysis.jinja2`

```jinja2
{# ------------------------------------------------------------------ #}
{# Data Analysis Agent System Prompt                                   #}
{# Extends global.jinja2 with workspace awareness                      #}
{# ------------------------------------------------------------------ #}

{% include 'coding/global.jinja2' %}

----------------------------------------------------------------------
WORKSPACE CONTEXT
----------------------------------------------------------------------

You are operating within a session workspace. Files uploaded by the user
are available in the workspace and may be loaded into DataFrames.

When files are provided:
- Use pandas to read CSV files: pd.read_csv(file_path)
- For Excel files: pd.read_excel(file_path)
- Pre-loaded DataFrames may be available as variables

Workspace Files:
{% if workspace_files %}
{% for file in workspace_files %}
- {{ file.name }} ({{ file.size | filesizeformat if file.size else 'unknown size' }})
{% endfor %}
{% else %}
No files currently in workspace.
{% endif %}

----------------------------------------------------------------------
VISUALIZATION GUIDELINES
----------------------------------------------------------------------

When asked to create visualizations:
1. Use matplotlib or plotly for charts
2. Save figures to the workspace: plt.savefig('output.png')
3. Return the filename in your final answer
4. Prefer plotly for interactive charts when appropriate

For data tables:
1. Use df.to_html() for rich table display
2. Limit displayed rows to 50 for performance

----------------------------------------------------------------------
OUTPUT ARTIFACTS
----------------------------------------------------------------------

When you generate files (charts, cleaned data, reports):
1. Save them with descriptive names
2. Include the file name in your response
3. The files will be automatically captured and shown to the user
```

### 2.3 Agent Orchestrator Service

Create: `app/services/agent_orchestrator.py`

```python
"""
Agent Orchestrator

Coordinates agent execution with workspace, session state, and artifact management.
"""
from uuid import UUID, uuid4
from typing import AsyncGenerator, Any

import structlog
import pandas as pd

from app.agents.data_analysis_agent import DataAnalysisAgent
from app.agents.base.base_agent import AgentStatus, AgentStatusType
from app.services.workspace_service import WorkspaceService
from app.services.session_state_service import SessionStateService
from app.db.session_db import ArtifactRepository, MessageRepository
from app.db.pool import get_system_db
from app.shared.logging import get_logger
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
            workspace_files = await self.workspace_service.list_workspace_files(session_id)
            
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
            new_artifacts = await self._capture_new_artifacts(session_id, workspace_files)
            
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
                    content=final_result.get("answer", "") if final_result else "",
                    code=final_result.get("code") if final_result else None,
                    thoughts=final_result.get("thoughts") if final_result else None,
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
                            from io import BytesIO
                            df = pd.read_csv(BytesIO(file_content))
                        else:
                            from io import BytesIO
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
                        file_type=file_name.rsplit(".", 1)[-1] if "." in file_name else "unknown",
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
            type="status" if status.status_type != AgentStatusType.COMPLETED else "completed",
            event_type=event_type_map.get(status.status_type, StreamEventType.THINKING),
            agent_name="data_analysis",
            message=status.message,
            data=status.data,
            iteration=status.iteration,
            total_iterations=status.total_iterations,
        )
```

### 2.4 Query API (Streaming Endpoint)

Create: `app/api/routes/query.py`

```python
"""
Query processing API with Server-Sent Events (SSE) streaming.
"""
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse

from app.services.agent_orchestrator import AgentOrchestrator
from app.shared.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["query"])


@router.post("/sessions/{session_id}/query")
async def process_query(
    session_id: UUID,
    request: Request,
):
    """
    Process a user query with streaming response.
    
    Uses Server-Sent Events (SSE) for real-time updates.
    """
    body = await request.json()
    user_query = body.get("query")
    file_ids = body.get("file_ids", [])
    
    if not user_query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    # Convert file_ids to UUIDs
    file_uuid_list = [UUID(fid) for fid in file_ids] if file_ids else None
    
    orchestrator = AgentOrchestrator()
    
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
```

---

## Phase 4: Persistence & Optimization

### 4.1 History Replay Endpoint

Add to: `app/api/routes/sessions.py`

```python
@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: UUID,
    limit: int = 100,
    offset: int = 0,
):
    """
    Get chat history for a session.
    
    Used for:
    - Resuming conversations
    - Replaying past sessions
    - Branching from a specific point
    """
    async with get_system_db() as conn:
        messages = await message_repo.get_messages_by_session(
            conn=conn,
            session_id=session_id,
            limit=limit,
            offset=offset,
        )
    
    # Enrich with artifact presigned URLs
    enriched_messages = []
    for msg in messages:
        enriched = dict(msg)
        if msg.get("artifact_ids"):
            enriched["artifact_urls"] = []
            for artifact_id in msg["artifact_ids"]:
                url = await workspace_service.get_presigned_url(
                    session_id=session_id,
                    file_name=...,  # Get from artifact
                )
                enriched["artifact_urls"].append(url)
        enriched_messages.append(enriched)
    
    return {"success": True, "data": enriched_messages}
```

### 4.2 Artifact Presigned URL Endpoint

Add to: `app/api/routes/artifacts.py`

```python
@router.get("/artifacts/{artifact_id}/url")
async def get_artifact_url(
    artifact_id: UUID,
    expires_hours: int = 1,
):
    """
    Get a presigned URL for an artifact.
    
    URLs are temporary (default 1 hour) for security.
    """
    async with get_system_db() as conn:
        artifact = await artifact_repo.get_artifact(conn, artifact_id)
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    url = storage_service.get_presigned_url(
        artifact["minio_object_key"],
        expires=timedelta(hours=expires_hours),
    )
    
    return {
        "success": True,
        "data": {
            "artifact_id": str(artifact_id),
            "url": url,
            "expires_in_seconds": expires_hours * 3600,
        },
    }
```

### 4.3 Cleanup Task

Create: `app/tasks/cleanup.py`

```python
"""
Cleanup tasks for old sessions and temporary data.

Run periodically (e.g., via cron or scheduled task).
"""
from datetime import datetime, timedelta

from app.core.cache import cache
from app.services.workspace_service import WorkspaceService
from app.db.pool import get_system_db
from app.shared.logging import get_logger

logger = get_logger(__name__)

workspace_service = WorkspaceService()


async def cleanup_old_sessions(days_old: int = 30):
    """
    Delete sessions and their workspaces older than specified days.
    """
    cutoff = datetime.utcnow() - timedelta(days=days_old)
    
    async with get_system_db() as conn:
        # Get old sessions
        old_sessions = await conn.fetch(
            """
            SELECT session_id FROM sessions
            WHERE updated_at < $1
            """,
            cutoff
        )
        
        for session in old_sessions:
            session_id = session["session_id"]
            try:
                # Delete workspace files from MinIO
                await workspace_service.delete_workspace(session_id)
                
                # Delete from database (cascade deletes artifacts and messages)
                await conn.execute(
                    "DELETE FROM sessions WHERE session_id = $1",
                    session_id
                )
                
                logger.info("old_session_deleted", session_id=str(session_id))
                
            except Exception as e:
                logger.error(
                    "session_cleanup_failed",
                    session_id=str(session_id),
                    error=str(e),
                )


async def cleanup_redis_keys():
    """
    Clean up expired Redis keys that weren't auto-expired.
    """
    # Clear old console buffers
    deleted = await cache.clear_pattern("session:console:*")
    logger.info("redis_cleanup_complete", deleted_keys=deleted)
```

---

## Files to Update/Extend

### Files to MODIFY

| File | Modification Required |
|------|----------------------|
| `app/__init__.py` | Add new routers to FastAPI app |
| `app/shared/models.py` | Add new Pydantic models for Session, Artifact, Message |
| `app/shared/stream_models.py` | Already has StreamEvent - may need new event types |
| `config.py` | Add any new config settings if needed |

### Files to CREATE

| File | Purpose |
|------|---------|
| `app/db/models.py` | SQLAlchemy/raw SQL model definitions |
| `app/db/session_db.py` | Repository classes for DB operations |
| `app/services/workspace_service.py` | MinIO workspace management |
| `app/services/session_state_service.py` | Redis session state |
| `app/services/agent_orchestrator.py` | Agent execution orchestration |
| `app/agents/data_analysis_agent.py` | Specialized data analysis agent |
| `app/prompts/templates/coding/data_analysis.jinja2` | Agent prompt template |
| `app/api/routes/upload.py` | File upload endpoint |
| `app/api/routes/query.py` | Query processing with SSE |
| `app/api/routes/sessions.py` | Session management endpoints |
| `app/api/routes/artifacts.py` | Artifact URL endpoints |
| `app/tasks/cleanup.py` | Background cleanup tasks |

---

## Coding Guidelines

Follow these patterns from the existing codebase:

### 1. Logging

```python
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Use structured logging
logger.info(
    "operation_completed",
    session_id=str(session_id),
    duration_ms=elapsed,
)
```

### 2. Async Patterns

```python
# Use async/await consistently
async def my_function():
    result = await some_async_operation()
    return result

# Use AsyncGenerator for streaming
async def stream_results() -> AsyncGenerator[Event, None]:
    yield event
```

### 3. Prompts as Jinja2 Templates

```python
from app.prompts.manager import get_prompt_manager

pm = get_prompt_manager()
prompt = pm.render("coding/data_analysis.jinja2", {
    "workspace_files": files,
    "user_query": query,
})
```

### 4. Error Handling

```python
from app.shared.errors import ValidationError, NotFoundError

try:
    result = await operation()
except StorageError as e:
    logger.error("storage_operation_failed", error=str(e))
    raise HTTPException(status_code=500, detail="Storage error")
```

### 5. Type Hints

```python
from typing import Any, AsyncGenerator
from uuid import UUID

async def process(
    session_id: UUID,
    data: dict[str, Any],
) -> AsyncGenerator[StreamEvent, None]:
    ...
```

### 6. Use Existing Services

```python
# Storage
from app.core.storage import get_storage_service
storage = get_storage_service()

# Cache
from app.core.cache import cache
await cache.set_json(key, value)

# LLM
from app.shared.llm import LLMService
llm = LLMService()
result = await llm.simple_call(...)
```

---

## API Documentation

After implementation, ensure all endpoints are documented with FastAPI's automatic OpenAPI docs:

- Sessions: `/api/v1/sessions/`
- Upload: `/api/v1/sessions/{session_id}/upload`
- Query: `/api/v1/sessions/{session_id}/query`
- History: `/api/v1/sessions/{session_id}/history`
- Artifacts: `/api/v1/artifacts/{artifact_id}/url`

Visit `/docs` for interactive Swagger UI.
