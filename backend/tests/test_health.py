from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["system"] == "air-gapped"
    assert body["status"] in ("ok", "degraded")
    assert set(body["services"]) == {"llm", "stt", "tts", "db"}


def test_interview_routes_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/interview/chat/stream" in paths
    assert "/api/interview/transcribe" in paths
    assert "/api/interview/synthesize" in paths
    assert "/api/interview/audio/{filename}" in paths
    assert "/api/interview/evaluate" in paths
