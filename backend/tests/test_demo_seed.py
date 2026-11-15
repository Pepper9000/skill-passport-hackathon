import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.main as main_module
from app import config
from app.services import storage

EXPECTED_IDS = {
    "demo-sample-backend-01",
    "demo-sample-frontend-01",
    "demo-sample-ml-01",
}


@pytest.fixture
def isolated_demo_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATABASE_PATH", tmp_path / "demo-seed.sqlite")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(config, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(config, "APP_ENV", "development")
    monkeypatch.setattr(config, "GITHUB_TOKEN", "")
    monkeypatch.setattr(config, "OWNERSHIP_PROOF_SETTING_VALID", True)
    monkeypatch.setattr(config, "REQUIRE_OWNERSHIP_PROOF", True)
    monkeypatch.setattr(config, "RECRUITER_ACCOUNTS_SETTING_VALID", True)
    monkeypatch.setattr(main_module, "REQUIRE_RECRUITER_AUTH", False)
    monkeypatch.setattr(main_module, "RECRUITER_ACCOUNTS", {})
    monkeypatch.setattr(main_module, "RECRUITER_KEY", "")


def test_fresh_database_startup_seeds_three_unverified_fictional_passports(
    isolated_demo_environment,
):
    main_module.startup()

    passports = storage.list_passports()
    assert {passport["id"] for passport in passports} == EXPECTED_IDS
    for passport in passports:
        assert passport["is_demo"] is True
        assert passport["sources"]["repos"] == 0
        assert passport["sources"]["reports"] == 2
        assert "demo-learner-" in passport["github_username"]
        assert passport["skills"]
        assert all(skill["level"] == "Claimed" for skill in passport["skills"])
        assert all(not skill["evidence"] and not skill["certified"] for skill in passport["skills"])
        assert all(
            source["verification_status"] == "pending"
            for skill in passport["skills"]
            for source in skill["source_evidence"]
        )
        assert all(
            claim["status"] == "not_evidenced"
            and claim["quote"].startswith("DEMO DATA (fictional; unverified): ")
            and "evidence" not in claim
            for report in passport["reports"]
            for claim in report["claims"]
        )
        assert all(
            report["filename"].startswith("DEMO DATA - fictional ")
            for report in passport["reports"]
        )


def test_repeated_startup_is_idempotent(isolated_demo_environment):
    main_module.startup()
    main_module.startup()

    passports = storage.list_passports()
    assert {passport["id"] for passport in passports} == EXPECTED_IDS
    assert len(passports) == 3


def test_demo_recruiter_can_list_and_review_seeded_profiles(
    isolated_demo_environment, monkeypatch
):
    monkeypatch.setattr(main_module, "REQUIRE_RECRUITER_AUTH", True)
    monkeypatch.setattr(config, "DEMO_RECRUITER_USERNAME", "recruiter@techcorp.com")
    monkeypatch.setattr(config, "DEMO_RECRUITER_PASSWORD", "recruiter2026")

    with TestClient(main_module.app) as client:
        login = client.post(
            "/auth/recruiter/login",
            json={"username": "recruiter@techcorp.com", "key": "recruiter2026"},
        )
        assert login.status_code == 200
        assert login.json()["read_only"] is True
        headers = {"Authorization": f"Bearer {login.json()['token']}"}

        listing = client.get("/passports/review", headers=headers)
        assert listing.status_code == 200
        assert listing.json()["total"] == 3
        assert {item["id"] for item in listing.json()["items"]} == EXPECTED_IDS
        for passport_id in EXPECTED_IDS:
            response = client.get(f"/passport/{passport_id}/review", headers=headers)
            assert response.status_code == 200
            assert response.json()["is_demo"] is True
            assert all(skill["level"] == "Claimed" for skill in response.json()["skills"])
            assert all(not skill["evidence"] for skill in response.json()["skills"])
            assert client.post(
                f"/passport/{passport_id}/recheck", headers=headers
            ).status_code == 403
