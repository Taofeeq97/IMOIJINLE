# Start local infrastructure (Postgres, Redis, MinIO, Mailpit)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$compose = @("compose", "-f", "infra/docker-compose.yml")

Write-Host "Starting MinIO..."
docker @compose up -d minio
Write-Host "Ensuring bucket imo-lms..."
docker @compose run --rm minio-init

$services = @("postgres", "redis", "minio", "mailpit")
Write-Host "Starting infra: $($services -join ', ')"
docker @compose up -d @services

Write-Host ""
Write-Host "Infra ready:"
Write-Host "  Postgres  localhost:5432  (db=imo_lms user=imo password=imo)"
Write-Host "  Redis     localhost:6379"
Write-Host "  MinIO API localhost:9000  console http://localhost:9001  (minio / minio_secret_change_me)"
Write-Host "  Mailpit   SMTP localhost:1025  UI http://localhost:8025"
