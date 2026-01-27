# Build stage
FROM golang:1.24 AS builder

WORKDIR /app

# Install git (often included in standard image, but good to be safe)
# Debian uses apt-get
# RUN apt-get update && apt-get install -y git

# Copy go mod files
COPY go.mod go.sum ./

# Copy vendored dependencies
COPY vendor/ vendor/

# Copy source
COPY . .

# Build with vendor
RUN CGO_ENABLED=0 GOOS=linux go build -mod=vendor -o main ./cmd/server

# Runtime stage
FROM debian:bookworm-slim

WORKDIR /app

# Install ca-certificates for HTTPS
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy binary
COPY --from=builder /app/main .

# Expose port
EXPOSE 8080

# Run
CMD ["./main"]
