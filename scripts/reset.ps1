<#
.SYNOPSIS
    Derruba tudo e APAGA os dados (containers + volumes).
.EXAMPLE
    .\scripts\reset.ps1
#>
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$resposta = Read-Host "Isso apaga o Postgres e o data lake. Digite 'sim' para confirmar"
if ($resposta -ne "sim") {
    Write-Host "Cancelado." -ForegroundColor Yellow
    exit 0
}

docker compose down -v --remove-orphans

Write-Host "Ambiente limpo. Rode .\scripts\start.ps1 para subir de novo." -ForegroundColor Green
