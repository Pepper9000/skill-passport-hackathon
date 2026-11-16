import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services import storage


def test_clean_install_has_no_passports(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATABASE_PATH", tmp_path / "empty.sqlite")
    storage.purge_legacy_seeded_passports()
    assert storage.list_passports() == []


def test_upgrade_removes_only_registered_fixtures_and_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATABASE_PATH", tmp_path / "upgrade.sqlite")
    base = {"created_at": "2026-01-01T00:00:00Z", "github_username": "real-account", "target_role": "backend", "skills": []}
    storage.save_passport({**base, "id": "ordinary", "is_demo": True})
    storage.save_passport({**base, "id": "legacy-seed"})
    with storage._connect() as connection:
        connection.execute("INSERT INTO trusted_demo_passports VALUES (?)", ("legacy-seed",))
    storage.purge_legacy_seeded_passports()
    storage.purge_legacy_seeded_passports()
    assert [item["id"] for item in storage.list_passports()] == ["ordinary"]
    assert storage.get_passport("ordinary")["is_demo"] is False
