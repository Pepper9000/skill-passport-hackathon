import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import gist_ingest


class FakeResponse:
    def __init__(self, data: Any, status_code: int = 200) -> None:
        self._data = data
        self.status_code = status_code
        self.reason_phrase = "Not Found"
        self.headers: dict[str, str] = {}
        self.is_error = status_code >= 400

    def json(self) -> Any:
        return self._data


class FakeClient:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def get(self, url: str) -> FakeResponse:
        self.calls.append(url)
        return self.responses[url]


def _gist_metadata(username: str = "student", *, public: bool = True, fork: bool = False) -> dict:
    return {
        "owner": {"login": username},
        "public": public,
        "fork_of": {"id": "original"} if fork else None,
        "history": [{"version": "rev123"}],
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-02T00:00:00Z",
        "files": {"app.py": {"content": "from flask import Flask\napp = Flask(__name__)\n"}},
    }


def _mock_api(monkeypatch, metadata: dict | FakeResponse, commits: list[dict] | None = None) -> FakeClient:
    gist_url = f"{gist_ingest.API_ROOT}/gists/abc1234"
    commits_url = f"{gist_url}/commits?per_page=1"
    responses = {
        gist_url: metadata if isinstance(metadata, FakeResponse) else FakeResponse(metadata),
        commits_url: FakeResponse(commits or [{"version": "rev123", "user": {"login": "student"}}]),
    }
    client = FakeClient(responses)
    monkeypatch.setattr(gist_ingest.httpx, "Client", lambda **_kwargs: client)
    monkeypatch.setattr(gist_ingest, "GITHUB_TOKEN", "")
    return client


def test_parse_gist_url_requires_https_exact_host_and_submitted_owner() -> None:
    assert gist_ingest.parse_gist_url("https://gist.github.com/Student/ABC1234", "student") == (
        "abc1234",
        "https://gist.github.com/student/abc1234",
    )
    for url in (
        "http://gist.github.com/student/abc1234",
        "https://gist.github.com.evil.example/student/abc1234",
        "https://gist.github.com/other/abc1234",
        "https://gist.github.com/student/abc1234?file=app.py",
        "https://gist.github.com/student/not-a-gist-id",
    ):
        with pytest.raises(ValueError):
            gist_ingest.parse_gist_url(url, "student")


def test_ingest_public_gist_returns_bounded_authored_source(monkeypatch) -> None:
    client = _mock_api(monkeypatch, _gist_metadata())

    repo = gist_ingest.ingest_public_gist("student", "https://gist.github.com/student/abc1234")

    assert repo["is_gist"] is True
    assert repo["name"] == "gist-abc1234"
    assert repo["source_files"]["app.py"]["authored_shas"] == ["rev123"]
    assert repo["test_authored"] == {}
    assert repo["coverage"]["source_files_read"] == 1
    assert client.calls[-1].endswith("/commits?per_page=1")


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        (_gist_metadata("someone-else"), "belong to the GitHub account"),
        (_gist_metadata(public=False), "not publicly accessible"),
        (_gist_metadata(fork=True), "Forked Gists"),
    ],
)
def test_ingest_rejects_wrong_owner_private_and_forked_gists(monkeypatch, metadata, expected) -> None:
    _mock_api(monkeypatch, metadata)

    with pytest.raises(gist_ingest.GistIngestError, match=expected):
        gist_ingest.ingest_public_gist("student", "https://gist.github.com/student/abc1234")


def test_ingest_rejects_deleted_or_inaccessible_gist(monkeypatch) -> None:
    _mock_api(monkeypatch, FakeResponse({"message": "Not Found"}, status_code=404))

    with pytest.raises(gist_ingest.GistNotFoundError, match="not found"):
        gist_ingest.ingest_public_gist("student", "https://gist.github.com/student/abc1234")


def test_gist_lines_get_revision_pinned_permalink(monkeypatch) -> None:
    from app.services.verifier import _make_url

    _mock_api(monkeypatch, _gist_metadata())
    repo = gist_ingest.ingest_public_gist("student", "https://gist.github.com/student/abc1234")

    assert _make_url(repo, "rev123", "app.py", 1, 2) == (
        "https://gist.github.com/student/abc1234/rev123#file-app-py-L1-L2"
    )
