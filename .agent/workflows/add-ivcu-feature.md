---
description: Add a feature to the IVCU (Intent-Verified Code Unit) system
---

# Add IVCU Feature

## What is an IVCU?
The atomic unit of AXIOM that bundles:
- Raw intent + parsed intent
- Contracts (formal constraints)
- Verification result + confidence score
- Generated code
- Provenance (model, version, hashes)

## Steps

1. Update IVCU model if needed (`apps/api/internal/models/ivcu.go`)

2. Update database migration in `infra/migrations/`

// turbo
3. Run migration
```bash
cd apps/api && go run cmd/migrate/main.go
```

4. Update Intent Service to handle new feature

5. Update Review Panel UI to display new feature

// turbo
6. Test the feature
```bash
go test ./internal/intent/... -v
```

## IVCU Lifecycle States
```
Draft → Generating → Verifying → Verified → Deployed
                               ↓
                            Failed
                               ↓
                          Deprecated
```

## Confidence Score Guidelines
- 0.0-0.3: Low confidence, needs review
- 0.3-0.7: Medium, acceptable for non-critical
- 0.7-0.9: High, production-ready
- 0.9-1.0: Very high, fully verified
