"""
Database models and schema definitions for sessions, artifacts, and chat history.

This file contains the SQL schema definitions. The actual table creation
should be done via migration scripts.
"""

# SQL Schema for reference
SESSIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    workspace_prefix VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
"""

ARTIFACTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(message_id) ON DELETE SET NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    minio_object_key VARCHAR(512) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_artifacts_session ON artifacts(session_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_message ON artifacts(message_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(file_type);
"""

MESSAGES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    code TEXT,
    thoughts TEXT,
    artifact_ids UUID[] DEFAULT '{}',
    execution_logs TEXT,
    is_error BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
"""


async def create_tables(conn):
    """
    Create all required tables if they don't exist.

    Args:
        conn: asyncpg connection object

    Note: This is a helper function. In production, use proper migration tools.
    """
    await conn.execute(SESSIONS_TABLE_SQL)
    await conn.execute(ARTIFACTS_TABLE_SQL)
    await conn.execute(MESSAGES_TABLE_SQL)
