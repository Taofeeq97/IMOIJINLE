# Local operations runbook

## Start infrastructure

```powershell
Copy-Item .env.example .env
pwsh -File scripts/dev.ps1
# or: docker compose -f infra/docker-compose.yml up -d
```

For API-only without Docker, set `USE_SQLITE=true` in `.env` and skip Compose.

## Backend

```powershell
cd backend
uv sync --extra dev
$env:USE_SQLITE="true"   # if not using Postgres
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py runserver
```

## Frontend

```powershell
cd frontend
pnpm install
pnpm dev
```

## Reset local SQLite DB

```powershell
Remove-Item backend\dev.sqlite3 -ErrorAction SilentlyContinue
uv run python manage.py migrate
uv run python manage.py seed_demo
```

## Reset Postgres (Compose)

```powershell
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up -d
```

## Email

Mailpit UI: http://localhost:8025 — password reset and magic-link emails appear there in dev.

## Secrets

Never commit `.env`. Rotate `SECRET_KEY`, MinIO credentials, Paystack, Mux, and Google OAuth before any shared environment.
