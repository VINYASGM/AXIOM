$ErrorActionPreference = "Stop"

function Test-SDOFlow {
    param (
        [string]$BaseUrl = "http://localhost:8080/api/v1"
    )

    Write-Host "`n0. Authenticating..."
    $loginBody = @{
        email    = "dev@axiom.local"
        password = "password"
    } | ConvertTo-Json
    
    try {
        $loginResp = Invoke-RestMethod -Uri "$BaseUrl/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
        $token = $loginResp.token
        Write-Host "   Logged in successfully. Token length: $($token.Length)"
        $headers = @{ "Authorization" = "Bearer $token" }
    }
    catch {
        Write-Error "Login failed: $_"
        return
    }

    Write-Host "`n1. Parsing Intent..."
    $intentBody = @{
        raw_intent      = "Create a python function that calculates fibonacci sequence up to n"
        project_context = "test_project"
    } | ConvertTo-Json

    $parseResp = Invoke-RestMethod -Uri "$BaseUrl/intent/parse" -Method Post -Body $intentBody -ContentType "application/json" -Headers $headers
    $sdoId = $parseResp.sdo_id
    Write-Host "   SDO ID Received: $sdoId"
    Write-Host "   Parsed Intent: $($parseResp.parsed_intent.description)"

    Write-Host "`n2. Creating Project (if needed)..."
    # Create a dummy project for testing
    $projectBody = @{
        name     = "SDO Verification Project"
        owner_id = $loginResp.user.id # Assuming login returns user
    } | ConvertTo-Json
    
    # We might not have a create-project endpoint exposed in main.go yet? 
    # Let's check main.go routes. 
    # It has auth, intent, generation, verification. NO Project management endpoints yet in main.go!
    # But intent creation needs a project_id.
    # We can use the user's ID as project ID temporarily or insert one manually via SQL if needed.
    # OR, we assume a project exists.
    # Let's inspect the DB actually.
    
    Write-Host "   Skipping Create Project - assuming we can use a placeholder for now or need to seed DB."
    # For now, let's just generate a random UUID for project_id, it might fail FK constraint.
    # We MUST have a valid project_id.
    # I'll query the DB for a project ID or insert one.
    
    Write-Host "`n3. Creating IVCU..."
    $projectUuid = "22222222-2222-2222-2222-222222222222" # Seeded Project ID
    
    $ivcuBody = @{
        project_id = $projectUuid
        raw_intent = "Create a python function that calculates fibonacci sequence up to n"
        contracts  = @()
        sdo_id     = $sdoId
    } | ConvertTo-Json

    try {
        $ivcuResp = Invoke-RestMethod -Uri "$BaseUrl/intent/create" -Method Post -Body $ivcuBody -ContentType "application/json" -Headers $headers
        $ivcuId = $ivcuResp.ivcu_id
        Write-Host "   IVCU Created: $ivcuId"
        
        Write-Host "`n4. Starting Generation..."
        $genBody = @{
            ivcu_id  = $ivcuId
            language = "python"
        } | ConvertTo-Json
        
        $genResp = Invoke-RestMethod -Uri "$BaseUrl/generation/start" -Method Post -Body $genBody -ContentType "application/json" -Headers $headers
        Write-Host "   Generation Started: $($genResp.status)"
        
    }
    catch {
        Write-Host "   step failed: $_"
    }
}

Write-Host "Simulating SDO Flow verification..."
# curl equivalent checking health
$health = Invoke-RestMethod -Uri "http://localhost:8080/health" -Method Get
Write-Host "API Health: $($health.status)"

Test-SDOFlow
