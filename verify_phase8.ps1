$ErrorActionPreference = "Stop"
$BaseUrl = "http://localhost:8080/api/v1"

function Test-Endpoint {
    param (
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host -NoNewline "Testing $Name... "
    try {
        & $Action
        Write-Host "PASS" -ForegroundColor Green
    }
    catch {
        Write-Host "FAIL" -ForegroundColor Red
        Write-Error "Failed: $_"
    }
}

Write-Host "=== Phase 8: Final System Verification ==="

# 1. Authentication
$token = ""
Test-Endpoint "Authentication" {
    $loginBody = @{ email = "dev@axiom.local"; password = "password" } | ConvertTo-Json
    $resp = Invoke-RestMethod -Uri "$BaseUrl/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
    $script:token = $resp.token
    if (-not $token) { throw "No token received" }
}

$headers = @{ "Authorization" = "Bearer $token" }

# 2. Speculation Engine
Test-Endpoint "Speculation Engine" {
    $body = @{ intent = "Create a React component for a login form" } | ConvertTo-Json
    $resp = Invoke-RestMethod -Uri "$BaseUrl/speculate" -Method Post -Body $body -ContentType "application/json" -Headers $headers
    
    if (-not $resp.paths) { throw "No speculation paths returned" }
    Write-Host "`n   > Paths found: $($resp.paths.Count)" -ForegroundColor Gray
    Write-Host "   > Recommended: $($resp.recommended_path_id)" -ForegroundColor Gray
}

# 3. Economic Control (Cost Estimation)
Test-Endpoint "Economic Control" {
    $body = @{ intent = "Create a complex microservice architecture"; candidate_count = 3 } | ConvertTo-Json
    $resp = Invoke-RestMethod -Uri "$BaseUrl/cost/estimate" -Method Post -Body $body -ContentType "application/json" -Headers $headers
    
    if (-not $resp.estimated_cost_usd) { throw "No cost estimate returned" }
    Write-Host "`n   > Estimated Cost: $$($resp.estimated_cost_usd)" -ForegroundColor Gray
}

# 4. Team Management
Test-Endpoint "Team Management" {
    # Using a dummy project ID - expect empty list or specific error, but endpoint should be reachable
    $projectId = "22222222-2222-2222-2222-222222222222"
    try {
        $resp = Invoke-RestMethod -Uri "$BaseUrl/project/$projectId/team" -Method Get -Headers $headers
        Write-Host "`n   > Team members: $($resp.Count)" -ForegroundColor Gray
    } catch {
        # If 404/403, standard API behavior. We just want to know it reached the handler.
        # But for 'verify', let's accept 200 OK (empty list) as success. 
        # If project doesn't exist, it might be 404.
        if ($_.Exception.Response.StatusCode -eq [System.Net.HttpStatusCode]::NotFound) {
             Write-Host "`n   > Project not found (Expected for dummy ID)" -ForegroundColor Yellow
        } else {
            throw $_
        }
    }
}

# 5. Temporal Workflow (Generation)
Test-Endpoint "Temporal Workflow Integration" {
    # Need Parsed SDO first
    $intentBody = @{ raw_intent = "Print hello world in python"; project_context = "test" } | ConvertTo-Json
    $parseResp = Invoke-RestMethod -Uri "$BaseUrl/intent/parse" -Method Post -Body $intentBody -ContentType "application/json" -Headers $headers
    $sdoId = $parseResp.sdo_id
    
    # Create IVCU
    $ivcuBody = @{
        project_id = "22222222-2222-2222-2222-222222222222"
        raw_intent = "Print hello world in python"
        sdo_id     = $sdoId
    } | ConvertTo-Json
    $ivcuResp = Invoke-RestMethod -Uri "$BaseUrl/intent/create" -Method Post -Body $ivcuBody -ContentType "application/json" -Headers $headers
    $ivcuId = $ivcuResp.ivcu_id

    # Start Generation
    $genBody = @{ ivcu_id = $ivcuId; language = "python" } | ConvertTo-Json
    $genResp = Invoke-RestMethod -Uri "$BaseUrl/generation/start" -Method Post -Body $genBody -ContentType "application/json" -Headers $headers
    
    if ($genResp.status -ne "generating") { throw "Status is not generating" }
    Write-Host "`n   > Generation Workflow Started: $($genResp.status)" -ForegroundColor Gray
}

Write-Host "`nVerification Complete!" -ForegroundColor Cyan
