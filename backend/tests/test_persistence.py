import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.interview import Interview
from app.models.message import Message
from app.services.interview_service import InterviewService


def _cleanup(session_id: uuid.UUID) -> None:
    with SessionLocal() as db:
        obj = db.get(Interview, session_id)
        if obj is not None:
            msgs = (
                db.execute(
                    select(Message).where(Message.interview_id == session_id)
                )
            ).scalars().all()
            for msg in msgs:
                db.delete(msg)
            db.delete(obj)
            db.commit()


def test_session_persistence_roundtrip():
    service = InterviewService(SessionLocal())
    created = None
    try:
        created = service.create_session(
            user_id=uuid.uuid4(), role_type="Senior Backend Engineer"
        )
        assert created.status == "in_progress"

        fetched = service.get_session(created.id)
        assert fetched is not None and fetched.id == created.id

        service.add_message(
            interview_id=created.id, sender="candidate", transcript="Hello"
        )
        history = service.get_history(created.id)
        assert [m.transcript for m in history] == ["Hello"]

        done = service.complete_session(created.id)
        assert done is not None and done.status == "completed"

        assert service.get_session(uuid.uuid4()) is None
    finally:
        if created is not None:
            _cleanup(created.id)


def test_session_endpoints_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/interview/sessions" in paths
    assert "/api/interview/sessions/{interview_id}" in paths
    assert "/api/interview/sessions/{interview_id}/history" in paths
    assert "/api/interview/sessions/{interview_id}/messages" in paths
    assert "/api/interview/sessions/{interview_id}/complete" in paths
    assert "/api/interview/sessions/{interview_id}/greet" in paths


def test_session_endpoints_live():
    with TestClient(app) as client:
        created = client.post(
            "/api/interview/sessions",
            json={"user_id": str(uuid.uuid4()), "role_type": "Data Scientist"},
        )
        assert created.status_code == 201, created.text
        session_id = created.json()["id"]

        try:
            msg = client.post(
                f"/api/interview/sessions/{session_id}/messages",
                json={"sender": "candidate", "transcript": "I scale with read replicas"},
            )
            assert msg.status_code == 201, msg.text

            history = client.get(f"/api/interview/sessions/{session_id}/history")
            assert history.status_code == 200
            assert [m["transcript"] for m in history.json()] == [
                "I scale with read replicas"
            ]

            bad_sender = client.post(
                f"/api/interview/sessions/{session_id}/messages",
                json={"sender": "alien", "transcript": "x"},
            )
            assert bad_sender.status_code == 400

            missing = client.get(f"/api/interview/sessions/{uuid.uuid4()}/history")
            assert missing.status_code == 404

            done = client.post(f"/api/interview/sessions/{session_id}/complete")
            assert done.status_code == 200
            assert done.json()["status"] == "completed"
        finally:
            _cleanup(uuid.UUID(session_id))


def test_greet_persists_and_returns_audio():

    with TestClient(app) as client:
        created = client.post(
            "/api/interview/sessions", json={"role_type": "Greeter Test"}
        )
        assert created.status_code == 201, created.text
        session_id = created.json()["id"]
        try:
            resp = client.post(f"/api/interview/sessions/{session_id}/greet")
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert "Greeter Test" in body["text"]
            assert body["audio_url"].startswith("/api/interview/audio/greeting_")

            audio = client.get(body["audio_url"])
            assert audio.status_code == 200
            assert len(audio.content) > 1000

            history = client.get(f"/api/interview/sessions/{session_id}/history")
            assert history.status_code == 200
            turns = [(m["sender"], m["transcript"]) for m in history.json()]
            assert turns == [("interviewer", body["text"])]

            missing = client.post(f"/api/interview/sessions/{uuid.uuid4()}/greet")
            assert missing.status_code == 404

            client.delete(body["audio_url"])
        finally:
            _cleanup(uuid.UUID(session_id))


def test_greet_asks_for_role_when_general():
    with TestClient(app) as client:
        created = client.post("/api/interview/sessions", json={})
        assert created.status_code == 201, created.text
        assert created.json()["role_type"] == "General"
        session_id = created.json()["id"]
        try:
            resp = client.post(f"/api/interview/sessions/{session_id}/greet")
            assert resp.status_code == 200, resp.text
            assert "What role are you applying for" in resp.json()["text"]
            client.delete(resp.json()["audio_url"])
        finally:
            _cleanup(uuid.UUID(session_id))


def test_patch_role():
    with TestClient(app) as client:
        created = client.post("/api/interview/sessions", json={})
        session_id = created.json()["id"]
        try:
            patched = client.patch(
                f"/api/interview/sessions/{session_id}",
                json={"role_type": "DevOps Engineer"},
            )
            assert patched.status_code == 200, patched.text
            assert patched.json()["role_type"] == "DevOps Engineer"

            missing = client.patch(
                f"/api/interview/sessions/{uuid.uuid4()}",
                json={"role_type": "DevOps Engineer"},
            )
            assert missing.status_code == 404

            empty = client.patch(
                f"/api/interview/sessions/{session_id}", json={"role_type": ""}
            )
            assert empty.status_code == 422
        finally:
            _cleanup(uuid.UUID(session_id))


def test_role_extraction_from_first_answer():
    from app.api.routes import interviews as interview_routes
    from app.services.llm_service import LLMService

    svc = LLMService()
    captured = {}

    async def fake_generate(messages):
        return "Data Scientist"

    async def fake_stream(messages):
        captured["messages"] = messages
        yield "Noted."

    svc.generate_response = fake_generate  # type: ignore[method-assign]
    svc.stream_response = fake_stream  # type: ignore[method-assign]
    app.dependency_overrides[interview_routes.get_llm_service] = lambda: svc
    try:
        with TestClient(app) as client:
            created = client.post("/api/interview/sessions", json={})
            session_id = created.json()["id"]
            try:
                resp = client.post(
                    "/api/interview/chat/stream",
                    json={
                        "messages": [
                            {"role": "user", "content": "I want to be a data scientist"}
                        ],
                        "interview_id": session_id,
                    },
                )
                assert resp.status_code == 200, resp.text
                system = captured["messages"][0]
                assert system["role"] == "system"
                assert "Data Scientist" in system["content"]
                got = client.get(f"/api/interview/sessions/{session_id}")
                assert got.json()["role_type"] == "Data Scientist"
            finally:
                _cleanup(uuid.UUID(session_id))
    finally:
        app.dependency_overrides.clear()
