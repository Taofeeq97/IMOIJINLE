# Backend for Imo Ijinle Academy LMS

## Setup

```bash
uv sync --extra dev
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py runserver
```

API docs: http://localhost:8000/api/docs/
