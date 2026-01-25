---
description: Run tests and verification for AXIOM
---

# Test and Verify Changes

## Quick Test Commands

// turbo
1. Run Go backend tests
```bash
cd apps/api && go test ./... -v
```

// turbo
2. Run Python AI service tests
```bash
cd services/ai && pytest -v
```

// turbo
3. Run frontend type check
```bash
cd apps/web && npm run typecheck
```

// turbo
4. Run frontend lint
```bash
cd apps/web && npm run lint
```

// turbo
5. Build frontend
```bash
cd apps/web && npm run build
```

## Full Integration Test

1. Ensure all services are running
```bash
docker-compose ps
```

2. Test intent parsing flow:
```bash
curl -X POST http://localhost:8080/api/v1/intent/parse \
  -H "Content-Type: application/json" \
  -d '{"raw_intent": "Create a function that adds two numbers"}'
```

3. Verify response includes:
- `parsed_intent` object
- `confidence` score (0-1)
- `suggested_refinements` array

## Verification Tiers (Per Architecture)
- **Tier 1** (<2s): Syntax, Types, Lint
- **Tier 2** (2-15s): Tests, Property checks
- **Tier 3** (15s-5min): SMT, Security, Fuzz
