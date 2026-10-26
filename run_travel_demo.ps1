$ErrorActionPreference = "Stop"

$baseUrl = "http://127.0.0.1:8000"
$request = @{
    task = "Plan my trip"
    travel = @{
        origin = "Berlin"
        destination = "Paris"
        days = 4
        travelers = 2
        budget = 2000
        currency = "EUR"
    }
} | ConvertTo-Json -Depth 5

Write-Host "Creating travel plan..." -ForegroundColor Cyan
$run = Invoke-RestMethod -Method Post `
    -Uri "$baseUrl/runs" `
    -ContentType "application/json" `
    -Body $request

Write-Host "Run ID: $($run.run_id)" -ForegroundColor Yellow
Write-Host "Status: $($run.status)" -ForegroundColor Yellow

if ($run.status -eq "awaiting_approval") {
    Write-Host "The plan is waiting for human approval." -ForegroundColor Cyan
    $decision = Read-Host "Approve this travel plan? (y/n)"
    $approvedValue = $decision -match "^(y|yes)$"
    $approved = Invoke-RestMethod -Method Post `
        -Uri "$baseUrl/runs/$($run.run_id)/resume" `
        -ContentType "application/json" `
        -Body (@{ approved = $approvedValue } | ConvertTo-Json)
} else {
    $approved = $run
}

Write-Host ""
Write-Host "Final result" -ForegroundColor Green
Write-Host "Status: $($approved.status)"
Write-Host "Response: $($approved.response)"
Write-Host ""
Write-Host "Audit trail:" -ForegroundColor Green
$approved.audit | ForEach-Object { Write-Host "- $_" }
