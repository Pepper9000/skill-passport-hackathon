import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import app.main as main_module
from app.services import storage


OWNER_TOKEN = "evidence-owner-session-secret"


def fake_passport(passport_id: str) -> dict:
    return {
        "id": passport_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "github_username": "demo-user",
        "target_role": "Backend Developer Intern",
        "sources": {"repos": 1, "resume": True, "certificates": 0},
        "skills": [
            {"skill_id": "python", "name": "Python", "level": "Applied", "evidence": []},
            {"skill_id": "flask", "name": "Flask", "level": "Used", "evidence": []},
        ],
        "growth_tasks": [],
        "rejected_claims": [],
        "role_match": {
            "role_id": "backend-developer-intern",
            "role_name": "Backend Developer Intern",
            "requirements": [],
        },
    }


def _client(tmp_path, monkeypatch, passport_id: str = "p-ask") -> TestClient:
    monkeypatch.setattr(storage, "DATABASE_PATH", tmp_path / "test.sqlite")
    monkeypatch.setattr(main_module, "RECRUITER_KEY", "")
    monkeypatch.setattr(main_module, "RECRUITER_ACCOUNTS", {})
    storage.save_passport(fake_passport(passport_id))
    storage.create_stored_job(
        passport_id,
        target="demo-user",
        access_token_hash=hashlib.sha256(OWNER_TOKEN.encode()).hexdigest(),
    )
    storage.complete_stored_job(passport_id, passport_id, [])
    return TestClient(main_module.app)


ASK = {"skill_id": "python", "note": "Can you share a demo or a walkthrough of the API?"}


def test_evidence_request_lifecycle(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    created = client.post("/passport/p-ask/evidence-requests", json=ASK)
    assert created.status_code == 201
    ask = created.json()
    assert ask["status"] == "open" and ask["recruiter_id"] and ask["created_at"]

    # The student sees the ask on their own passport page.
    student = client.get("/passport/p-ask").json()
    assert [item["id"] for item in student["evidence_requests"]] == [ask["id"]]

    responded = client.post(
        f"/evidence-requests/{ask['id']}/respond",
        json={"response": "Demo at https://example.com/demo, walkthrough in the README."},
        headers={"X-Passport-Token": OWNER_TOKEN},
    )
    assert responded.status_code == 200
    assert responded.json()["status"] == "responded" and responded.json()["responded_at"]

    # The recruiter view carries the answer.
    review = client.get("/passport/p-ask/review").json()
    assert review["evidence_requests"][0]["response"].startswith("Demo at")

    trail = client.get("/passport/p-ask/audit-trail").json()["events"]
    kinds = [event["kind"] for event in trail]
    assert kinds == ["evidence_requested", "evidence_responded"]
    assert trail[0]["skill_id"] == "python"
    assert trail[1]["note"].startswith("Demo at")


def test_evidence_request_validation(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    # Unknown skill and unknown passport.
    assert client.post("/passport/p-ask/evidence-requests", json={"skill_id": "rust"}).status_code == 422
    assert client.post("/passport/missing/evidence-requests", json=ASK).status_code == 404
    # One open ask per skill.
    assert client.post("/passport/p-ask/evidence-requests", json=ASK).status_code == 201
    assert client.post("/passport/p-ask/evidence-requests", json=ASK).status_code == 409
    # A different skill is still allowed.
    assert client.post("/passport/p-ask/evidence-requests", json={"skill_id": "flask"}).status_code == 201
    # Responding twice or to a missing request is rejected.
    assert client.post("/evidence-requests/nope/respond", json={"response": "hi"}).status_code == 404
    assert client.post("/evidence-requests/nope/respond",
                       json={"response": "hi"}, headers={"X-Passport-Token": OWNER_TOKEN}).status_code == 404


def test_evidence_response_requires_owner_token(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    ask = client.post("/passport/p-ask/evidence-requests", json=ASK).json()
    path = f"/evidence-requests/{ask['id']}/respond"
    body = {"response": "Here is the demo."}
    assert client.post(path, json=body, headers={"X-Passport-Token": ""}).status_code == 404
    assert client.post(path, json=body, headers={"X-Passport-Token": "not-the-owner"}).status_code == 404
    assert client.post(path, json=body, headers={"X-Passport-Token": OWNER_TOKEN}).status_code == 200
    # Already answered.
    assert client.post(path, json=body, headers={"X-Passport-Token": OWNER_TOKEN}).status_code == 409
    # An answered skill can be asked about again.
    assert client.post("/passport/p-ask/evidence-requests", json=ASK).status_code == 201


def test_evidence_request_limit(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DATABASE_PATH", tmp_path / "test.sqlite")
    monkeypatch.setattr(main_module, "RECRUITER_KEY", "")
    monkeypatch.setattr(main_module, "RECRUITER_ACCOUNTS", {})
    for index in range(12):
        request, reason = storage.create_evidence_request(
            "p-ask", f"skill-{index}", "", "recruiter-a", 10
        )
        if index < 10:
            assert reason is None and request is not None
        else:
            assert request is None and reason == "limit"
