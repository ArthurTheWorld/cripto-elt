<#
.SYNOPSIS
    Acompanha os logs do scheduler (onde as tasks rodam).
.EXAMPLE
    .\scripts\logs.ps1
#>
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

docker compose logs -f airflow-scheduler
