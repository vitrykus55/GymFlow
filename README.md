# GymFlow

Next.js frontend + FastAPI backend + PostgreSQL, running in Docker.

## Run

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

## Project structure

- `frontend/` – Next.js app
- `backend/` – FastAPI app
- `docker-compose.yml` – local development
- `docker-compose.prod.yml` – production build

## Branches

- `main` – release
- `develop` – development
- `feature/*` – new features, created from `develop`
