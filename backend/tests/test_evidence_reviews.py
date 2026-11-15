import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import app.main as main_module
from app.services import storage
from app.services.roadmap import build_roadmap


@pytest.fixture(autouse=True)
def disable_legacy_depth_backfills(monkeypatch):
    monkeypatch.setattr(main_module.config, "ENABLE_SQL_DEPTH", False)
    monkeypatch.setattr(main_module.config, "ENABLE_SKILL_DEPTH", False)


def fake_passport(passport_id: str) -> dict:
    return {
        "id": passport_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "github_username": "demo-user",
        "target_role": "Backend Developer Intern",
        "sources": {"repos": 1, "resume": True, "certificates": 0},
        "skills": [],
        "growth_tasks": [],
        "rejected_claims": [],
        "role_match": {
            "role_id": "backend-developer-intern",
            "role_name": "Backend Developer Intern",
            "requirements": [],
        },
    }


def _client(tmp_path, monkeypatch, passport_id: str = "p-audit") -> TestClient:
    monkeypatch.setattr(storage, "DATABASE_PATH", tmp_path / "test.sqlite")
    monkeypatch.setattr(main_module, "RECRUITER_KEY", "")
    monkeypatch.setattr(main_module, "RECRUITER_ACCOUNTS", {})
    storage.save_passport(fake_passport(passport_id))
    return TestClient(main_module.app)


CITATION = "python:demo:helpers.py:3-7"
BODY = {"skill_id": "python", "citation": CITATION, "status": "verified", "note": "Checked the repo."}


def test_evidence_review_lifecycle(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    created = client.post("/passport/p-audit/evidence-reviews", json=BODY)
    assert created.status_code == 201
    row = created.json()
    assert row["reviewer_id"] and row["created_at"] and row["status"] == "verified"

    states = client.get("/passport/p-audit/evidence-reviews").json()["reviews"]
    assert states[CITATION]["status"] == "verified"
    assert states[CITATION]["note"] == "Checked the repo."

    # A changed decision is a new event, and the latest one wins.
    assert client.post("/passport/p-audit/evidence-reviews",
                       json={**BODY, "status": "flagged", "note": "On second thought."}).status_code == 201
    states = client.get("/passport/p-audit/evidence-reviews").json()["reviews"]
    assert states[CITATION]["status"] == "flagged"

    trail = client.get("/passport/p-audit/audit-trail").json()["events"]
    reviews = [event for event in trail if event["kind"] == "evidence_review"]
    assert [event["status"] for event in reviews] == ["verified", "flagged"]
    assert reviews[0]["note"] == "Checked the repo."
    assert reviews[1]["note"] == "On second thought."
    assert all(event["actor"] == "local-recruiter" for event in reviews)


def test_evidence_review_validation(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    assert client.post("/passport/p-audit/evidence-reviews", json={**BODY, "status": "maybe"}).status_code == 422
    assert client.post("/passport/missing/evidence-reviews", json=BODY).status_code == 404
    empty = client.get("/passport/p-audit/evidence-reviews")
    assert empty.status_code == 200 and empty.json()["reviews"] == {}
    assert client.get("/passport/p-audit/audit-trail").json()["events"] == []


def test_audit_trail_includes_review_requests(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    request, reason = storage.create_review_request("p-audit", "python:demo:old.py:1-9", "Mine.", 3)
    assert reason is None
    storage.mark_review_request_reviewed(request["id"], "recruiter-a")
    client.post("/passport/p-audit/evidence-reviews", json=BODY)

    trail = client.get("/passport/p-audit/audit-trail").json()["events"]
    kinds = [event["kind"] for event in trail]
    assert kinds == ["review_requested", "review_marked_reviewed", "evidence_review"]
    assert trail[0]["actor"] == "student"
    assert trail[1]["actor"] == "recruiter-a"
    # Chronological order.
    assert [event["at"] for event in trail] == sorted(event["at"] for event in trail)


def _passport_for_roadmap() -> dict:
    base = fake_passport("p-roadmap")
    base["role_match"]["requirements"] = [
        {"skill_id": "rest-api", "name": "REST API design", "importance": "must", "status": "missing",
         "student_level": "Claimed", "min_level": "Applied", "reason": "No evidence."},
        {"skill_id": "python", "name": "Python", "importance": "must", "status": "met",
         "student_level": "Demonstrated", "min_level": "Applied", "reason": "Requires Applied."},
        {"skill_id": "git", "name": "Git", "importance": "must", "status": "met",
         "student_level": "Used", "min_level": "Applied", "reason": "Requires Applied."},
        {"skill_id": "docker", "name": "Docker", "importance": "nice", "status": "missing",
         "student_level": "Not found", "min_level": "Used", "reason": "No evidence."},
    ]
    base["growth_tasks"] = [
        {"skill_id": "rest-api", "target_repo": "demo", "task": "Add a REST endpoint.",
         "evidence_it_will_create": "Route files with tests."},
    ]
    return base


def test_roadmap_phases_and_ordering() -> None:
    roadmap = build_roadmap(_passport_for_roadmap())
    assert not roadmap["empty"]
    assert [phase["title"] for phase in roadmap["phases"]] == [
        "Close must-have gaps",
        "Close nice-to-have gaps",
        "Strengthen existing evidence",
    ]
    first = roadmap["phases"][0]["steps"][0]
    assert first["skill_id"] == "rest-api" and first["order"] == 1 and first["effort"] == "M"
    # The growth task becomes the build action, and the plan ends with re-checking.
    assert any("Add a REST endpoint." in action for action in first["actions"])
    assert "Re-check" in first["actions"][-1]
    nice = roadmap["phases"][1]["steps"][0]
    assert nice["skill_id"] == "docker" and nice["effort"] == "S"
    upgrade = roadmap["phases"][2]["steps"][0]
    assert upgrade["skill_id"] == "git" and upgrade["target_level"] == "Applied"
    assert roadmap["total_steps"] == 3


def test_roadmap_empty_when_no_gaps() -> None:
    passport = fake_passport("p-done")
    passport["role_match"]["requirements"] = [
        {"skill_id": "python", "name": "Python", "importance": "must", "status": "met",
         "student_level": "Demonstrated", "min_level": "Applied", "reason": "Met."},
    ]
    roadmap = build_roadmap(passport)
    assert roadmap["empty"] and roadmap["total_steps"] == 0 and roadmap["phases"] == []


def test_student_view_includes_roadmap(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch, passport_id="p-roadmap")
    storage.save_passport(_passport_for_roadmap())
    response = client.get("/passport/p-roadmap")
    assert response.status_code == 200
    roadmap = response.json()["roadmap"]
    assert roadmap["total_steps"] == 3
    assert roadmap["phases"][0]["steps"][0]["skill_id"] == "rest-api"
