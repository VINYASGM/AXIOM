$ErrorActionPreference = "Stop"

Write-Host "Checking Backend Health..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8080/health" -Method Get
    Write-Host "✅ Backend is UP and reachable!" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 1)" -ForegroundColor Gray
}
catch {
    Write-Host "❌ Backend is DOWN or unreachable." -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host "`nPlease ensure you ran: cd apps/api; go run ./cmd/server" -ForegroundColor Yellow
    exit 1
}

Write-Host "`nChecking Verifier Connection..." -ForegroundColor Cyan
# Simple TCP check for Verifier
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect("localhost", 50051)
    $tcp.Close()
    Write-Host "✅ Verifier is LISTENING on 50051!" -ForegroundColor Green
}
catch {
    Write-Host "❌ Verifier is DOWN (Port 50051 closed)." -ForegroundColor Red
    Write-Host "Please ensure you ran: cd services/verifier; cargo run" -ForegroundColor Yellow
}
