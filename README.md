# CodingAgent: AI-Powered Data Analysis & Coding Assistant

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.124.4-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.2.0-61DAFB.svg)](https://reactjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**CodingAgent** is a stateful, AI-driven platform for automated data analysis and visualization. It leverages frontier LLMs and a secure Python execution environment to transform natural language queries into executable code and interactive insights.

---

## Architecture Overview

The system features a project-centric, event-driven architecture designed for scalability and state persistence.

```mermaid
graph TD
    User([User])
    
    subgraph "Frontend (React + Vite)"
        UI[Project & Session Management]
        Chat[Interactive Chat Interface]
        Artifacts[Rich Result Renderer]
    end
    
    subgraph "Backend (FastAPI)"
        API[API Gateway]
        Orchestrator[Agent Orchestrator]
        Agent[ReAct Analysis Agent]
        Sandbox[Secure Python Sandbox]
    end
    
    subgraph "Storage & Services"
        Postgres[(PostgreSQL: Projects, Sessions & History)]
        Redis[(Redis: Distributed Locks & State)]
        MinIO[(MinIO: S3-Compatible Workspace)]
        OpenRouter([OpenRouter: Multi-Model API])
    end
    
    User <--> UI
    UI <--> Chat
    Chat <--> API
    API <--> Orchestrator
    Orchestrator <--> Agent
    Agent <--> Sandbox
    
    Orchestrator <--> Postgres
    Orchestrator <--> Redis
    Orchestrator <--> MinIO
    Orchestrator <--> OpenRouter
    
    Sandbox <--> MinIO
```

## Key Features

- **Project-Based Organization**: Group multiple analysis sessions under unified projects with shared datasets and persistent state.
- **Natural Language Data Analysis**: Convert English queries into complex data processing, filtering, and aggregation using pandas.
- **Multi-Model Support via OpenRouter**: Seamless access to frontier models including GPT-4o, Claude 3.5 Sonnet, Gemini 3 Pro, and DeepSeek V3.
- **Secure Code Execution**: Isolated sandbox for running AI-generated Python code using sophisticated safety boundaries and authorized imports.
- **Stateful Intelligence**: Persistent context across interactions, including file history, previous results, and agent "thought" logs.
- **Dynamic Artifacts**: Real-time rendering of interactive Plotly charts, data tables (pandas), and execution logs.
- **Automated Self-Correction**: The agent identifies execution errors and automatically refines code to achieve the requested goal.

## Tech Stack

| Layer | Technologies |
| --- | --- |
| **Frontend** | React 19, Vite, Tailwind CSS (v4), Shadcn UI, Lucide |
| **Backend** | FastAPI, Pydantic, LiteLLM, LangChain |
| **Agent Core** | smolagents, Custom Python Executors |
| **Storage** | PostgreSQL (Relational), Redis (Cache), MinIO (Object Storage) |
| **Build Tools** | **uv** (Python), **pnpm** (Node.js) |
| **AI Gateway** | **OpenRouter** (Unified LLM access) |

## Project Structure

```text
.
├── backend/                # FastAPI Application
│   ├── app/
│   │   ├── agents/         # ReAct logic & specialized analysis agents
│   │   ├── api/routes/     # API Endpoints (Projects, Sessions, Query, etc.)
│   │   ├── core/           # Core infrastructure (Storage providers, locks)
│   │   ├── db/             # Repository layer & Database connectivity
│   │   ├── prompts/        # Jinja2 templates for LLM instruction sets
│   │   ├── services/       # Business logic: Orchestration & Session state
│   │   ├── shared/         # Common models, LLM bridge & Logging
│   │   └── config.py       # Pydantic Settings & environment config
│   └── main.py             # Server entry point
├── frontend/               # React + Vite Application
│   ├── src/
│   │   ├── api/            # API client definitions (Axios)
│   │   ├── components/     # UI: Chat components, Artifact renderers, Sidebars
│   │   ├── hooks/          # Custom hooks for state & API consumption
│   │   ├── stores/         # Application state management
│   │   └── types/          # TypeScript interface & enum definitions
│   └── package.json
├── docker-compose.yml      # App services container orchestration
├── docker-compose.infra.yml # External dependencies (Postgres, Redis, MinIO)
└── Makefile                # Shortcuts for setup, testing, and linting
```

## Execution Flow

The following sequence illustrates a typical data analysis cycle within a project context.

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant LLM as OpenRouter
    participant A as Agent
    participant W as MinIO Workspace
    
    U->>F: Create Project & Upload File
    F->>B: POST /api/v1/projects
    B->>W: Initialize Project Bucket
    U->>F: Query: "Analyze sales correlation"
    F->>B: POST /api/v1/query (session_id)
    B->>B: Acquire Redis Lock
    B->>W: Fetch Project Files
    B->>A: Trigger ReAct Loop
    loop Self-Correction Cycle
        A->>LLM: Prompt for logic/code
        LLM->>A: Return Reasoning & Python Code
        A->>B: Execute in Sandbox
        B->>W: Read/Write Results
        B->>F: Stream Thoughts & Logs (SSE)
    end
    B->>F: Final Typed Data + Artifact IDs
    F->>U: Render Charts & Summary
```

## Installation & Setup

### 1. Infrastructure
Ensure Docker is installed and run:
```bash
docker-compose up -d
```

### 2. Backend (using uv)
```bash
cd backend
uv sync
# Add OPENROUTER_API_KEY to .env
python main.py
```

### 3. Frontend (using pnpm)
```bash
cd frontend
pnpm install
pnpm dev
```
