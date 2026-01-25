---
description: Add a new API endpoint to AXIOM backend
---

# Add New API Endpoint

## AXIOM API Conventions
- Base: `/api/v1/{resource}`
- Use standard REST verbs
- Always return confidence scores where applicable
- Include request ID in responses

## Steps

1. Define DTO in `apps/api/internal/{service}/dto.go`:
```go
type {Action}Request struct {
    // Fields with validation tags
}

type {Action}Response struct {
    Data      interface{} `json:"data"`
    Confidence float64    `json:"confidence,omitempty"`
}
```

2. Add handler in `apps/api/internal/{service}/handler.go`:
```go
func (h *Handler) Handle{Action}(c *gin.Context) {
    var req {Action}Request
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(400, gin.H{"error": err.Error()})
        return
    }
    // Call service
    result, err := h.service.{Action}(c.Request.Context(), req)
    // Return response
}
```

3. Register route in `apps/api/cmd/server/routes.go`

// turbo
4. Test endpoint
```bash
curl -X POST http://localhost:8080/api/v1/{resource}/{action} \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

## API Checklist
- [ ] Request validation
- [ ] Error handling with proper codes
- [ ] Logging with request ID
- [ ] Confidence score (if AI-related)
