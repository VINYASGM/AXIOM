# AXIOM

> **Autonomous eXecution with Intent-Oriented Modeling**

A semantic development environment where humans express verified intent and AI generates, proves, and maintains implementations.

---

## 🚀 Quick Start

### Prerequisites
- Node.js 20+
- Go 1.22+
- Python 3.12+
- Docker Desktop

### 1. Clone and Setup
```bash
cd Axiom
cp .env.example .env
# Edit .env with your OpenAI/Anthropic API keys
```

### 2. Start Infrastructure
```bash
docker-compose up -d postgres redis qdrant
```

### 3. Install Dependencies
```bash
# Frontend
cd apps/web && npm install

# AI Service
cd services/ai && pip install -r requirements.txt
```

### 4. Run Services
```bash
# Terminal 1: Go API
cd apps/api && go run cmd/server/main.go

# Terminal 2: AI Service
cd services/ai && python main.py

# Terminal 3: Frontend
cd apps/web && npm run dev
```

### 5. Open AXIOM
Visit http://localhost:3000

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        AXIOM Platform                        │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Next.js)                                          │
│  IntentCanvas │ ReviewPanel │ ConfidenceIndicator           │
├─────────────────────────────────────────────────────────────┤
│  API Gateway (Go/Gin)                                        │
│  Auth │ Intent │ Generation │ Verification                   │
├─────────────────────────────────────────────────────────────┤
│  AI Service (Python/FastAPI)                                 │
│  Intent Parsing │ Code Generation │ LLM Integration          │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure                                              │
│  PostgreSQL │ Redis │ Qdrant                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
Axiom/
├── apps/
│   ├── web/              # Next.js 14 frontend
│   └── api/              # Go backend services
├── services/
│   └── ai/               # Python AI service
├── packages/
│   ├── shared/           # Shared TypeScript types
│   └── ui/               # Reusable UI components
├── infra/
│   └── docker/           # Docker configs & SQL
├── docker-compose.yml    # Local development
└── turbo.json            # Turborepo config
```

---

## 🔑 Core Concepts

### IVCU (Intent-Verified Code Unit)
The atomic unit of AXIOM that bundles:
- Raw intent + parsed intent
- Contracts (formal constraints)
- Verification result + confidence score
- Generated code + provenance

### 7 Foundational Principles
1. **Intent is Source of Truth** - Code derives from intent
2. **Verification Precedes Visibility** - No unverified output
3. **Uncertainty is Visible** - Confidence scores everywhere
4. **Control is Continuous** - Trust dial 1-10
5. **Consequences Visible** - Impact preview before commits
6. **Everything Reversible** - All actions can undo
7. **Understanding Preserved** - Builds competence, not dependency

---

## 🛠️ API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Authenticate |
| POST | `/api/v1/intent/parse` | Parse raw intent |
| POST | `/api/v1/intent/create` | Create IVCU |
| GET | `/api/v1/intent/:id` | Get IVCU |
| POST | `/api/v1/generation/start` | Start generation |
| GET | `/api/v1/generation/:id/status` | Check status |
| POST | `/api/v1/verification/verify` | Run verification |

---

## 🎨 Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind, Zustand, Framer Motion |
| Backend | Go 1.22, Gin, JWT |
| AI | Python 3.12, FastAPI, OpenAI/Anthropic |
| Database | PostgreSQL 16, Redis 7, Qdrant |

---

## 📖 Documentation

- [Architecture Document](./AXIOM_Comprehensive_Architecture.txt)
- [Development Rules](./.gemini/rules.md)
- [Workflows](./.agent/workflows/)

---

## 📝 License

MIT © 2026 AXIOM Project
