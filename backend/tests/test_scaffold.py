from fastapi.testclient import TestClient

from nexus import __version__
from nexus.api.app import create_app


def test_app_factory_creates_fastapi_app() -> None:
    app = create_app()

    assert app.title == "NEXUS AI API"


def test_package_version_is_pinned() -> None:
    assert __version__ == "0.1.0"


def test_health_returns_liveness_without_external_services() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unimplemented_readiness_is_not_reported_as_ready() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/ready")

    assert response.status_code == 404
