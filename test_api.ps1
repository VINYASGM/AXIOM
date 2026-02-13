$base = "http://localhost:8080/api/v1"

# 1. Register
$body = @{
    email = "test_script_$(Get-Random)@example.com"
    name = "Test User"
    password = "password123"
} | ConvertTo-Json

try {
    $authParams = @{
        Uri = "$base/auth/register"
        Method = "Post"
        Body = $body
        ContentType = "application/json"
    }
    $auth = Invoke-RestMethod @authParams
    $token = $auth.token
    Write-Host "Registered User. Token: $token"
} catch {
    Write-Host "Registration Failed: $_"
    exit 1
}

$headers = @{
    Authorization = "Bearer $token"
}

# 2. Create Project
$projBody = @{
    name = "Test Project"
} | ConvertTo-Json

try {
    $projParams = @{
        Uri = "$base/projects"
        Method = "Post"
        Headers = $headers
        Body = $projBody
        ContentType = "application/json"
    }
    $project = Invoke-RestMethod @projParams
    $projectId = $project.id
    Write-Host "Created Project: $projectId"
} catch {
    Write-Host "Create Project Failed: $_"
    exit 1
}

# 3. Create IVCU
$ivcuBody = @{
    project_id = $projectId
    raw_intent = "Create a python function to add two numbers"
} | ConvertTo-Json

try {
    $ivcuParams = @{
        Uri = "$base/intent/create"
        Method = "Post"
        Headers = $headers
        Body = $ivcuBody
        ContentType = "application/json"
    }
    $ivcu = Invoke-RestMethod @ivcuParams
    $ivcuId = $ivcu.ivcu_id
    Write-Host "Created IVCU: $ivcuId"
} catch {
    Write-Host "Create IVCU Failed: $_"
    exit 1
}

# 4. Start Generation
$genBody = @{
    ivcu_id = $ivcuId
    language = "python"
} | ConvertTo-Json

try {
    $genParams = @{
        Uri = "$base/generation/start"
        Method = "Post"
        Headers = $headers
        Body = $genBody
        ContentType = "application/json"
    }
    $gen = Invoke-RestMethod @genParams
    $genId = $gen.id
    Write-Host "Started Generation: $genId. Initial Status: $($gen.status)"
} catch {
    Write-Host "Start Generation Failed: $_"
    exit 1
}
Write-Host "SUCCESS"
