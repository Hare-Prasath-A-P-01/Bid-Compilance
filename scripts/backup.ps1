param(
    [string]$OutputDirectory = ".\backups"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outputFile = Join-Path $OutputDirectory "bidcompliance-$timestamp.sql"
$databaseUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "bytebusters" }
$databaseName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "bidcompliance" }

docker compose exec -T db pg_dump `
    -U $databaseUser `
    -d $databaseName | Out-File -Encoding utf8 $outputFile

Write-Output "Database backup written to $outputFile"
