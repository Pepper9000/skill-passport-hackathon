import hashlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.main as main_module
from app import config
from app.services import storage

NAMED_KEY = "named_recruiter_secret_32_characters_long"


@pytest.fixture
def regression_env(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATABASE_PATH", tmp_path / "regressions.sqlite")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(config, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(config, "APP_ENV", "production")
    monkeypatch.setattr(config, "GITHUB_TOKEN", "mock-token")
    monkeypatch.setattr(config, "OWNERSHIP_PROOF_SETTING_VALID", True)
    monkeypatch.setattr(config, "REQUIRE_OWNERSHIP_PROOF", True)
    monkeypatch.setattr(config, "RECRUITER_ACCOUNTS_SETTING_VALID", True)
    monkeypatch.setattr(main_module, "REQUIRE_RECRUITER_AUTH", True)
    monkeypatch.setattr(main_module, "RECRUITER_ACCOUNTS", {"lead-recruiter": NAMED_KEY})
    monkeypatch.setattr(config, "DEMO_RECRUITER_USERNAME", "recruiter@techcorp.com")
    monkeypatch.setattr(config, "DEMO_RECRUITER_PASSWORD", "recruiter2026")
    main_module.startup()


def test_default_gemini_model_is_flash_lite():
    assert "gemini-3.5-flash-lite" in config.GEMINI_MODEL


def test_demo_recruiter_is_read_only_and_blocked_from_all_mutations(regression_env):
    with TestClient(main_module.app) as client:
        login = client.post(
            "/auth/recruiter/login",
            json={"username": "recruiter@techcorp.com", "key": "recruiter2026"},
        )
        assert login.status_code == 200
        assert login.json()["read_only"] is True
        headers = {"Authorization": f"Bearer {login.json()['token']}"}

        # 1. Interview generation
        assert client.post(
            "/passport/demo-sample-walkthrough-01/interview-sessions",
            headers=headers,
        ).status_code == 403

        # 2. Assessment
        assert client.put(
            "/interview-sessions/any-session/questions/any-q/assessment",
            headers=headers,
            json={"outcome": "explained_well", "note": ""},
        ).status_code == 403

        # 3. Mark reviewed
        assert client.post(
            "/review-requests/any-request/mark-reviewed",
            headers=headers,
        ).status_code == 403

        # 4. Evidence review
        assert client.post(
            "/passport/demo-sample-walkthrough-01/evidence-reviews",
            headers=headers,
            json={"skill_id": "python", "citation": "any", "status": "verified", "note": "ok"},
        ).status_code == 403

        # 5. Evidence request
        assert client.post(
            "/passport/demo-sample-walkthrough-01/evidence-requests",
            headers=headers,
            json={"skill_id": "python", "note": "Please explain"},
        ).status_code == 403

        # 6. Recheck
        assert client.post(
            "/passport/demo-sample-walkthrough-01/recheck",
            headers=headers,
        ).status_code == 403


def test_named_recruiter_has_write_permissions(regression_env):
    with TestClient(main_module.app) as client:
        login = client.post(
            "/auth/recruiter/login",
            json={"username": "lead-recruiter", "key": NAMED_KEY},
        )
        assert login.status_code == 200
        assert login.json()["read_only"] is False
        assert login.json()["recruiter_id"] == "lead-recruiter"

        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        me = client.get("/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["role"] == "recruiter"
        assert me.json()["read_only"] is False


def test_missing_gemini_api_key_error_message(regression_env, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    with TestClient(main_module.app) as client:
        login = client.post(
            "/auth/recruiter/login",
            json={"username": "lead-recruiter", "key": NAMED_KEY},
        )
        headers = {"Authorization": f"Bearer {login.json()['token']}"}

        response = client.post(
            "/passport/demo-sample-walkthrough-01/interview-sessions",
            headers=headers,
        )
        assert response.status_code == 503
        assert "GEMINI_API_KEY to be configured" in response.json()["detail"]


def test_walkthrough_candidate_structure(regression_env):
    passport = storage.get_passport("demo-sample-walkthrough-01")
    assert passport is not None
    assert passport["is_demo"] is True
    assert passport["github_username"] == "demo-candidate-walkthrough"
    assert passport["sources"]["repos"] == 2
    assert passport["role_match"]["met"] == 4
    assert passport["role_match"]["total"] == 8
    assert len(passport["growth_tasks"]) == 4
    assert len(passport["interview_kit"]) == 2

    # Check skills levels
    levels = {s["skill_id"]: s["level"] for s in passport["skills"]}
    assert levels["python"] == "Demonstrated"
    assert levels["rest-api"] == "Applied"
    assert levels["sql"] == "Applied"
    assert levels["git"] == "Used"
    assert levels["unit-testing"] == "Claimed"
    assert levels["docker"] == "Claimed"
