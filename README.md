# GymFlow

GymFlow is a Next.js frontend and FastAPI backend. The local development stack runs in Docker and connects the backend to Neon PostgreSQL.

## Run locally on Windows

1. Copy `.env.example` to `.env`:

   ```powershell
   Copy-Item .env.example .env
   ```

2. In `.env`, set `DATABASE_URL` to the pooled Neon URL for application requests and `DATABASE_URL_UNPOOLED` to the direct URL for Alembic migrations. Use URLs from the same Neon branch. Set `JWT_SECRET_KEY` to a private random value of at least 32 characters. Never commit `.env` or share these values.

3. If this is a **new, empty Neon database**, apply the project migrations from `backend/`:

   ```powershell
   Set-Location backend
   python -m alembic upgrade head
   Set-Location ..
   ```

   The baseline migration creates the initial tables. If the selected Neon database already contains tables or data, do **not** run this baseline blindly; first verify its schema and migration state with the team.

4. Start the frontend and backend:

   ```powershell
   docker compose up --build
   ```

Open <http://localhost:3000>. The page displays backend and Neon connection status. Registering through the form sends the user's details to FastAPI, which stores the client and a password hash in Neon. The API docs are available at <http://localhost:8000/docs>.

Stop the stack with `Ctrl+C`, then run `docker compose down`.

## Project structure

- `frontend/` – Next.js application and registration/login form.
- `backend/` – FastAPI API, authentication, and SQLAlchemy models.
- `backend/alembic/` – versioned database migrations.
- `docker-compose.yml` – local development connected to Neon.
- `docker-compose.prod.yml` – production-like stack with its own PostgreSQL container.

## Branches

- `main` – release.
- `develop` – development.
- `feature/*` – features created from `develop`.
