"""
CodingAgent Shared Models

Pydantic models, enums, and type definitions used throughout the application.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# =============================================================================
# Enums
# =============================================================================


class UserRole(str, Enum):
    """User access levels for authorization."""

    ADMIN = "admin"  # System admin - manages users and quotas
    READ_WRITE = (
        "read_write"  # Can upload files, attach DBs, create dashboards, AND query
    )
    READ_ONLY = "read_only"  # Can ONLY query existing data (no modifications)


# =============================================================================
# User Models
# =============================================================================


class UserBase(BaseModel):
    """Base user fields."""

    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    """Request body for admin to create a new user."""

    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.READ_WRITE
    storage_limit_mb: int = Field(default=500, ge=10, le=10000)
    table_limit: int = Field(default=50, ge=1, le=1000)
    can_connect_external_db: bool = True
    can_create_dashboards: bool = True
    can_use_rag: bool = True


class UserUpdate(BaseModel):
    """Request body for user to update their own profile."""

    full_name: str | None = None
    password: str | None = Field(default=None, min_length=8)


class UserAdminUpdate(BaseModel):
    """Request body for admin to update a user."""

    email: EmailStr | None = None
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    storage_limit_mb: int | None = Field(default=None, ge=10, le=10000)
    table_limit: int | None = Field(default=None, ge=1, le=1000)
    can_connect_external_db: bool | None = None
    can_create_dashboards: bool | None = None
    can_use_rag: bool | None = None


class User(UserBase):
    """Full user model stored in the system database."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    role: UserRole
    database_name: str

    # Quotas
    storage_limit_mb: int = 500
    table_limit: int = 50

    # Feature flags
    can_connect_external_db: bool = True
    can_create_dashboards: bool = True
    can_use_rag: bool = True

    # Metadata
    created_at: datetime
    created_by: UUID | None = None
    is_active: bool = True


class UserInDB(User):
    """User model with password hash (never expose this)."""

    password_hash: str


class UserResponse(UserBase):
    """User response for API (excludes sensitive fields)."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    role: UserRole
    storage_limit_mb: int
    table_limit: int
    can_connect_external_db: bool
    can_create_dashboards: bool
    can_use_rag: bool
    created_at: datetime
    is_active: bool


# =============================================================================
# Authentication Models
# =============================================================================


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class RefreshRequest(BaseModel):
    """Token refresh request body."""

    refresh_token: str


class TokenPayload(BaseModel):
    """JWT token payload (claims)."""

    sub: str  # User ID
    email: str
    role: str
    database_name: str
    exp: datetime
    token_type: str = "access"  # "access" or "refresh"


# =============================================================================
# Response Models
# =============================================================================

DataT = TypeVar("DataT")


class BaseResponse(BaseModel, Generic[DataT]):
    """Standard API response wrapper."""

    success: bool = True
    data: DataT | None = None
    message: str | None = None


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Paginated API response."""

    success: bool = True
    data: list[DataT]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorDetail(BaseModel):
    """Error detail for structured errors."""

    field: str | None = None
    message: str
    code: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response format."""

    success: bool = False
    error: str
    error_code: str | None = None
    details: list[ErrorDetail] | None = None
    request_id: str | None = None


# =============================================================================
# Health Check Models
# =============================================================================


class HealthStatus(str, Enum):
    """Health check status values."""

    OK = "ok"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DependencyHealth(BaseModel):
    """Health status of a single dependency."""

    status: HealthStatus
    latency_ms: float | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: HealthStatus
    version: str
    checks: dict[str, DependencyHealth] | None = None


# =============================================================================
# File Management Models
# =============================================================================


class FileTypeEnum(str, Enum):
    """File types supported by the system."""

    CSV = "csv"

    EXCEL = "excel"
    JSON = "json"
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class FileMetadataModel(BaseModel):
    """File metadata stored in database."""

    model_config = ConfigDict(from_attributes=True)

    file_id: str
    user_id: UUID
    original_name: str
    file_type: FileTypeEnum
    size_bytes: int
    storage_path: str  # Path in MinIO
    uploaded_at: datetime

    # For tabular files
    row_count: int | None = None
    column_names: list[str] | None = None

    # Processing status
    is_cleaned: bool = False
    cleaned_file_id: str | None = None
    schema_summary: str | None = None
    cleaning_report: dict | None = None  # JSONB cleaning report from DB

    # Metadata
    updated_at: datetime | None = None


class FileUploadResponse(BaseModel):
    """Response after successful file upload."""

    file_id: str
    original_name: str
    file_type: FileTypeEnum
    size_bytes: int
    row_count: int | None = None
    column_names: list[str] | None = None
    uploaded_at: datetime


class FileListResponse(BaseModel):
    """Response for file list endpoint."""

    files: list[FileMetadataModel]
    total: int


class FilePreview(BaseModel):
    """Preview of file data (first N rows)."""

    file_id: str
    rows: list[dict[str, Any]]
    total_rows: int
    columns: list[str]


# =============================================================================
# Cleaning Models
# =============================================================================


class CleaningIssue(BaseModel):
    """A single data quality issue detected during cleaning."""

    description: str
    severity: str = "medium"  # "low", "medium", "high"
    issue_type: str | None = None  # "empty_rows", "duplicates", etc.
    location: str | None = None  # Column name or cell reference
    count: int | None = None  # Number of occurrences


class CleaningReport(BaseModel):
    """Report of data cleaning operations."""

    file_name: str
    issues: list[CleaningIssue] = []
    transformations: list[str] = []  # List of applied transformations
    before_row_count: int
    before_col_count: int
    after_row_count: int
    after_col_count: int
    error: str | None = None  # Error message if cleaning failed


# =============================================================================
# Agent Response Models
# =============================================================================


class ArtifactType(str, Enum):
    """Types of artifacts returned by agents."""

    CODE = "code"
    SQL = "sql"
    CHART = "chart"
    DASHBOARD = "dashboard"
    SOURCE = "source"
    CLEANING_REPORT = "cleaning_report"
    ERROR = "error"
    TEXT = "text"


class Artifact(BaseModel):
    """
    Artifact returned by an agent (code, SQL, chart spec, etc.).
    """

    type: ArtifactType
    content: str
    language: str | None = None  # e.g., "python", "sql"
    reason: str | None = None  # Explanation for why this artifact was created
    metadata: dict[str, Any] | None = None


class AgentResponse(BaseModel):
    """
    Standardized response format for all agents.
    """

    agent_name: str
    success: bool = True
    answer: str  # Natural language response
    artifacts: list[Artifact] = []
    sources: list[str] = []  # Citations, file IDs, table names, etc.
    execution_time_ms: float | None = None
    usage: dict[str, Any] | None = None  # Token usage, cost, etc.
    metadata: dict[str, Any] | None = None


class AgentStatusType(str, Enum):
    """Types of status updates from agents."""

    STARTED = "started"
    THINKING = "thinking"
    GENERATING_CODE = "generating_code"
    EXECUTING = "executing"
    ITERATION_COMPLETE = "iteration_complete"
    CLARIFICATION_REQUIRED = "clarification_required"
    ERROR = "error"
    COMPLETED = "completed"


class AgentStatus(BaseModel):
    """
    Status update from an agent during execution.

    Used for streaming live updates to the frontend.
    Agents yield these during execution to provide progress.
    """

    agent_name: str
    status_type: AgentStatusType
    message: str
    iteration: int | None = None
    total_iterations: int | None = None
    data: dict[str, Any] | None = None  # Additional status-specific data
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Memory Models
# =============================================================================


class ChatMessage(BaseModel):
    """Chat message for memory system."""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str | None = None
    metadata: dict[str, Any] | None = None


class SessionContext(BaseModel):
    """Session context for LLM calls."""

    session_id: str
    messages: list[ChatMessage]
    active_files: list[str] = []
    active_connections: list[str] = []


class UserPreference(BaseModel):
    """Single user preference."""

    user_id: UUID
    preference_key: str
    preference_value: Any
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SavedQuery(BaseModel):
    """User's saved query."""

    query_id: UUID
    user_id: UUID
    query_text: str
    query_type: str  # "sql", "pandas", "rag"
    description: str | None = None
    is_favorite: bool = False
    use_count: int = 0
    created_at: datetime
    last_used_at: datetime


# =============================================================================
# Schema Models (for Schema Learning)
# =============================================================================


class ColumnSummary(BaseModel):
    """Summary of a single column."""

    name: str
    data_type: str
    nullable: bool = True
    unique_count: int | None = None
    sample_values: list[Any] = []
    description: str | None = None


class TableSummary(BaseModel):
    """Summary of a database table."""

    table_name: str
    columns: list[ColumnSummary]
    row_count: int | None = None
    description: str | None = None
    primary_keys: list[str] = []
    foreign_keys: dict[str, str] = {}  # {column: referenced_table.column}


class SchemaSummary(BaseModel):
    """Complete schema summary for a database or file collection."""

    source_type: str  # "database", "files", "external_db"
    source_name: str
    tables: list[TableSummary]
    relationships: list[dict[str, str]] = []  # [{from, to, type}]
    description: str | None = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# LLM Usage Tracking Models
# =============================================================================


class TokenMetrics(BaseModel):
    """Token usage metrics."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None = None


class LLMUsage(BaseModel):
    """LLM usage log entry."""

    log_id: UUID
    user_id: UUID
    agent_name: str | None = None
    model_name: str
    operation: str  # "query", "clean", "visualize", etc.
    input_tokens: int
    output_tokens: int
    estimated_cost: float | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Database Connection Models
# =============================================================================


class DBType(str, Enum):
    """Supported external database types."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"


class DBConnectionCreate(BaseModel):
    """Request to create a new database connection."""

    name: str = Field(..., min_length=1, max_length=100)
    db_type: DBType
    host: str
    port: int = Field(..., ge=1, le=65535)
    database_name: str
    username: str
    password: str
    description: str | None = None


class DBConnectionUpdate(BaseModel):
    """Request to update a database connection."""

    name: str | None = None
    description: str | None = None
    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = None
    password: str | None = None  # If provided, will be re-encrypted


class DBConnection(BaseModel):
    """Database connection metadata."""

    model_config = ConfigDict(from_attributes=True)

    connection_id: str
    user_id: UUID | None = None
    name: str
    db_type: DBType
    host: str
    port: int
    database_name: str
    username: str
    description: str | None = None
    is_active: bool = True
    schema_learned: bool = False
    schema_summary: str | None = None
    created_at: datetime
    last_tested_at: datetime | None = None


class DBConnectionTestResult(BaseModel):
    """Result of testing a database connection."""

    success: bool
    message: str
    latency_ms: float | None = None


# =============================================================================
# Database Schema Info Models
# =============================================================================


class DBColumnInfo(BaseModel):
    """Column information from external database."""

    column_name: str
    data_type: str
    is_nullable: bool = True
    is_primary_key: bool = False
    column_description: str | None = None


class DBTableInfo(BaseModel):
    """Table information from external database."""

    table_name: str
    table_description: str | None = None
    columns: list[DBColumnInfo] = []


class DBInfo(BaseModel):
    """Complete database schema information."""

    connection_id: str
    database_name: str
    tables: list[DBTableInfo] = []
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DBRelationship(BaseModel):
    """Table relationship from external database."""

    table_name: str  # Source table
    primary_key: str  # Source column
    related_table_name: str  # Target table
    foreign_key: str  # Target column
    relationship_type: str = "one-to-many"  # one-to-one, one-to-many, many-to-many
    relationship_description: str | None = None


class DBRelationships(BaseModel):
    """All relationships for a database."""

    connection_id: str
    database_name: str
    relationships: list[DBRelationship] = []
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# DBA Agent Models
# =============================================================================


class DBAQueryResult(BaseModel):
    """Result from DBA agent query execution."""

    success: bool
    sql_query: str | None = None
    results: list[dict[str, Any]] | None = None
    row_count: int = 0
    explanation: str | None = None
    iterations: int = 0
    code_history: list[dict[str, Any]] = []
    error: str | None = None


class SQLValidationResult(BaseModel):
    """Result of SQL validation."""

    is_valid: bool
    modified_sql: str | None = None
    errors: list[str] = []
    warnings: list[str] = []


class SQLAnalysis(BaseModel):
    """Analysis of a SQL query structure."""

    query_type: str  # SELECT, INSERT, etc.
    tables: list[str] = []
    columns: dict[str, list[str]] = {}  # table -> columns
    joins: list[dict[str, str]] = []
    where_conditions: list[str] = []
    has_aggregation: bool = False
    has_subquery: bool = False


# =============================================================================
# Analyst Agent Models
# =============================================================================


class AnalystResult(BaseModel):
    """Result from Analyst agent.

    .. deprecated:: 2.0
        Use DataProcessorResult + VizSpec via Orchestrator instead.
    """

    success: bool
    answer: str = ""
    code_history: list[dict[str, Any]] = []
    data: dict | list | None = None  # Aggregated/computed data
    chart_json: dict | None = None  # Plotly figure as JSON (deprecated)
    chart_spec: dict | None = None  # Vega-Lite specification (preferred)
    iterations: int = 0
    error: str | None = None


# =============================================================================
# Query Decomposition Models (Smart Orchestrator)
# =============================================================================


class VizIntent(BaseModel):
    """Visualization intent extracted from user query.

    Used by QueryDecomposer to signal chart requirements to VizSpecAgent.
    """

    needed: bool = False
    chart_type_hint: str | None = None  # "bar", "line", "scatter", "pie", etc.
    x_hint: str | None = None  # Suggested x-axis field
    y_hint: str | None = None  # Suggested y-axis field
    color_hint: str | None = None  # Suggested color encoding field


class PostProcessingIntent(BaseModel):
    """Post-processing intent for SQL-incompatible operations.

    Set when the query requires operations SQL cannot handle:
    - correlation, covariance
    - dynamic pivoting
    - statistical tests
    - outlier detection
    """

    needed: bool = False
    operation_hint: str | None = None  # "correlation", "pivot", "outliers", etc.
    description: str | None = None  # Human-readable description of operation


class DecomposedQuery(BaseModel):
    """Result of query decomposition by QueryDecomposer.

    Splits user query into:
    - data_query: Clean query for DBA (stripped of viz/analysis keywords)
    - viz_intent: Chart requirements
    - post_processing: SQL-incompatible operations
    """

    original_query: str
    data_query: str  # Clean query for DBA (no "plot", "chart", "correlation" etc.)
    viz_intent: VizIntent = Field(default_factory=VizIntent)
    post_processing: PostProcessingIntent = Field(default_factory=PostProcessingIntent)
    target: str = "dba"  # Primary agent target
    reasoning: str | None = None  # Explanation of decomposition


class DataProcessorResult(BaseModel):
    """Result from DataProcessor agent.

    Returned after pandas-based post-processing of SQL results.
    """

    success: bool
    data: list[dict[str, Any]] | None = None  # Transformed data
    code: str | None = None  # Python code executed
    answer: str = ""  # Natural language explanation
    iterations: int = 0
    error: str | None = None


class QueryArtifact(BaseModel):
    """Stored artifacts for query rerun capability.

    Captures the complete execution path for reproducing results:
    - SQL query for data fetching
    - Transform code for post-processing
    - Viz spec for chart generation
    """

    artifact_id: str
    sql_code: str
    transform_code: str | None = None
    viz_spec: dict[str, Any] | None = None  # Vega-Lite specification
    connection_id: str | None = None
    file_id: str | None = None
    table_name: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage/API response."""
        return {
            "artifact_id": self.artifact_id,
            "sql_code": self.sql_code,
            "transform_code": self.transform_code,
            "viz_spec": self.viz_spec,
            "connection_id": self.connection_id,
            "file_id": self.file_id,
            "table_name": self.table_name,
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# Query & Conversation Models
# =============================================================================


class QueryRequest(BaseModel):
    """Request body for query endpoint."""

    query: str
    conversation_id: UUID | None = None  # Continue existing conversation
    file_id: str | None = None
    connection_id: str | None = None
    skip_visualization: bool = False  # Force skip visualization stage
    theme: str | None = None


class QueryResponse(BaseModel):
    """Response from query endpoint."""

    conversation_id: UUID
    turn_id: UUID
    turn_number: int
    answer: str
    agent_used: str
    success: bool
    artifacts: list[Artifact] = []
    data: dict | list | None = None
    code_history: list[dict[str, Any]] = []
    # Chart output - prefer chart_spec (Vega-Lite)
    chart_spec: dict | None = None  # Vega-Lite specification (preferred)
    chart_json: dict | None = None  # Plotly JSON (deprecated, backward compat)
    chart_type: str | None = None  # "vega" or "plotly"
    # Rerun capability
    query_artifact_id: str | None = None
    needs_clarification: bool = False
    execution_time_ms: float | None = None


class QueryIntent(BaseModel):
    """Classification result for query routing."""

    target: str  # "dba", "analyst", "librarian", "unknown"
    confidence: float
    needs_visualization: bool = False
    file_id: str | None = None
    connection_id: str | None = None
    reasoning: str | None = None


# =============================================================================
# Source Selection Models (Intelligent Data Source Detection)
# =============================================================================


class FileMetadata(BaseModel):
    """Metadata for uploaded files (for source selection)."""

    file_id: str
    name: str
    upload_date: datetime
    row_count: int | None = None
    columns: list[str] | None = None


class ConnectionMetadata(BaseModel):
    """Metadata for database connections (for source selection)."""

    connection_id: str
    name: str
    db_type: str  # postgres, mysql, etc.
    schema_preview: list[str] | None = None  # table names


class DocumentMetadata(BaseModel):
    """Metadata for documents (PDFs, DOCX) for source selection."""

    document_id: str
    name: str
    doc_type: str  # "pdf", "docx"
    page_count: int | None = None
    upload_date: datetime


class SourceSelectionContext(BaseModel):
    """Rich context for source selection."""

    query: str
    available_files: list[FileMetadata] = []
    available_connections: list[ConnectionMetadata] = []
    available_documents: list[DocumentMetadata] = []
    conversation_history: list[dict] | None = None
    query_intent: "QueryIntent | None" = None


class SourceSelection(BaseModel):
    """Result of source selection."""

    source_type: str  # "file", "connection", "document", "needs_clarification", "none"
    source_id: str | None = None
    source_name: str | None = None
    confidence: float
    reasoning: str
    clarification_question: str | None = None  # Set when needs_clarification
    available_options: list[dict] | None = None  # Options to show user
    agent_target: str = "dba"  # "dba", "librarian", "dashboard", "unknown"
    needs_visualization: bool = False


class UnifiedQueryResult(BaseModel):
    """Unified result from single-agent query routing.

    Combines intent classification, source selection, and query decomposition
    into a single LLM call to reduce latency.

    Note: Detailed visualization hints (chart type, axes) are delegated to
    viz_spec_agent which can infer them from the actual data.
    """

    # Intent classification
    target: str  # "dba", "librarian", "dashboard", "unknown"
    confidence: float

    # Source selection
    source_type: str  # "file", "connection", "document", "needs_clarification", "none"
    source_id: str | None = None
    source_name: str | None = None

    # Query decomposition
    data_query: str  # Clean query without viz keywords
    needs_visualization: bool = False  # Simple boolean flag
    post_processing: PostProcessingIntent = Field(default_factory=PostProcessingIntent)

    # Shared fields
    reasoning: str | None = None
    clarification_question: str | None = None
    available_options: list[dict] | None = None


class ConversationSummary(BaseModel):
    """Summary of a conversation for list view."""

    conversation_id: UUID
    title: str | None = None
    last_query: str | None = None
    turn_count: int = 0
    created_at: datetime
    last_activity_at: datetime


class ConversationDetail(BaseModel):
    """Full conversation with all turns."""

    conversation_id: UUID
    title: str | None = None
    turns: list["TurnSummary"] = []
    created_at: datetime


class TurnSummary(BaseModel):
    """Summary of a single turn."""

    turn_id: UUID
    turn_number: int
    query_text: str
    agent_used: str | None = None
    success: bool = True
    response_summary: str | None = None
    artifacts: list[Artifact] = []
    data: dict | list | None = None
    code_history: list[dict] = []
    chart_spec: dict | None = None  # Vega-Lite or Plotly chart specification
    chart_type: str | None = None  # "vega" or "plotly"
    has_chart: bool = False
    needs_clarification: bool = False
    execution_time_ms: float | None = None
    started_at: datetime | None = None
    created_at: datetime


class TurnDetailResponse(BaseModel):
    """Complete turn details for replay."""

    turn_id: UUID
    turn_number: int
    query_text: str
    translated_query: str | None = None
    original_language: str | None = None
    agent_used: str | None = None
    success: bool = True
    response_summary: str | None = None
    code_history: list[dict[str, Any]] | None = None
    observations: list[str] | None = None
    artifacts: list[Artifact] | None = None
    result_data: dict | list | None = None
    chart_spec: dict | None = None  # Vega-Lite or Plotly chart specification
    chart_url: str | None = None  # Presigned URL to fetch chart JSON (for large charts)
    chart_type: str | None = None  # "plotly" or "vega"
    input_tokens: int | None = None
    output_tokens: int | None = None
    created_at: datetime
