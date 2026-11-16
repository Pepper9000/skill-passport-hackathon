from datetime import datetime, timedelta, timezone
import hashlib
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.main as main_module
from app import config
from app.services import demo_seed, storage

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


def _seed_real_candidate():
    sample = demo_seed._build_walkthrough_sample()
    sample["id"] = "real-student-passport-01"
    sample["github_username"] = "real-student-dev"
    sample["is_demo"] = False
    with storage._connect() as conn:
        storage._save_passport(conn, sample)
    return sample


def test_default_gemini_model_is_flash_lite():
    assert "gemini-3.5-flash-lite" in config.GEMINI_MODEL


def test_demo_recruiter_permissions_and_narrow_scope(regression_env):
    with TestClient(main_module.app) as client:
        login = client.post(
            "/auth/recruiter/login",
            json={"username": "recruiter@techcorp.com", "key": "recruiter2026"},
        )
        assert login.status_code == 200
        assert login.json()["read_only"] is True
        headers = {"Authorization": f"Bearer {login.json()['token']}"}

        # 1. Permitted action: generate interview session for demo candidate
        gen_resp = client.post(
            "/passport/demo-sample-walkthrough-01/interview-sessions",
            headers=headers,
        )
        assert gen_resp.status_code == 201
        session_data = gen_resp.json()
        assert session_data["passport_id"] == "demo-sample-walkthrough-01"
        assert session_data["is_demo"] is True
        assert len(session_data["questions"]) > 0
        q_id = session_data["questions"][0]["id"]
        session_id = session_data["id"]

        # 2. Permitted action: assess interview question for demo session
        assess_resp = client.put(
            f"/interview-sessions/{session_id}/questions/{q_id}/assessment",
            headers=headers,
            json={"outcome": "explained_well", "note": "Great explanation of Pydantic models."},
        )
        assert assess_resp.status_code == 200
        assert assess_resp.json()["assessment"]["outcome"] == "explained_well"
        assert assess_resp.json()["summary"]["explained_well"] == 1

        # 3. Blocked: General write endpoints MUST remain strictly forbidden (403)
        assert client.post(
            "/review-requests/any-request/mark-reviewed",
            headers=headers,
        ).status_code == 403

        assert client.post(
            "/passport/demo-sample-walkthrough-01/evidence-reviews",
            headers=headers,
            json={"skill_id": "python", "citation": "any", "status": "verified", "note": "ok"},
        ).status_code == 403

        assert client.post(
            "/passport/demo-sample-walkthrough-01/evidence-requests",
            headers=headers,
            json={"skill_id": "python", "note": "Please explain"},
        ).status_code == 403

        assert client.post(
            "/passport/demo-sample-walkthrough-01/recheck",
            headers=headers,
        ).status_code == 403


def test_demo_recruiter_cannot_modify_or_target_real_candidate(regression_env):
    _seed_real_candidate()
    with TestClient(main_module.app) as client:
        # Named recruiter logs in and creates a legitimate interview session on real candidate
        named_login = client.post(
            "/auth/recruiter/login",
            json={"username": "lead-recruiter", "key": NAMED_KEY},
        )
        named_headers = {"Authorization": f"Bearer {named_login.json()['token']}"}
        real_gen = client.post(
            "/passport/real-student-passport-01/interview-sessions",
            headers=named_headers,
        )
        # Even if Gemini fails on real passport, real_gen session or 503 is created
        real_session_id = real_gen.json().get("id") if real_gen.status_code == 201 else None

        # Demo recruiter logs in
        demo_login = client.post(
            "/auth/recruiter/login",
            json={"username": "recruiter@techcorp.com", "key": "recruiter2026"},
        )
        demo_headers = {"Authorization": f"Bearer {demo_login.json()['token']}"}

        # 1. Server-side authorization blocks demo recruiter from generating interview for real student
        resp = client.post(
            "/passport/real-student-passport-01/interview-sessions",
            headers=demo_headers,
        )
        assert resp.status_code == 403
        assert "read-only" in resp.json()["detail"].lower() or "demo" in resp.json()["detail"].lower()

        # 2. Server-side authorization blocks demo recruiter from assessing questions on real candidate
        if real_session_id:
            assess = client.put(
                f"/interview-sessions/{real_session_id}/questions/any-q/assessment",
                headers=demo_headers,
                json={"outcome": "explained_well", "note": "Illegal demo attack"},
            )
            # Must fail with 404 (not owner) or 403 (real passport protection)
            assert assess.status_code in (403, 404)

        # 3. Real student passport in storage remains completely unaltered
        stored_real = storage.get_passport("real-student-passport-01")
        assert stored_real["is_demo"] is False
        assert stored_real["github_username"] == "real-student-dev"


def test_demo_visitor_session_isolation(regression_env):
    with TestClient(main_module.app) as client:
        # Visitor A logs in
        login_a = client.post(
            "/auth/recruiter/login",
            json={"username": "recruiter@techcorp.com", "key": "recruiter2026"},
        )
        headers_a = {"Authorization": f"Bearer {login_a.json()['token']}"}

        # Visitor B logs in separately
        login_b = client.post(
            "/auth/recruiter/login",
            json={"username": "recruiter@techcorp.com", "key": "recruiter2026"},
        )
        headers_b = {"Authorization": f"Bearer {login_b.json()['token']}"}
        assert login_a.json()["token"] != login_b.json()["token"]

        # Visitor A creates an interview session
        session_a = client.post(
            "/passport/demo-sample-walkthrough-01/interview-sessions",
            headers=headers_a,
        ).json()
        assert session_a["id"]

        # Visitor B checks their interview sessions: must NOT see Visitor A's session
        list_b = client.get(
            "/passport/demo-sample-walkthrough-01/interview-sessions",
            headers=headers_b,
        ).json()
        assert list_b["items"] == []

        # Visitor B attempts to access or assess Visitor A's session: must receive 404
        get_a_by_b = client.get(f"/interview-sessions/{session_a['id']}", headers=headers_b)
        assert get_a_by_b.status_code == 404

        q_id = session_a["questions"][0]["id"]
        assess_a_by_b = client.put(
            f"/interview-sessions/{session_a['id']}/questions/{q_id}/assessment",
            headers=headers_b,
            json={"outcome": "explained_well", "note": "Hacked from visitor B"},
        )
        assert assess_a_by_b.status_code in (403, 404)


def test_demo_rate_limits(regression_env):
    with TestClient(main_module.app) as client:
        login = client.post(
            "/auth/recruiter/login",
            json={"username": "recruiter@techcorp.com", "key": "recruiter2026"},
        )
        headers = {"Authorization": f"Bearer {login.json()['token']}"}

        # Demo interview generation allows up to 5 requests per 10-minute window
        statuses = []
        for _ in range(6):
            unique_key = str(uuid.uuid4())
            res = client.post(
                "/passport/demo-sample-walkthrough-01/interview-sessions",
                headers={**headers, "Idempotency-Key": unique_key},
            )
            statuses.append(res.status_code)

        assert 429 in statuses
        assert statuses[-1] == 429


def test_missing_gemini_fallback_for_demo_vs_real_passport(regression_env, monkeypatch):
    _seed_real_candidate()
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    with TestClient(main_module.app) as client:
        named_login = client.post(
            "/auth/recruiter/login",
            json={"username": "lead-recruiter", "key": NAMED_KEY},
        )
        named_headers = {"Authorization": f"Bearer {named_login.json()['token']}"}

        # 1. On real passport: generation without GEMINI_API_KEY fails with actionable 503
        real_res = client.post(
            "/passport/real-student-passport-01/interview-sessions",
            headers=named_headers,
        )
        assert real_res.status_code == 503
        assert "GEMINI_API_KEY to be configured" in real_res.json()["detail"]

        # 2. On demo passport: generation without GEMINI_API_KEY gracefully falls back to pre-generated questions (201)
        demo_res = client.post(
            "/passport/demo-sample-walkthrough-01/interview-sessions",
            headers=named_headers,
        )
        assert demo_res.status_code == 201
        data = demo_res.json()
        assert len(data["questions"]) > 0
        assert any(q["source"] == "pre_generated" for q in data["questions"])


def test_demo_session_cleanup(regression_env):
    # Manually insert an expired demo session from 4 hours ago
    expired_id = str(uuid.uuid4())
    four_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()
    with storage._connect() as conn:
        conn.execute(
            """
            INSERT INTO interview_sessions (id, passport_id, recruiter_id, idempotency_key, status, created_at, updated_at, source_revision)
            VALUES (?, 'demo-sample-walkthrough-01', 'demo-recruiter:expired1234', 'key-exp', 'ready', ?, ?, 'rev')
            """,
            (expired_id, four_hours_ago, four_hours_ago),
        )
        conn.execute(
            """
            INSERT INTO interview_questions (id, session_id, position, skill_id, question_type, payload)
            VALUES (?, ?, 0, 'python', 'explain', '{}')
            """,
            (str(uuid.uuid4()), expired_id),
        )
        conn.commit()

    # Verify inserted
    assert storage.get_interview_session(expired_id) is not None

    # Run cleanup
    storage.cleanup_expired_demo_sessions(ttl_hours=2)

    # Verify expired session was pruned
    assert storage.get_interview_session(expired_id) is None


def test_named_recruiter_has_full_permissions(regression_env):
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
