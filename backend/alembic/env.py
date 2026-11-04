import sys
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

backend_root = Path(__file__).resolve().parents[1]
project_root = backend_root.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# Make the root .env available when Alembic is invoked from backend/ locally.
# Compose-provided environment variables take precedence in the container.
load_dotenv(project_root / ".env", override=False)

from app.core.config import settings  # noqa: E402
from app.db.session import Base, engine  # noqa: E402

# Import model modules here as they are added so their tables register on Base.metadata.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating an Engine."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using the application's configured SQLAlchemy Engine."""
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
