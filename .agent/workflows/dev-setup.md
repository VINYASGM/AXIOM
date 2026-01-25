---
description: Set up AXIOM development environment from scratch
---

# Development Environment Setup

## Prerequisites
Ensure you have installed: Node.js 20+, Go 1.22+, Python 3.12+, Docker Desktop

## Steps

1. Navigate to project root
```bash
cd "c:\Users\Vinyas G M\OneDrive\Desktop\Axiom"
```

// turbo
2. Start infrastructure containers
```bash
docker-compose up -d postgres redis qdrant
```

// turbo
3. Install frontend dependencies
```bash
cd apps/web && npm install
```

// turbo
4. Install AI service dependencies
```bash
cd services/ai && pip install -r requirements.txt
```

// turbo
5. Run database migrations
```bash
cd apps/api && go run cmd/migrate/main.go
```

6. Start all services
```bash
docker-compose up
```

## Verification
- Frontend: http://localhost:3000
- API: http://localhost:8080/health
- AI Service: http://localhost:8000/health
- Qdrant: http://localhost:6333/dashboard
