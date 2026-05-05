# 🤖 Autonomous Requirement-to-Code Refinement Agent (ReAct)

An AI agent that iteratively refines code from vague requirements using an **explicit ReAct loop**:

```
Thought → Action → Observation → Evaluation → Refinement → (loop)
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      ReAct Loop Controller                    │
│                                                              │
│  while score < threshold and iter < max_iterations:          │
│    thought     = Planner.think()          # REASON           │
│    code        = CodeGenerator.generate() # ACT              │
│    exec_result = Sandbox.execute()        # OBSERVE          │
│    test_result = TestRunner.run()         # OBSERVE          │
│    score       = Evaluator.evaluate()     # EVALUATE         │
│    plan        = Refiner.plan()           # REFINE           │
└──────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Backend  | FastAPI + Python 3.11               |
| AI       | OpenAI GPT-4o (or any local SLM)    |
| Sandbox  | Docker (subprocess fallback)         |
| Database | MongoDB (Motor async driver)        |
| Frontend | React 18 + Vite + TailwindCSS       |
| Streaming| Server-Sent Events (SSE)            |

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Node.js 20+
- MongoDB (local or Docker)
- Docker (optional, for code sandbox)
- OpenAI API key (or local LLM)

### 2. Backend Setup

```bash
cd backend
cp .env.example .env
# Edit .env and set OPENAI_API_KEY

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### 4. Docker Compose (Full Stack)

```bash
cp backend/.env.example backend/.env
# Set OPENAI_API_KEY in backend/.env

docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 5. Run Demo Script

```bash
# Shows full "Build a login API" example end-to-end
OPENAI_API_KEY=your-key python demo.py
```

### 6. Run Tests

```bash
cd backend
pip install pytest pytest-asyncio
pytest ../tests/ -v
```

## Configuration (`.env`)

| Variable             | Default      | Description                         |
|----------------------|--------------|-------------------------------------|
| `LLM_PROVIDER`       | `openai`     | `openai` or `local`                 |
| `OPENAI_API_KEY`     | —            | Your OpenAI key                     |
| `OPENAI_MODEL`       | `gpt-4o`     | Model name                          |
| `LOCAL_LLM_BASE_URL` | `http://localhost:11434/v1` | Ollama/LM Studio URL |
| `LOCAL_LLM_MODEL`    | `codellama`  | Local model name                    |
| `MAX_ITERATIONS`     | `8`          | Max ReAct loop iterations           |
| `QUALITY_THRESHOLD`  | `0.80`       | Score threshold to stop loop        |
| `MONGODB_URL`        | `mongodb://localhost:27017` | MongoDB connection |
| `DOCKER_TIMEOUT`     | `30`         | Sandbox execution timeout (seconds) |

## API Reference

| Method | Endpoint                        | Description                    |
|--------|---------------------------------|--------------------------------|
| POST   | `/api/v1/agent/start`           | Submit requirement, get questions |
| POST   | `/api/v1/agent/submit`          | Submit clarification answers   |
| GET    | `/api/v1/agent/stream/{id}`     | SSE stream of agent events     |
| GET    | `/api/v1/agent/status/{id}`     | Session status                 |
| GET    | `/api/v1/sessions`              | List all sessions              |
| GET    | `/api/v1/sessions/{id}`         | Session detail                 |
| DELETE | `/api/v1/sessions/{id}`         | Delete session                 |
| GET    | `/api/v1/health`                | Health check                   |

## Project Structure

```
react-agent/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── planner.py        # Thought: plans next action
│   │   │   ├── evaluator.py      # Scores code quality (0-1)
│   │   │   ├── refiner.py        # Plans targeted improvements
│   │   │   └── react_loop.py     # THE explicit ReAct loop
│   │   ├── tools/
│   │   │   ├── clarification_tool.py   # Tool 1: Q&A
│   │   │   ├── code_generator_tool.py  # Tool 2: Code gen
│   │   │   ├── execution_tool.py       # Tool 3: Docker sandbox
│   │   │   ├── test_generator_tool.py  # Tool 4: Test gen
│   │   │   └── test_runner_tool.py     # Tool 5: Pytest runner
│   │   ├── core/
│   │   │   ├── config.py         # Settings
│   │   │   ├── database.py       # MongoDB
│   │   │   └── llm.py            # Modular LLM interface
│   │   ├── models/schemas.py     # Pydantic models
│   │   └── routes/               # FastAPI routes
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── agent/            # Agent UI components
│       │   └── ui/               # Reusable UI
│       ├── hooks/useAgentStream.ts  # SSE state management
│       ├── lib/api.ts            # API client
│       └── pages/                # Route pages
├── tests/
│   ├── conftest.py
│   └── test_agent.py
├── demo.py                       # End-to-end demo
└── docker-compose.yml
```

## Using a Local LLM (Ollama)

```bash
# Install Ollama
ollama pull codellama

# Set in .env:
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=codellama
```

## Evaluation Scoring Weights

| Dimension      | Weight | Description                        |
|----------------|--------|------------------------------------|
| Correctness    | 35%    | Does it run without errors?        |
| Completeness   | 25%    | All requirements addressed?        |
| Edge Cases     | 20%    | Input validation and errors?       |
| Code Quality   | 10%    | Clean, typed, documented?          |
| Test Pass Rate | 10%    | Fraction of tests passing          |
