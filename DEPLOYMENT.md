# AXIOM Deployment Guide

This guide covers the deployment process for the AXIOM platform, including local development, production readiness, and CI/CD pipelines.

## Prerequisites

- **Docker & Docker Compose**: v24.0+
- **Go**: v1.22+ (for local backend dev)
- **Node.js**: v20+ (for frontend)
- **Python**: v3.12+ (for AI service)

## Quick Start (Local Production-Like Env)

To bring up the entire stack including databases, API, AI services, and observability tools:

```bash
# 1. Clone repository
git clone https://github.com/VINYASGM/AXIOM.git
cd AXIOM

# 2. Configure Environment
cp services/ai/.env.example services/ai/.env
# Update API Keys in services/ai/.env

# 3. Start Services
docker-compose up -d --build
```

Access the services:
- **Frontend**: http://localhost (via Nginx)
- **API**: http://localhost/api/
- **Grafana**: http://localhost:3001 (User: admin/admin)
- **Temporal UI**: http://localhost:8088

## Database Migrations

The database schema is managed via Go migrations in `apps/api/migrations`.

To apply migrations manually (if not handled by the app on startup):
```bash
# Install golang-migrate
go install -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate@latest

# Run migrations
migrate -path apps/api/migrations -database "postgresql://axiom:axiom_dev_password@localhost:5433/axiom?sslmode=disable" up
```

## CI/CD Pipeline

The project uses **GitHub Actions** located in `.github/workflows/ci.yml`.

### Triggers
- Pushes to `main`
- Pull Requests to `main`

### Jobs
1. **Backend Tests**: Runs Go unit tests and `golangci-lint`.
2. **Frontend Build**: Installs dependencies, lints, and builds the Vite app.
3. **Docker Build**: Verifies that all `Dockerfile`s build successfully (dry run).

## Observability

The stack includes a full Grafana/Prometheus/Loki/Tempo suite.

- **Dashboards**: Pre-provisioned in `infra/docker/config/grafana-dashboard.json`.
- **Logs**: Ship to Loki via Promtail.
- **Traces**: Sent to Tempo from the API and AI services.

## Production Considerations

1. **Security**:
   - Change default passwords in `docker-compose.yml` (`POSTGRES_PASSWORD`, `GF_SECURITY_ADMIN_PASSWORD`).
   - Use a secrets manager for API keys (e.g., Docker Swarm Secrets or K8s Secrets).
   - Enable SSL/TLS in Nginx.

2. **Scaling**:
   - The `ai-worker` service can be scaled horizontally to handle more concurrent intent generations.
   - `docker-compose up -d --scale ai-worker=3`

3. **Backup**:
   - Regularly backup `postgres_data` and `qdrant_data` volumes.
