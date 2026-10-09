# Start backend + frontend for local development (Windows PowerShell).
# Usage (from repo root imo-ijinle-lms):
#   powershell -File scripts\run.ps1
#   powershell -File scripts\run.ps1 -Seed
#   powershell -File scripts\run.ps1 -BackendPort 8080 -FrontendPort 3000
#
# Requires: uv, pnpm, Node 22+
# Ctrl+C stops both processes.

[CmdletBinding()]
param(
  [switch]$Seed,
  [int]$BackendPort = 8080,
  [int]$FrontendPort = 3000,
  [string]$UseSqlite = "true"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"

function Assert-Command([string]$Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Missing dependency: $Name"
  }
}

# pnpm is often a .ps1 shim; Start-Process needs .cmd/.exe
function Resolve-WinCommand([string]$Name) {
  $fromWhere = @(& where.exe $Name 2>$null)
  $preferred = $fromWhere | Where-Object {
    $_ -like "*.cmd" -or $_ -like "*.exe" -or $_ -like "*.bat"
  } | Select-Object -First 1
  if ($preferred) { return $preferred }

  $cmd = Get-Command $Name -ErrorAction Stop
  $path = $cmd.Source
  if ($path -like "*.ps1") {
    $asCmd = [System.IO.Path]::ChangeExtension($path, ".cmd")
    if (Test-Path $asCmd) { return $asCmd }
  }
  if ($path -like "*.cmd" -or $path -like "*.exe" -or $path -like "*.bat") {
    return $path
  }
  throw "Could not resolve a Win32 launcher for '$Name' (got $path)"
}

function Start-CmdProcess {
  param(
    [string]$WorkingDirectory,
    [string]$CommandLine
  )
  # cmd.exe can run .cmd shims; keeps children attached under this process tree better
  Start-Process -FilePath "cmd.exe" `
    -ArgumentList @("/d", "/c", $CommandLine) `
    -WorkingDirectory $WorkingDirectory `
    -PassThru `
    -NoNewWindow
}

Assert-Command uv
Assert-Command pnpm

$env:USE_SQLITE = $UseSqlite
$env:CELERY_TASK_ALWAYS_EAGER = "true"

$backendProc = $null
$frontendProc = $null

function Stop-DevProcesses {
  Write-Host ""
  Write-Host "Stopping..."
  foreach ($proc in @($script:frontendProc, $script:backendProc)) {
    if ($null -eq $proc) { continue }
    try {
      if (-not $proc.HasExited) {
        # Kill process tree (cmd + children)
        Start-Process -FilePath "taskkill.exe" `
          -ArgumentList @("/PID", "$($proc.Id)", "/T", "/F") `
          -WindowStyle Hidden `
          -Wait `
          -ErrorAction SilentlyContinue | Out-Null
      }
    } catch { }
  }
}

try {
  Write-Host "-> Migrating backend..."
  Push-Location $BackendDir
  try {
    & uv run python manage.py migrate --noinput
    if ($Seed) {
      Write-Host "-> Seeding demo data..."
      & uv run python manage.py seed_demo
    }
  } finally {
    Pop-Location
  }

  $envLocal = Join-Path $FrontendDir ".env.local"
  if (-not (Test-Path $envLocal)) {
    "NEXT_PUBLIC_API_URL=http://localhost:$BackendPort" | Set-Content -Path $envLocal -Encoding ascii
    Write-Host "Wrote frontend/.env.local -> http://localhost:$BackendPort"
  }

  $uvPath = Resolve-WinCommand "uv"
  $pnpmPath = Resolve-WinCommand "pnpm"

  Write-Host "-> Backend  http://localhost:$BackendPort"
  $backendProc = Start-CmdProcess -WorkingDirectory $BackendDir `
    -CommandLine "`"$uvPath`" run python manage.py runserver $BackendPort"

  Write-Host "-> Frontend http://localhost:$FrontendPort"
  # Next.js reads PORT; avoid `pnpm dev -- --port` (Next treats `--` as a directory)
  $frontendProc = Start-CmdProcess -WorkingDirectory $FrontendDir `
    -CommandLine "set PORT=$FrontendPort&& `"$pnpmPath`" dev"

  Write-Host ""
  Write-Host "Running. Demo password: DemoPass123!"
  Write-Host "  student@imoijinle.local  |  superadmin@imoijinle.local"
  Write-Host "Ctrl+C to stop."
  Write-Host ""

  while ($true) {
    Start-Sleep -Seconds 1
    if ($null -ne $backendProc -and $backendProc.HasExited) {
      Write-Host "Backend exited (code $($backendProc.ExitCode))."
      break
    }
    if ($null -ne $frontendProc -and $frontendProc.HasExited) {
      Write-Host "Frontend exited (code $($frontendProc.ExitCode))."
      break
    }
  }
} finally {
  Stop-DevProcesses
}
