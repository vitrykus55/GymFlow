# GymFlow

Full-stack застосунок: **Next.js** (frontend) + **FastAPI** (backend) + **PostgreSQL**, усе запускається через **Docker**.

## Структура

```
GymFlow/
├── frontend/                # Next.js 16 (App Router, TypeScript, Tailwind CSS 4)
│   ├── src/app/             # сторінки та layout
│   ├── src/lib/api.ts       # клієнт для запитів до бекенду
│   └── Dockerfile           # таргети: dev / prod
├── backend/                 # FastAPI (Python 3.12)
│   ├── app/
│   │   ├── main.py          # точка входу, CORS, роутери
│   │   ├── core/config.py   # налаштування з env
│   │   ├── db/session.py    # SQLAlchemy engine/session
│   │   └── api/routes/      # ендпоінти (health, …)
│   ├── tests/               # pytest
│   └── Dockerfile           # таргети: dev / prod
├── docker-compose.yml       # dev: hot reload + Postgres
├── docker-compose.prod.yml  # prod-подібний запуск
├── .env.example
└── .github/workflows/ci.yml # CI: lint, тести, build
```

## Швидкий старт (Docker)

```bash
cp .env.example .env
docker compose up --build
```

| Сервіс   | URL                                |
|----------|------------------------------------|
| Frontend | http://localhost:3000              |
| Backend  | http://localhost:8000              |
| API docs | http://localhost:8000/docs         |
| Health   | http://localhost:8000/api/v1/health |
| Postgres | localhost:5432 (gymflow/gymflow)   |

Код фронту й бекенду змонтований у контейнери, тож зміни підхоплюються одразу (hot reload).

Production-збірка:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

## Локальний запуск без Docker

**Backend**

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
pytest            # тести
ruff check .      # лінтер
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

> Після першого `npm install` закомітьте `frontend/package-lock.json`.

## Гілки та workflow

| Гілка       | Призначення |
|-------------|-------------|
| `main`      | **реліз** — стабільний код, лише через Pull Request з `develop` |
| `develop`   | **розробка** — сюди зливаються всі фічі |
| `feature/*` | окрема задача, відгалужується від `develop` |
| `fix/*`     | виправлення багів, від `develop` |
| `hotfix/*`  | термінові виправлення релізу, від `main` (потім злити і в `main`, і в `develop`) |

```bash
git checkout develop && git pull
git checkout -b feature/user-auth
# ... робота, коміти ...
git push -u origin feature/user-auth
# відкрити Pull Request: feature/user-auth → develop
```

Реліз: Pull Request `develop → main`, після злиття — тег версії (`git tag v0.1.0 && git push --tags`).
