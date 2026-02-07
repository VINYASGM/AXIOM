# Check if Docker is running
docker info > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

Write-Host "Starting Infrastructure (Postgres, Redis, NATS, Qdrant)..." -ForegroundColor Green
docker-compose up -d postgres redis nats qdrant ai

Write-Host "`nInfrastructure is UP!" -ForegroundColor Cyan
Write-Host "Now start the services in separate terminals:" -ForegroundColor Yellow
Write-Host "1. Backend:   cd apps/api; go run ./cmd/server"
Write-Host "2. Frontend:  cd apps/web-next; npm run dev"
Write-Host "3. Verifier:  cd services/verifier; cargo run"
