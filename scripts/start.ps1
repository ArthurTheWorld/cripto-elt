<#
.SYNOPSIS
    Sobe o pipeline inteiro (Airflow + Postgres + datalake S3).
.EXAMPLE
    .\scripts\start.ps1
#>
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Arquivo .env criado a partir do .env.example." -ForegroundColor Yellow
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker não encontrado no PATH. Instale o Docker Desktop e abra-o antes de continuar." -ForegroundColor Red
    Write-Host "  winget install -e --id Docker.DockerDesktop"
    exit 1
}

Write-Host "Subindo containers (a primeira execução compila a imagem do Airflow e demora)..." -ForegroundColor Cyan
docker compose up -d --build

Write-Host ""
Write-Host "Serviços:" -ForegroundColor Green
docker compose ps

Write-Host ""
Write-Host "Airflow ....... http://localhost:8080  (admin / admin)" -ForegroundColor Green
Write-Host "Datalake ...... http://localhost:9001  (admin / admin12345)" -ForegroundColor Green
Write-Host "Warehouse ..... localhost:5433  (dw / dw12345 / warehouse)" -ForegroundColor Green
Write-Host ""
Write-Host "A DAG 'cripto_elt' começa pausada. Ative no Airflow e clique em Trigger." -ForegroundColor Yellow
