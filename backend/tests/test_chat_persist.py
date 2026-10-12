import json
import os
import uuid

from fastapi.testclient import TestClient

from app.api.routes import interviews as interview_routes
from app.main import app
from tests.test_persistence import _cleanup


class FakeLLM:
    async def stream_response(self, messages):
        yield "Hello "
        yield "candidate"


def _override_llm():
    app.dependency_overrides[interview_routes.get_llm_service] = lambda: FakeLLM()
    return app


def test_chat_stream_sse_framing_and_persist():
    _override_llm()
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/interview/sessions", json={"role_type": "QA Engineer"}
            )
            assert created.status_code == 201, created.text
            assert uuid.UUID(created.json()["user_id"])  # auto-generated
            session_id = created.json()["id"]

            try:
                resp = client.post(
                    "/api/interview/chat/stream",
                    json={
                        "messages": [
                            {"role": "user", "content": "Tell me about yourself"}
                        ],
                        "interview_id": session_id,
                    },
                )
                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers["content-type"]
                frames = [
                    line
                    for line in resp.text.splitlines()
                    if line.startswith("data:")
                ]
                assert frames[-1] == "data: [DONE]"
                contents = "".join(
                    json.loads(f[len("data: "):])["content"] for f in frames[:-1]
                )
                assert contents == "Hello candidate"

                history = client.get(
                    f"/api/interview/sessions/{session_id}/history"
                )
                assert history.status_code == 200
                turns = [(m["sender"], m["transcript"]) for m in history.json()]
                assert turns == [
                    ("candidate", "Tell me about yourself"),
                    ("interviewer", "Hello candidate"),
                ]

                missing = client.post(
                    "/api/interview/chat/stream",
                    json={
                        "messages": [{"role": "user", "content": "hi"}],
                        "interview_id": str(uuid.uuid4()),
                    },
                )
                assert missing.status_code == 404
            finally:
                _cleanup(uuid.UUID(session_id))
    finally:
        app.dependency_overrides.clear()


def test_audio_upload_cycle():
    os.makedirs("storage/audio", exist_ok=True)
    path = "storage/audio/_test_ping.wav"
    with open(path, "wb") as fh:
        fh.write(b"RIFF----WAVE")
    try:
        with TestClient(app) as client:
            got = client.get("/api/interview/audio/_test_ping.wav")
            assert got.status_code == 200

            traversal = client.get("/api/interview/audio/..%2F..%2F.env")
            assert traversal.status_code in (400, 404)

            deleted = client.delete("/api/interview/audio/_test_ping.wav")
            assert deleted.status_code == 204
            assert not os.path.exists(path)

            again = client.delete("/api/interview/audio/_test_ping.wav")
            assert again.status_code == 404
    finally:
        if os.path.exists(path):
            os.remove(path)
