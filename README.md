# CODESENTINEL
## 🔍 AI-Powered Autonomous Code Review Platform

> A multi-agent AI system that autonomously reviews GitHub repositories and ZIP archives for bugs, security vulnerabilities, and improvement opportunities — generating structured engineering reports with severity scoring.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-blue)](https://langchain-ai.github.io/langgraph/)
[![Groq](https://img.shields.io/badge/LLM-Groq%20Llama3.3-orange)](https://groq.com)
[![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-purple)](https://www.trychroma.com)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791?logo=postgresql)](https://www.postgresql.org)

---

## 📸 Overview

```
User submits GitHub URL or ZIP
        ↓
Ingestion Pipeline (clone → parse → chunk → embed → ChromaDB)
        ↓
LangGraph Multi-Agent Workflow
  ├── Repository Analysis Agent
  ├── Bug Detection Agent
  ├── Security Review Agent
  ├── Documentation Agent
  └── Final Reviewer Agent
        ↓
Severity-scored Engineering Report (JSON + PDF download)
        ↓
Next.js Dashboard with Agent Timeline
```

---

## ✨ Features

| Feature | Status |
|---|---|
| GitHub URL ingestion (shallow clone) | ✅ |
| ZIP file upload & extraction | ✅ |
| Code-aware chunking + RAG (ChromaDB) | ✅ |
| 5 LangGraph agents (Groq Llama 3.3) | ✅ |
| Bug detection with file citations | ✅ |
| OWASP-aligned security review | ✅ |
| Documentation suggestions | ✅ |
| Severity + confidence scoring (0–100) | ✅ |
| PDF report download | ✅ |
| Agent activity timeline UI | ✅ |
| Demo auth (JWT) | ✅ |
| Docker + GCP deployment | ✅ |
| Vercel frontend deployment | ✅ |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Next.js Frontend                     │
│              (Vercel · TypeScript · Tailwind CSS)           │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│                       FastAPI Backend                       │
│               (Docker · GCP Cloud Run · Python)             │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │  Ingestion  │  │  LangGraph   │  │  Report Engine   │    │
│  │  Pipeline   │  │  5 Agents    │  │  PDF + Scoring   │    │
│  └──────┬──────┘  └──────┬───────┘  └──────────────────┘    │
│         │                │                                  │
│  ┌──────▼──────┐  ┌──────▼───────┐  ┌──────────────────┐    │
│  │  ChromaDB   │  │  Groq LLM    │  │   PostgreSQL      │   │
│  │  (RAG)      │  │  Llama 3.3   │  │   (Jobs/Reports)  │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop
- [Groq API Key](https://console.groq.com) (free)

---

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/codesentinel.git
cd codesentinel
```

---

### 2. Start PostgreSQL (Docker)

```bash
docker run -d \
  --name codereview-pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=codesentinel \
  -p 5432:5432 \
  postgres:16
```
OR
```bash
psql -U postgres -c "CREATE DATABASE codesentinel;"
```

---

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — fill in GROQ_API_KEY and SECRET_KEY

# Start the server
uvicorn app.main:app --reload --port 8000
```

Backend runs at: `http://localhost:8000`
Swagger docs at: `http://localhost:8000/docs`

---

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000

# Start dev server
npm run dev
```

Frontend runs at: `http://localhost:3000`

---

### 5. Demo Login

```
Username: admin
Password: demo1234
```

---

## 📁 Project Structure

```
code-review-platform/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── config.py                  # Settings (pydantic-settings)
│   │   ├── database.py                # Async SQLAlchemy + PostgreSQL
│   │   ├── models/
│   │   │   └── job.py                 # Job, Report, AgentLog ORM models
│   │   ├── routers/
│   │   │   ├── auth.py                # POST /api/auth/login
│   │   │   ├── upload.py              # POST /api/upload/github|zip
│   │   │   ├── jobs.py                # GET  /api/jobs/{id}
│   │   │   └── reports.py             # GET  /api/reports/{id}[/pdf]
│   │   ├── services/
│   │   │   ├── ingestion/
│   │   │   │   ├── github_loader.py   # Git shallow clone
│   │   │   │   ├── zip_loader.py      # ZIP extraction (zip-slip safe)
│   │   │   │   ├── file_parser.py     # File walker + language detector
│   │   │   │   ├── chunker.py         # Overlap chunking for RAG
│   │   │   │   └── orchestrator.py    # Ingestion pipeline coordinator
│   │   │   ├── rag/
│   │   │   │   ├── embedder.py        # HuggingFace all-MiniLM-L6-v2
│   │   │   │   ├── vector_store.py    # ChromaDB CRUD
│   │   │   │   └── retriever.py       # Agent-facing RAG interface
│   │   │   ├── agents/
│   │   │   │   ├── graph.py           # LangGraph StateGraph (Phase 4)
│   │   │   │   ├── state.py           # Shared AgentState TypedDict
│   │   │   │   ├── repo_agent.py      # Repository Analysis
│   │   │   │   ├── bug_agent.py       # Bug Detection
│   │   │   │   ├── security_agent.py  # Security Review (OWASP)
│   │   │   │   ├── docs_agent.py      # Documentation
│   │   │   │   └── reviewer_agent.py  # Final Reviewer + Scoring
│   │   │   └── report/
│   │   │       ├── scorer.py          # Severity/confidence scoring
│   │   │       └── pdf_generator.py   # ReportLab PDF generation
│   │   └── utils/
│   │       ├── logger.py              # Structlog structured logging
│   │       └── auth.py                # JWT demo auth
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                   # Login page
│   │   ├── dashboard/page.tsx         # Main dashboard
│   │   └── analysis/[jobId]/page.tsx  # Per-job results
│   ├── components/
│   │   ├── UploadForm.tsx
│   │   ├── AgentTimeline.tsx
│   │   ├── SeverityBadge.tsx
│   │   ├── ReportViewer.tsx
│   │   └── DownloadButton.tsx
│   └── lib/api.ts
│
├── docker-compose.yml
└── README.md
```

---

## 🔌 API Reference

### Authentication

```http
POST /api/auth/login
Content-Type: application/json

{"username": "admin", "password": "demo1234"}
```

```json
{"access_token": "eyJ...", "token_type": "bearer"}
```

---

### Submit GitHub Repository

```http
POST /api/upload/github
Authorization: Bearer <token>
Content-Type: application/json

{"github_url": "https://github.com/user/repo"}
```

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Analysis started. Poll /api/jobs/{job_id} for status."
}
```

---

### Submit ZIP File

```http
POST /api/upload/zip
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=@project.zip
```

---

### Poll Job Status

```http
GET /api/jobs/{job_id}
Authorization: Bearer <token>
```

```json
{
  "job_id": "550e8400...",
  "status": "analyzing",
  "agent_logs": [
    {"agent_name": "Ingestion", "status": "done", "message": "Source loaded"},
    {"agent_name": "Bug Detection Agent", "status": "started", "message": "Scanning..."}
  ],
  "report_id": null
}
```

Status values: `pending → ingesting → analyzing → done | failed`

---

### Fetch Report

```http
GET /api/reports/{report_id}
Authorization: Bearer <token>
```

```json
{
  "id": "...",
  "severity_score": 72,
  "confidence_score": 88,
  "bugs": {"issues": [...]},
  "security_issues": {"vulnerabilities": [...]},
  "final_review": {"summary": "...", "action_items": [...]}
}
```

---

### Download PDF

```http
GET /api/reports/{report_id}/pdf
Authorization: Bearer <token>
```

Returns: `application/pdf` binary

---

## 🤖 Agent Pipeline

| Agent | Responsibility | RAG Queries |
|---|---|---|
| **Repository Analysis** | Language detection, structure, dependencies | Top-level files, config files |
| **Bug Detection** | Logic errors, null refs, anti-patterns | Function bodies, error handling |
| **Security Review** | OWASP Top 10, secrets, injection risks | Auth code, API routes, DB queries |
| **Documentation** | README gaps, missing docstrings, API docs | Public interfaces, README |
| **Final Reviewer** | Validates all outputs, severity scoring, action items | All agent outputs |

---

## 🐳 Docker

### Local Full Stack

```bash
docker-compose up --build
```

Services started:
- `backend` → `http://localhost:8000`
- `postgres` → `localhost:5432`
- `frontend` → `http://localhost:3000`

---

## ☁️ Deployment

### Backend → GCP Cloud Run

```bash
cd backend

# Build and push image
gcloud builds submit --tag gcr.io/YOUR_PROJECT/code-review-backend

# Deploy
gcloud run deploy code-review-backend \
  --image gcr.io/YOUR_PROJECT/code-review-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GROQ_API_KEY=xxx,DATABASE_URL=xxx,SECRET_KEY=xxx
```

### Frontend → Vercel

```bash
cd frontend
npx vercel --prod
# Set NEXT_PUBLIC_API_URL to your GCP Cloud Run URL
```

---

## 🧪 Testing

```bash
cd backend

# Run all tests
pytest tests/ -v

# Test specific module
pytest tests/test_ingestion.py -v

# With coverage
pytest tests/ --cov=app --cov-report=term-missing
```

---

## 🔒 Security Notes

- All endpoints (except `/health` and `/api/auth/login`) require JWT authorization
- ZIP extraction includes zip-slip attack prevention
- GitHub clones are shallow (`depth=1`) to limit exposure
- Secrets never logged — structured logging masks sensitive fields
- CORS restricted to configured `FRONTEND_URL`

---

## 📊 Evaluation Metrics

| Metric | Target | Method |
|---|---|---|
| Ingestion latency | < 30s for 100-file repo | Timing logs |
| RAG retrieval precision | > 0.75 | Manual spot-check |
| Agent completion rate | > 95% | Job success/fail ratio |
| End-to-end analysis time | < 3 min | Timestamp diff |
| PDF generation | < 5s | Timing |

---

## 🛣️ Future Scope

- **Chat with Repository** — conversational Q&A over embedded codebase
- **PR Diff Analysis** — review only changed files in a pull request
- **CI/CD Integration** — GitHub Actions webhook trigger
- **Private Repo Support** — GitHub OAuth token passthrough
- **ST-GCN Graph Analysis** — structural code graph reasoning
- **Multi-language test generation** — pytest, Jest, JUnit output
- **Team collaboration** — shared workspaces, comment threads on findings

---

## 👨‍💻 Author

Built as a capstone project demonstrating production-grade GenAI system design with multi-agent orchestration, RAG, and full-stack engineering.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
