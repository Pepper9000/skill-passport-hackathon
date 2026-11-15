import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import CACHE_DIR, DEEPSEEK_API_KEY, GEMINI_API_KEY, GEMINI_MODEL
from app.services.gemini import create_gemini_client, generate_json_result
from app.services.framework import get_skills
from app.services.json_cache import write_json_cache


class ProposedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_id: str
    repo: str
    file_path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    explanation: str = Field(min_length=1, max_length=500)


class ClaimProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[ProposedClaim]


class ClaimProposalError(RuntimeError):
    """The AI proposal was unavailable or unusable."""


class NoUsableFallbackEvidenceError(RuntimeError):
    """No extracted resume or certificate skill can support a fallback claim."""


def evidence_fallback(
    resume_skills: list[dict[str, str]],
    certificate_skills: list[dict[str, str]],
) -> dict[str, list[dict[str, Any]]]:
    """Keep document-derived skill mentions as pending claims, never as verified evidence."""
    allowed = {skill["id"]: skill for skill in get_skills()}
    aliases = {
        term.strip().casefold(): skill
        for skill in allowed.values()
        for term in (skill["id"], skill["name"], *skill.get("aliases", []))
    }
    sources: dict[str, list[dict[str, Any]]] = {}
    for source_name, mentions in (
        ("resume", resume_skills),
        ("certificate", certificate_skills),
    ):
        for item in mentions:
            skill = allowed.get(item.get("skill_id", "")) or aliases.get(
                item.get("skill_id", "").strip().casefold()
            )
            if not skill:
                continue
            source = {
                "source": source_name,
                "mention": item.get("mention") or skill["name"],
                "confidence": 0.35,
                "verification_status": "pending",
            }
            evidence = sources.setdefault(skill["id"], [])
            if source not in evidence:
                evidence.append(source)
    if not sources:
        raise NoUsableFallbackEvidenceError(
            "AI skill suggestions were unavailable, and no known skills were extracted from the resume or certificates."
        )
    return sources


def parse_proposal(text: str) -> ClaimProposal:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    proposal = ClaimProposal.model_validate_json(cleaned)
    allowed_ids = {skill["id"] for skill in get_skills()}
    for claim in proposal.claims:
        if claim.skill_id not in allowed_ids:
            raise ValueError(f"Unknown skill id in proposal: {claim.skill_id}")
    return proposal


def _lenient_proposal(text: str) -> ClaimProposal:
    """Invalid JSON or a missing claims array still fails, but a malformed claim, an unknown
    skill id or a 4th citation is dropped, not fatal.

    Dropped claims never reach the verifier, so nothing unverified can slip through.
    """
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    data = json.loads(cleaned)
    if not isinstance(data, dict) or not isinstance(data.get("claims"), list):
        raise ValueError('Expected a JSON object with a "claims" array.')
    allowed_ids = {skill["id"] for skill in get_skills()}
    counts: dict[str, int] = {}
    kept = []
    for raw in data["claims"]:
        try:
            claim = ProposedClaim.model_validate(raw)
        except ValidationError:
            continue  # e.g. line 0 or an over-long explanation: one bad claim can't fail the job
        if claim.skill_id not in allowed_ids:
            continue
        counts[claim.skill_id] = counts.get(claim.skill_id, 0) + 1
        if counts[claim.skill_id] <= 3:
            kept.append(claim)
    return ClaimProposal(claims=kept)


MAX_PROMPT_LINES = 8000


def _files_for_prompt(
    ingestion: dict[str, Any], max_lines: int | None = None
) -> list[tuple[str, str, dict[str, Any]]]:
    """Source files within the line budget, dropping the lowest-priority files first.

    Priority: each repo's first-selected file across all repos, then each repo's second, and so on
    (ingestion orders files by the user's recent changes; repos by most recent push).
    """
    ranked = sorted(
        (
            (file_index, repo_index, repo["name"], path, source)
            for repo_index, repo in enumerate(ingestion["repos"])
            for file_index, (path, source) in enumerate(repo["source_files"].items())
        ),
        key=lambda item: item[:2],
    )
    max_lines = MAX_PROMPT_LINES if max_lines is None else max_lines
    kept: set[tuple[int, int]] = set()
    total = 0
    for file_index, repo_index, _, _, source in ranked:
        size = len(source["lines"])
        if total + size > max_lines:
            break
        total += size
        kept.add((file_index, repo_index))
    # Keep each repo's files together in the prompt.
    return [
        (name, path, source)
        for file_index, repo_index, name, path, source in sorted(ranked, key=lambda item: (item[1], item[0]))
        if (file_index, repo_index) in kept
    ]


def _build_prompt(ingestion: dict[str, Any], resume_skills: list[dict[str, str]]) -> str:
    skills = [{"id": skill["id"], "name": skill["name"]} for skill in get_skills()]
    files = [
        {
            "repo": repo_name,
            "file_path": path,
            "lines": [
                {"line": number, "text": line}
                for number, line in enumerate(source["lines"], start=1)
            ],
        }
        for repo_name, path, source in _files_for_prompt(ingestion)
    ]
    resume_ids = sorted({item["skill_id"] for item in resume_skills})
    return (
        "Propose only skills directly supported by the supplied source-code lines. "
        "Return JSON with a claims array. Each claim must contain skill_id, repo, "
        "file_path, start_line, end_line, and explanation. Use only supplied skill ids "
        "and exact repository/file names and line numbers. Cite the most specific range, "
        "no more than three claims for any one skill, and never invent evidence. "
        "Resume skill ids are context only and are not proof. You do not decide verification.\n"
        f"Allowed skills: {json.dumps(skills)}\n"
        f"Resume-mentioned skill ids: {json.dumps(resume_ids)}\n"
        f"Source files: {json.dumps(files, ensure_ascii=False)}"
    )


def propose_claims(
    ingestion: dict[str, Any], resume_skills: list[dict[str, str]]
) -> list[dict[str, Any]]:
    if not GEMINI_API_KEY:
        raise ClaimProposalError("GEMINI_API_KEY is not configured.")
    prompt = _build_prompt(ingestion, resume_skills)
    cache_key = hashlib.sha256(
        f"{GEMINI_MODEL}\0{prompt}".encode("utf-8")
    ).hexdigest()
    cache_path = CACHE_DIR / f"claims-{cache_key}.json"
    if cache_path.exists():
        try:
            return ClaimProposal.model_validate_json(
                cache_path.read_text(encoding="utf-8")
            ).model_dump(mode="json")["claims"]
        except (UnicodeDecodeError, ValueError, ValidationError):
            cache_path.unlink(missing_ok=True)

    try:
        client = create_gemini_client(GEMINI_API_KEY)
    except Exception as exc:
        raise ClaimProposalError(
            f"AI skill proposal client could not be initialized ({exc.__class__.__name__})."
        ) from exc
    contents = prompt
    last_error: Exception | None = None
    for attempt in range(2):
        # A malformed Gemini answer is retried on the fallback provider when configured,
        # not re-asked of the model that just failed schema validation.
        prefer = "deepseek" if attempt and DEEPSEEK_API_KEY else "gemini"
        try:
            result = generate_json_result(client, contents, prefer=prefer)
        except Exception as exc:
            raise ClaimProposalError(
                f"AI skill proposal failed ({exc.__class__.__name__})."
            ) from exc
        response_text = result.text
        try:
            proposal = _lenient_proposal(response_text)
            payload = proposal.model_dump(mode="json")
            # Cache only primary-provider answers: a fallback answer is outage
            # survival, and the next run should get Gemini's own output.
            if result.provider == "gemini":
                write_json_cache(cache_path, payload)
            return payload["claims"]
        except (ValueError, ValidationError) as exc:
            last_error = exc
            if attempt == 0:
                contents = (
                    f"{prompt}\nYour previous output was invalid: {exc}. "
                    "Return corrected JSON only, preserving the schema and citation rules."
                )
    raise ClaimProposalError(
        f"The claim proposer returned unusable output after one retry ({last_error})."
    )
