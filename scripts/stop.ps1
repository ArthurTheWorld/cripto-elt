<#
.SYNOPSIS
    Para os containers preservando os dados (volumes).
.EXAMPLE
    .\scripts\stop.ps1
#>
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

docker compose down

Write-Host "Containers parados. Volumes preservados." -ForegroundColor Yellow
