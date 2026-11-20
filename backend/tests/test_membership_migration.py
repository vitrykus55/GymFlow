import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20261120_0001_add_coach_memberships.py"
)


class OperationRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def __getattr__(self, name: str):
        def record(*args: Any, **kwargs: Any) -> None:
            self.calls.append((name, args, kwargs))

        return record


@pytest.fixture
def migration_module() -> ModuleType:
    specification = importlib.util.spec_from_file_location(
        "coach_membership_migration", MIGRATION_PATH
    )
    assert specification is not None
    assert specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_upgrade_rejects_unsupported_roles_before_changing_role_enum(
    monkeypatch: pytest.MonkeyPatch, migration_module: ModuleType
) -> None:
    operations = OperationRecorder()
    monkeypatch.setattr(migration_module, "op", operations)

    migration_module.upgrade()

    statements = [args[0] for name, args, _ in operations.calls if name == "execute"]
    assert statements[0].startswith("DO $$")
    assert "role::text NOT IN ('client', 'trainer')" in statements[0]
    assert "Cannot migrate users.role values" in statements[0]
    assert statements.index("ALTER TYPE user_role RENAME TO user_role_legacy") > 0


def test_upgrade_preserves_only_supported_legacy_role_mappings(
    monkeypatch: pytest.MonkeyPatch, migration_module: ModuleType
) -> None:
    operations = OperationRecorder()
    monkeypatch.setattr(migration_module, "op", operations)

    migration_module.upgrade()

    role_conversion = next(
        args[0]
        for name, args, _ in operations.calls
        if name == "execute" and "ALTER COLUMN role TYPE user_role USING" in args[0]
    )
    assert "WHEN role::text = 'trainer' THEN 'coach'::user_role" in role_conversion
    assert "ELSE 'client'::user_role END" in role_conversion


def test_downgrade_rejects_unsupported_roles_before_changing_role_enum(
    monkeypatch: pytest.MonkeyPatch, migration_module: ModuleType
) -> None:
    operations = OperationRecorder()
    monkeypatch.setattr(migration_module, "op", operations)

    migration_module.downgrade()

    statements = [args[0] for name, args, _ in operations.calls if name == "execute"]
    assert statements[0].startswith("DO $$")
    assert "role::text NOT IN ('client', 'coach')" in statements[0]
