## Project Plan: AI Coding & Data Analysis Agent

This document outlines the strategic plan for building a custom coding agent. The goal is to create a system where users can upload files and interact with an AI that writes and executes Python code to perform data cleaning, analysis, and visualization in a secure, stateful environment.

---

### 1. System Architecture Overview

The application will be built on a modular stack designed for scalability and data persistence:

* **Frontend (The Interface):** A responsive web application built with **Vite** and **Shadcn UI**. It will handle file uploads, chat interactions, and the rendering of "artifacts" (charts, tables, and logs).
* **Backend (The Orchestrator):** A **FastAPI** server that manages the logic flow between the user, the LLM (Large Language Model), and the execution environment.
* **Storage & Persistence:**
* **MinIO:** Acting as the "Virtual File System," providing dedicated workspace folders for every session.
* **PostgreSQL:** The source of truth for metadata, storing file registries, artifact details, and "playable" chat histories.
* **Redis:** A high-speed cache for session states, locking mechanisms to prevent race conditions, and temporary storage for transient logs.


* **Execution Engine:** A sandboxed environment (Docker or a specialized Micro-VM) where the AI-generated Python code is safely executed.

---

### 2. The Data Management Strategy

To ensure the agent is "stateful" and can remember previous steps, we will implement a tiered storage approach:

| Component | Responsibility |
| --- | --- |
| **Workspace (MinIO)** | Stores the actual physical files (.csv, .png, .py) generated or uploaded. |
| **Metadata (Postgres)** | Maps MinIO objects to specific chat messages and sessions. Tracks file types and sizes. |
| **History (Postgres)** | Stores messages in a structured format, allowing users to "replay" or branch conversations. |
| **Session Cache (Redis)** | Tracks if the agent is currently "busy" and stores recent console outputs for real-time streaming. |

---

### 3. Core Workflow: From Prompt to Artifact

1. **Initialization:** When a user starts a chat, a unique session ID is generated, and a corresponding folder (prefix) is reserved in MinIO.
2. **Upload & Registry:** User uploads an image or dataset. The file is saved to MinIO. A record is created in Postgres with a unique **Artifact ID**.
3. **The Reasoning Loop:**
* The user asks a question (e.g., "Analyze this sales data").
* The Backend sends the prompt + file metadata to the LLM.
* The LLM returns Python code.


4. **Secure Execution:**
* The Backend spins up a sandbox.
* Files are pulled from the MinIO workspace into the sandbox.
* The code runs, producing logs and new files (like a bar chart).


5. **Artifact Capture:** Any new files created by the code are pushed back to MinIO. Postgres is updated with these new Artifact IDs.
6. **Response:** The UI receives the message and a list of Artifact IDs. It fetches the results via signed URLs to display them to the user.

---

### 4. Key Milestones & Roadmap

#### Phase 1: Infrastructure & Storage

* Configure the MinIO bucket policy and PostgreSQL schema.
* Implement the FastAPI "Upload" logic that simultaneously writes to S3 and the Database.
* Set up Redis for basic session tracking.

#### Phase 2: The Agent & Execution

* Develop the system prompt that instructs the LLM on how to use the "Workspace" files.
* Establish the secure execution bridge (running code and capturing the standard output/error).
* Implement "Self-Correction" (if the code fails, the error is sent back to the LLM to fix).

#### Phase 3: Frontend & Visualization

* Build the chat interface using Shadcn components.
* Implement "Artifact Cards" that can render Markdown, Tables, or Images dynamically based on the file type.
* Add a "Code Viewer" so users can inspect what the agent wrote.

#### Phase 4: Persistence & Optimization

* Build the "History Replay" feature using the Postgres message store.
* Implement signed-URL logic for secure, temporary access to MinIO files.
* Add cleanup tasks to purge old workspaces and temporary Redis keys.
