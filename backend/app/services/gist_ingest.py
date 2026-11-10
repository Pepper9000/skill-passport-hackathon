"""Bounded ingestion of a candidate's own public GitHub Gist."""
import re
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import quote, unquote, urlsplit

import httpx

from app.config import GITHUB_TOKEN
from app.services.github_ingest import (
    API_ROOT,
    MAX_LINES,
    MAX_SOURCE_BYTES,
    MAX_SOURCE_FILES,
    SOURCE_EXTENSIONS,
    GitHubAuthenticationError,
    GitHubRateLimitError,
    validate_github_username,
)

GIST_URL_HOST = "gist.github.com"
GIST_ID_PATTERN = re.compile(r"[A-Fa-f0-9]{5,64}")
MAX_GIST_URL_LENGTH = 300


class GistIngestError(RuntimeError):
    """A submitted public Gist couldn't be safely analysed."""


class GistNotFoundError(GistIngestError):
    """The Gist is invalid, deleted, private, or otherwise not publicly accessible."""


def parse_gist_url(value: str, github_username: str) -> tuple[str, str]:
    """Return a validated Gist id and canonical URL bound to the submitted account."""
    raw = value.strip()
    if not raw or len(raw) > MAX_GIST_URL_LENGTH:
        raise ValueError("Enter one public GitHub Gist URL (up to 300 characters).")
    try:
        username = validate_github_username(github_username)
        parsed = urlsplit(raw)
    except ValueError as exc:
        raise ValueError("Enter a valid GitHub Gist URL.") from exc
    parts = [unquote(part) for part in parsed.path.strip("/").split("/")]
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != GIST_URL_HOST
        or parsed.query
        or len(parts) != 2
        or parts[0].lower() != username.lower()
        or not GIST_ID_PATTERN.fullmatch(parts[1])
    ):
        raise ValueError("Use a public Gist URL owned by the submitted GitHub account.")
    gist_id = parts[1].lower()
    return gist_id, f"https://{GIST_URL_HOST}/{quote(username, safe='')}/{gist_id}"


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Skill-Passport-Prototype",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _json_response(client: httpx.Client, url: str, *, missing_is_gist: bool = False) -> Any:
    try:
        response = client.get(url)
    except httpx.HTTPError as exc:
        raise GistIngestError("Could not reach GitHub to read the public Gist.") from exc
    if response.status_code == 404:
        if missing_is_gist:
            raise GistNotFoundError(
                "The Gist was not found or is not publicly accessible. Check the URL and visibility."
            )
        raise GistIngestError("GitHub could not provide the Gist's revision history.")
    if response.status_code == 401:
        raise GitHubAuthenticationError("GitHub rejected the configured API credentials.")
    if response.status_code in (403, 429):
        message = response.reason_phrase
        try:
            message = response.json().get("message", message)
        except (ValueError, AttributeError):
            pass
        remaining = response.headers.get("X-RateLimit-Remaining", "unknown")
        if response.status_code == 429 or remaining == "0" or "rate limit" in str(message).lower():
            raise GitHubRateLimitError("GitHub API rate limit exceeded while reading the public Gist.")
        raise GistIngestError("GitHub denied access to the Gist. Confirm that it is public.")
    if response.is_error:
        raise GistIngestError(f"GitHub could not read the public Gist (HTTP {response.status_code}).")
    try:
        return response.json()
    except ValueError as exc:
        raise GistIngestError("GitHub returned unreadable Gist data.") from exc


def _safe_gist_path(path: str) -> bool:
    parsed = PurePosixPath(path)
    return bool(path) and "\\" not in path and not parsed.is_absolute() and ".." not in parsed.parts


def ingest_public_gist(github_username: str, gist_url: str) -> dict[str, Any]:
    username = validate_github_username(github_username)
    gist_id, canonical_url = parse_gist_url(gist_url, username)
    timeout = httpx.Timeout(20.0, connect=10.0)
    with httpx.Client(headers=_headers(), timeout=timeout, follow_redirects=True) as client:
        detail = _json_response(
            client, f"{API_ROOT}/gists/{quote(gist_id, safe='')}", missing_is_gist=True
        )
        if not isinstance(detail, dict):
            raise GistIngestError("GitHub returned invalid Gist metadata.")
        owner = (detail.get("owner") or {}).get("login")
        if not isinstance(owner, str) or owner.lower() != username.lower():
            raise GistIngestError("The submitted Gist must belong to the GitHub account being analysed.")
        if not detail.get("public"):
            raise GistNotFoundError(
                "The Gist was not found or is not publicly accessible. Check the URL and visibility."
            )
        if detail.get("fork_of"):
            raise GistIngestError("Forked Gists are not accepted as candidate-authored evidence.")

        revisions = detail.get("history") or []
        version = revisions[0].get("version") if revisions and isinstance(revisions[0], dict) else None
        if not isinstance(version, str) or not version:
            raise GistIngestError("GitHub did not provide a current Gist revision to verify.")
        commits = _json_response(
            client, f"{API_ROOT}/gists/{quote(gist_id, safe='')}/commits?per_page=1"
        )
        latest = commits[0] if isinstance(commits, list) and commits else {}
        latest_user = ((latest.get("user") or {}).get("login") if isinstance(latest, dict) else None)
        authored = (
            isinstance(latest, dict)
            and latest.get("version") == version
            and isinstance(latest_user, str)
            and latest_user.lower() == username.lower()
        )

    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    files = detail.get("files")
    if not isinstance(files, dict):
        raise GistIngestError("GitHub returned no readable files for this Gist.")
    candidates = sorted(
        (
            name for name, metadata in files.items()
            if isinstance(name, str)
            and _safe_gist_path(name)
            and PurePosixPath(name).suffix.lower() in SOURCE_EXTENSIONS
        ),
        key=str.lower,
    )
    skipped: dict[str, int] = {}
    source_files: dict[str, dict[str, Any]] = {}
    for path in candidates[:MAX_SOURCE_FILES]:
        metadata = files[path]
        if not isinstance(metadata, dict):
            skipped["unreadable"] = skipped.get("unreadable", 0) + 1
            continue
        content = metadata.get("content")
        if not isinstance(content, str):
            skipped["unreadable"] = skipped.get("unreadable", 0) + 1
            continue
        if metadata.get("truncated") or len(content.encode("utf-8")) > MAX_SOURCE_BYTES:
            skipped["too_large"] = skipped.get("too_large", 0) + 1
            continue
        lines = content.splitlines()
        if len(lines) > MAX_LINES:
            skipped["too_many_lines"] = skipped.get("too_many_lines", 0) + 1
            lines = lines[:MAX_LINES]
        source_files[path] = {
            "content": "\n".join(lines),
            "lines": lines,
            "authored_shas": [version] if authored else [],
            "line_count": len(lines),
            "history": None,
            "blame": None,
            "commit_verification": None,
            "commit_verification_scope": "head",
            "first_commit_date": None,
            "retrieved_at": retrieved_at,
        }
    if len(candidates) > MAX_SOURCE_FILES:
        skipped["file_limit"] = skipped.get("file_limit", 0) + len(candidates) - MAX_SOURCE_FILES
    if not source_files:
        raise GistIngestError("The Gist contains no readable source-code files supported for analysis.")

    tree = list(files)
    test_files = [path for path in source_files if path.lower().split("/")[-1].startswith("test_")
                  or path.lower().split("/")[-1].endswith(("_test.py", "_spec.py"))
                  or ".test." in path.lower() or ".spec." in path.lower()]
    test_authored = {path: bool(authored and path in source_files) for path in test_files}
    return {
        "name": f"gist-{gist_id}",
        "full_name": f"{username}/{gist_id}",
        "owner": username,
        "html_url": canonical_url,
        "created_at": detail.get("created_at"),
        "pushed_at": detail.get("updated_at"),
        "head_sha": version,
        "is_fork": False,
        "is_gist": True,
        "tree": tree,
        "tree_truncated": False,
        "source_files": source_files,
        "source_file_count": len(candidates),
        "coverage": {
            "source_files_total": len(candidates),
            "source_files_read": len(source_files),
            "lines_read": sum(item["line_count"] for item in source_files.values()),
            "skipped": skipped,
            "tree_truncated": False,
        },
        "supporting_files_not_read": 0,
        "supporting_files_too_large": 0,
        "supporting_files_over_budget": 0,
        "supporting_files_failed_to_fetch": 0,
        "dependency_files": [],
        "dependency_contents": {},
        "config_files": [],
        "config_contents": {},
        "test_files": test_files,
        "test_contents": {
            path: source_files[path]["content"] for path in test_files
        },
        "test_authored": test_authored,
        "authored_paths": {},
        "user_commits": [],
        "user_commits_complete": False,
        "commit_counts": {"total": None, "by_user": 0},
    }
