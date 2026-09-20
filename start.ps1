# AcadEval+ canonical development startup
# Usage: .\start.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile = Join-Path $Root ".env"

if (-not (Test-Path $EnvFile)) {
    Write-Host "Missing .env. Creating it from .env.example." -ForegroundColor Yellow
    Copy-Item (Join-Path $Root ".env.example") $EnvFile
    Write-Host "Set the required database, Neo4j, JWT, and optional demo-user secrets in .env, then run this script again." -ForegroundColor Yellow
    exit 1
}

Set-Location $Root
docker compose up --build -d

Write-Host ""
Write-Host "AcadEval+ is starting:" -ForegroundColor Cyan
Write-Host "  Frontend:  http://localhost:5173"
Write-Host "  API docs:  http://localhost:8000/docs"
Write-Host "  Neo4j:     http://localhost:7474"
Write-Host ""
Write-Host "Use 'docker compose logs -f' to follow startup progress." -ForegroundColor DarkGray
