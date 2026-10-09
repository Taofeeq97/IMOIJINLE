# Imo Ijinle Academy LMS

Monorepo for the Spirit Science / Educational Portal (Django API + Next.js). Architecture and specs live under [`docs/`](docs/ARCHITECTURE.md).

**Goal:** local setup in under 10 minutes.

## Prerequisites

| Tool | Version |
|------|---------|
| [Docker](https://docs.docker.com/get-docker/) | Desktop or Engine |
| [uv](https://docs.astral.sh/uv/) | latest |
| [Node.js](https://nodejs.org/) | 22+ |
| [pnpm](https://pnpm.io/) | 9+ |
| `make` | optional on Windows (use `scripts/dev.ps1`) |

## 1. Infrastructure (Postgres, Redis, MinIO, Mailpit)

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml run --rm minio-init
```

Windows (PowerShell):

```powershell
Copy-Item .env.example .env
pwsh -File scripts/dev.ps1
```

## 2. Run app (backend + frontend)

One-shot local servers (SQLite by default, API on **8080** to match `frontend/.env.local`).

**Windows (PowerShell)** — from `imo-ijinle-lms/`:

```powershell
powershell -File scripts\run.ps1 -Seed
```

**macOS / Linux / Git Bash:**

```bash
chmod +x scripts/run.sh
./scripts/run.sh --seed
```

| Flag / env | Purpose |
|------------|---------|
| `-Seed` / `--seed` | Run `seed_demo` before start |
| `-BackendPort` / `BACKEND_PORT` | Default `8080` |
| `-FrontendPort` / `FRONTEND_PORT` | Default `3000` |
| `-UseSqlite` / `USE_SQLITE` | Default `true` |

Ctrl+C stops both. Or start each side manually:

### Backend only

```bash
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo
USE_SQLITE=true uv run python manage.py runserver 8080
```

API: [http://localhost:8080](http://localhost:8080) · OpenAPI UI: [http://localhost:8080/api/docs/](http://localhost:8080/api/docs/)

### Frontend only

```bash
cd frontend
pnpm install
pnpm dev
```

Web app: [http://localhost:3000](http://localhost:3000)

## Local URLs

| Service | URL |
|---------|-----|
| Web | http://localhost:3000 |
| API (`./scripts/run.sh`) | http://localhost:8080 |
| API docs (Swagger) | http://localhost:8080/api/docs/ |
| Mailpit (email UI) | http://localhost:8025 |
| MinIO console | http://localhost:9001 |

## Seeded demo logins

Password for every account: **`DemoPass123!`** (local development only).

| Role | Email |
|------|-------|
| Super Admin | `superadmin@imoijinle.local` |
| Program Admin | `programadmin@imoijinle.local` |
| Finance Admin | `financeadmin@imoijinle.local` |
| Tutor | `tutor@imoijinle.local` |
| Teaching Assistant | `ta@imoijinle.local` |
| Student | `student@imoijinle.local` |
| Observer | `observer@imoijinle.local` |
| Applicant | `applicant@imoijinle.local` |

Created by `manage.py seed_demo` (see [D-013](docs/DECISIONS.md)).

## Make targets

Run from the repo root:

| Target | Description |
|--------|-------------|
| `make dev` | Start infra services + ensure MinIO bucket |
| `make down` | Stop compose stack |
| `make migrate` | Django migrations (`backend/`) |
| `make seed` | Run `seed_demo` |
| `make test` | Backend pytest + frontend vitest |
| `make lint` | Ruff + frontend lint |
| `make typecheck` | mypy + `pnpm typecheck` |
| `make gen-api` | Fetch OpenAPI from running API → TypeScript types |
| `make e2e` | Playwright tests |
| `make bootstrap` | `dev` + `migrate` + `seed` |

## Project layout

```
backend/          Django 5 + DRF (built by backend agent)
frontend/         Next.js App Router (built by frontend agent)
infra/            Docker Compose, Dockerfiles, CI helpers
docs/             Architecture, decisions, specs, runbook
```

## Further reading

- [Architecture](docs/ARCHITECTURE.md)
- [Runbook](docs/RUNBOOK.md)
- [Decisions](docs/DECISIONS.md)
