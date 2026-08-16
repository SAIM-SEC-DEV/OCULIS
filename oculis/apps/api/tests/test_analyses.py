import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from oculis_api.db import Base, database, get_db
from oculis_api.main import app


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(database, "SessionLocal", TestingSessionLocal)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_create_and_get_analysis_are_persistent(client, monkeypatch):
    monkeypatch.setattr(
        "oculis_api.routers.analyses.enqueue_analysis", lambda _analysis_id: "job-1"
    )
    response = client.post("/api/v1/analyses", json={"url": "https://example.com"})
    assert response.status_code == 201
    analysis_id = response.json()["id"]

    result = client.get(f"/api/v1/analyses/{analysis_id}")
    assert result.status_code == 200
    body = result.json()
    assert body["id"] == analysis_id
    assert body["submitted_url"] == "https://example.com"
    assert body["status"] == "queued"


def test_missing_analysis_returns_404(client):
    response = client.get("/api/v1/analyses/not-found")
    assert response.status_code == 404
