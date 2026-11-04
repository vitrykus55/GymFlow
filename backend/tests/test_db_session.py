from collections.abc import Generator, Iterator
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import session as db_session
from app.main import app


@pytest.fixture
def sqlite_engine() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def session_factory(
    sqlite_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> tuple[sessionmaker[Session], list[tuple[Session, Mock]]]:
    factory = sessionmaker(bind=sqlite_engine, autoflush=False, expire_on_commit=False)
    created_sessions: list[tuple[Session, Mock]] = []

    def create_session() -> Session:
        session = factory()
        close_spy = Mock(wraps=session.close)
        session.close = close_spy
        created_sessions.append((session, close_spy))
        return session

    monkeypatch.setattr(db_session, "SessionLocal", create_session)
    return factory, created_sessions


@pytest.fixture
def records(sqlite_engine: Engine) -> Table:
    table = Table(
        "test_records",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("value", String, nullable=False),
    )
    table.metadata.create_all(sqlite_engine)
    return table


def finish_request(dependency: Generator[Session, None, None]) -> None:
    with pytest.raises(StopIteration):
        next(dependency)


def test_get_db_yields_usable_fresh_sessions_and_closes_them(
    session_factory: tuple[sessionmaker[Session], list[tuple[Session, Mock]]],
) -> None:
    _, created_sessions = session_factory

    first_dependency = db_session.get_db()
    first_session = next(first_dependency)
    assert first_session.execute(text("SELECT 1")).scalar_one() == 1
    finish_request(first_dependency)

    second_dependency = db_session.get_db()
    second_session = next(second_dependency)
    assert second_session.execute(text("SELECT 1")).scalar_one() == 1
    finish_request(second_dependency)

    assert first_session is not second_session
    assert [close_spy.call_count for _, close_spy in created_sessions] == [1, 1]


def test_get_db_closes_session_when_request_raises(
    session_factory: tuple[sessionmaker[Session], list[tuple[Session, Mock]]],
) -> None:
    _, created_sessions = session_factory
    dependency = db_session.get_db()
    next(dependency)

    with pytest.raises(RuntimeError, match="request failed"):
        dependency.throw(RuntimeError("request failed"))

    assert created_sessions[0][1].call_count == 1


def test_caller_commit_persists_changes(
    session_factory: tuple[sessionmaker[Session], list[tuple[Session, Mock]]], records: Table
) -> None:
    factory, _ = session_factory
    dependency = db_session.get_db()
    session = next(dependency)
    session.execute(records.insert().values(value="committed"))
    session.commit()
    finish_request(dependency)

    with factory() as verifier:
        assert verifier.scalar(select(records.c.value)) == "committed"


def test_get_db_does_not_commit_uncommitted_changes(
    session_factory: tuple[sessionmaker[Session], list[tuple[Session, Mock]]], records: Table
) -> None:
    factory, _ = session_factory
    dependency = db_session.get_db()
    session = next(dependency)
    session.execute(records.insert().values(value="uncommitted"))
    finish_request(dependency)

    with factory() as verifier:
        assert verifier.scalar(select(records.c.value)) is None


def test_request_exception_rolls_back_uncommitted_changes(
    session_factory: tuple[sessionmaker[Session], list[tuple[Session, Mock]]], records: Table
) -> None:
    factory, _ = session_factory
    dependency = db_session.get_db()
    session = next(dependency)
    session.execute(records.insert().values(value="rolled back"))

    with pytest.raises(RuntimeError, match="request failed"):
        dependency.throw(RuntimeError("request failed"))

    with factory() as verifier:
        assert verifier.scalar(select(records.c.value)) is None


def test_database_health_endpoint_uses_request_session(
    session_factory: tuple[sessionmaker[Session], list[tuple[Session, Mock]]],
) -> None:
    _, created_sessions = session_factory

    with TestClient(app) as client:
        response = client.get("/api/v1/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}
    assert created_sessions[0][1].call_count == 1
