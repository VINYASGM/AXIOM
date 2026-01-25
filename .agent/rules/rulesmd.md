---
trigger: always_on
---

# AXIOM Development Rules

## Project Context
AXIOM (Autonomous eXecution with Intent-Oriented Modeling) is a semantic development environment. Read `.gemini/antigravity/brain/*/context.md` and `AXIOM_Comprehensive_Architecture.txt` if you need to restore context.

## Core Principles to Follow
When writing code for AXIOM, always embody:
1. **Intent is Source of Truth** - Code derives from intent, not the other way around
2. **Verification First** - No output without validation
3. **Uncertainty is Visible** - Always surface confidence scores
4. **Everything is Reversible** - Design for undo

## Technology Stack (Do Not Deviate)
| Layer | Stack |
|-------|-------|
| Frontend | Next.js 14, TypeScript, Zustand, Tailwind + Radix UI |
| Backend | Go 1.22, Gin, gRPC, Temporal, GORM |
| AI Services | Python 3.12, FastAPI, LangChain |
| Databases | PostgreSQL 16, Qdrant, Neo4j, Redis |

## Directory Conventions
```
apps/web/          → Frontend (Next.js)
apps/api/          → Backend (Go)
services/ai/       → AI services (Python)
packages/shared/   → Shared types
packages/ui/       → Reusable components
infra/docker/      → Docker configs
```

## Code Style
- **Go**: Follow standard `gofmt`, use dependency injection
- **TypeScript**: Strict mode, prefer `const`, use Zod for validation
- **Python**: Type hints required, use Pydantic models

## Naming Conventions
- **IVCUs**: Intent-Verified Code Units (the atomic unit)
- **Services**: `{Name}Service` (e.g., `IntentService`)
- **Handlers**: `handle{Action}` (e.g., `handleParseIntent`)
- **API routes**: `/api/v1/{resource}/{action}`

## Task Management
- Always update `task.md` in the brain directory when completing items
- Log session progress in the session log table
- Reference `implementation_plan.md` for current phase details

## Auto-Run Commands (// turbo-all)
The following commands are safe to auto-run in this project:
- `go fmt ./...`
- `npm run lint`
- `npm run build`
- `pytest`
- `docker-compose up -d`