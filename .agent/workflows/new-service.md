---
description: Create a new backend service for AXIOM
---

# Create New Backend Service

## Information Needed
- **Service Name**: e.g., "Memory", "Verification", "Economic"
- **Service Type**: Go (backend) or Python (AI)

## Steps for Go Service

1. Create service directory structure
```
apps/api/internal/{service_name}/
├── handler.go      # HTTP handlers
├── service.go      # Business logic
├── repository.go   # Database operations
├── dto.go          # Request/Response DTOs
└── models.go       # Domain models
```

2. Define the service interface in `service.go`:
```go
type {Name}Service interface {
    // Define methods
}
```

3. Register routes in `apps/api/cmd/server/routes.go`

// turbo
4. Run tests
```bash
cd apps/api && go test ./internal/{service_name}/...
```

## Steps for Python AI Service

1. Create service module in `services/ai/app/{service_name}/`

2. Define endpoints in FastAPI router

3. Register in `services/ai/app/main.py`

// turbo
4. Run tests
```bash
cd services/ai && pytest tests/test_{service_name}.py
```
