"""Backend-owned fictional passports used by the read-only recruiter demo."""

from typing import Any

from app.services.framework import skill_map
from app.services.role_match import match_role
from app.services.storage import save_trusted_demo_passport
from app.services.verifier import snippet_sha256

_DEMO_DATA_NOTICE = "DEMO DATA (fictional; unverified): "
_CREATED_AT = "2026-10-25T12:00:00+00:00"

_SAMPLES = (
    {
        "id": "demo-sample-backend-01",
        "github_username": "demo-learner-backend",
        "target_role": "Backend Developer Intern",
        "skills": {
            "python": "Fictional resume claim: used Python in coursework and a study-planner project.",
            "fastapi": "Fictional resume claim: explored FastAPI for a small API project.",
            "sql": "Fictional resume claim: studied SQL queries in database coursework.",
            "git": "Fictional resume claim: used Git in class exercises.",
            "unit-testing": "Fictional resume claim: learned basic unit-testing concepts.",
        },
        "reports": [
            {
                "filename": "DEMO DATA - fictional Study Planner project brief",
                "claims": [
                    ("python", "Fictional project: a study-planner API concept using Python and FastAPI; no repository evidence is supplied."),
                    ("fastapi", "Fictional project: endpoint sketches for a study-planner API; no repository evidence is supplied."),
                ],
            },
            {
                "filename": "DEMO DATA - fictional education summary",
                "claims": [
                    ("sql", "Fictional education: introductory database coursework covering SQL; this is a sample claim, not a credential."),
                    ("unit-testing", "Fictional education: software testing exercises; this is a sample claim, not a verified result."),
                ],
            },
        ],
    },
    {
        "id": "demo-sample-frontend-01",
        "github_username": "demo-learner-frontend",
        "target_role": "Frontend Developer Intern",
        "skills": {
            "javascript": "Fictional resume claim: studied JavaScript for browser programming.",
            "typescript": "Fictional resume claim: tried TypeScript in coursework.",
            "react": "Fictional resume claim: explored React for a campus-events interface.",
            "git": "Fictional resume claim: used Git for class project version control.",
            "unit-testing": "Fictional resume claim: learned introductory UI testing concepts.",
            "rest-api": "Fictional resume claim: consumed REST APIs in a sample interface.",
        },
        "reports": [
            {
                "filename": "DEMO DATA - fictional Campus Events interface brief",
                "claims": [
                    ("react", "Fictional project: a campus-events interface concept using React and TypeScript; no repository evidence is supplied."),
                    ("javascript", "Fictional project: browser interactions for an events page; no repository evidence is supplied."),
                ],
            },
            {
                "filename": "DEMO DATA - fictional education summary",
                "claims": [
                    ("typescript", "Fictional education: web-programming coursework introducing TypeScript; this is a sample claim, not a credential."),
                    ("rest-api", "Fictional education: coursework included using a sample REST API; no implementation evidence is supplied."),
                ],
            },
        ],
    },
    {
        "id": "demo-sample-ml-01",
        "github_username": "demo-learner-ml",
        "target_role": "ML Engineer Intern",
        "skills": {
            "python": "Fictional resume claim: used Python in data-focused coursework.",
            "pandas": "Fictional resume claim: explored pandas for a sample data exercise.",
            "scikit-learn": "Fictional resume claim: studied basic scikit-learn workflows.",
            "sql": "Fictional resume claim: learned SQL fundamentals in coursework.",
            "git": "Fictional resume claim: used Git for class assignments.",
        },
        "reports": [
            {
                "filename": "DEMO DATA - fictional Course Outcomes project brief",
                "claims": [
                    ("pandas", "Fictional project: a course-outcomes data exploration concept using pandas; no repository evidence is supplied."),
                    ("scikit-learn", "Fictional project: a proposed introductory model experiment; no trained model or repository evidence is supplied."),
                ],
            },
            {
                "filename": "DEMO DATA - fictional education summary",
                "claims": [
                    ("python", "Fictional education: introductory programming and data-science coursework; this is a sample claim, not a credential."),
                    ("sql", "Fictional education: database fundamentals coursework; this is a sample claim, not a credential."),
                ],
            },
        ],
    },
)


def _build_sample(sample: dict[str, Any]) -> dict[str, Any]:
    catalogue = skill_map()
    skills = [
        {
            "skill_id": skill_id,
            "name": catalogue[skill_id]["name"],
            "level": "Claimed",
            "certified": False,
            "evidence": [],
            "source_evidence": [
                {
                    "source": "resume",
                    "mention": _DEMO_DATA_NOTICE + mention,
                    "confidence": 0.2,
                    "verification_status": "pending",
                }
            ],
        }
        for skill_id, mention in sample["skills"].items()
    ]
    reports = [
        {
            "filename": report["filename"],
            "claims": [
                {
                    "skill_id": skill_id,
                    "name": catalogue[skill_id]["name"],
                    "quote": _DEMO_DATA_NOTICE + quote,
                    "status": "not_evidenced",
                }
                for skill_id, quote in report["claims"]
            ],
            "dropped": [],
            "repo_links": [],
        }
        for report in sample["reports"]
    ]
    return {
        "id": sample["id"],
        "created_at": _CREATED_AT,
        "github_username": sample["github_username"],
        "target_role": sample["target_role"],
        "sources": {
            "repos": 0,
            "resume": True,
            "certificates": 0,
            "reports": len(reports),
        },
        "skills": skills,
        "rejected_claims": [],
        "role_match": match_role(skills, sample["target_role"]),
        "growth_tasks": [],
        "interview_kit": [],
        "reports": reports,
        "is_demo": True,
    }


def _build_walkthrough_sample() -> dict[str, Any]:
    catalogue = skill_map()

    py_snippet = "\n".join([
        "from datetime import datetime",
        "from pydantic import BaseModel, Field",
        "",
        "class StudyItem(BaseModel):",
        "    id: int",
        "    title: str = Field(min_length=1, max_length=120)",
        "    due_date: datetime",
        "    completed: bool = False",
        "",
        "    def mark_completed(self) -> None:",
        "        self.completed = True",
    ])

    api_snippet = "\n".join([
        "from fastapi import FastAPI, HTTPException",
        "from app.models import StudyItem",
        "",
        "app = FastAPI(title='Study Planner API')",
        "",
        "@app.get('/items/{item_id}', response_model=StudyItem)",
        "def get_study_item(item_id: int):",
        "    item = db.find_item(item_id)",
        "    if not item:",
        "        raise HTTPException(status_code=404, detail='Item not found')",
        "    return item",
    ])

    sql_snippet = "\n".join([
        "def query_pending_items(limit: int = 50):",
        "    query = 'SELECT id, title, due_date FROM study_items WHERE completed = 0 LIMIT ?'",
        "    return cursor.execute(query, (limit,)).fetchall()",
    ])

    skills = [
        {
            "skill_id": "python",
            "name": catalogue["python"]["name"],
            "level": "Demonstrated",
            "certified": False,
            "evidence": [
                {
                    "type": "code",
                    "repo": "demo-study-planner",
                    "file_path": "app/models.py",
                    "start_line": 1,
                    "end_line": 11,
                    "commit_sha": "demo7a1c",
                    "url": "https://github.com/demo-candidate-walkthrough/demo-study-planner/blob/demo7a1c/app/models.py#L1-L11",
                    "snippet": py_snippet,
                    "snippet_start_line": 1,
                    "snippet_end_line": 11,
                    "matched_line": 4,
                    "explanation": "DEMO DATA: Declares Pydantic data models with type hints and completion helper method.",
                    "checks": {
                        "file_exists": True,
                        "lines_valid": True,
                        "authored": True,
                        "not_fork": True,
                        "signature_found": True,
                    },
                    "demonstrated_by": {
                        "path": "tests/test_models.py",
                        "match": "name",
                    },
                    "integrity": [
                        {
                            "id": "line_share",
                            "label": "Cited lines written by the candidate",
                            "status": "ok",
                            "written": 11,
                            "cited": 11,
                            "detail": "All cited lines written in candidate commits.",
                        },
                        {
                            "id": "commit_spread",
                            "label": "Work spread over time",
                            "status": "ok",
                            "detail": "Commits spread across multiple development days.",
                        },
                    ],
                    "record": {
                        "commit_sha": "demo7a1c",
                        "path": "app/models.py",
                        "start_line": 1,
                        "end_line": 11,
                        "snippet_sha256": snippet_sha256(py_snippet),
                        "retrieved_at": _CREATED_AT,
                        "verifier_version": "2026-10-24",
                        "checks": ["file_exists", "lines_valid", "authored", "not_fork", "signature_found"],
                        "rules_applied": ["applied:code_citation", "demonstrated:test_name_match"],
                    },
                }
            ],
            "source_evidence": [
                {
                    "source": "resume",
                    "mention": "DEMO DATA: 2+ years coursework and project development with Python.",
                    "confidence": 0.9,
                    "verification_status": "verified",
                }
            ],
        },
        {
            "skill_id": "rest-api",
            "name": catalogue["rest-api"]["name"],
            "level": "Applied",
            "certified": False,
            "evidence": [
                {
                    "type": "code",
                    "repo": "demo-study-planner",
                    "file_path": "app/main.py",
                    "start_line": 1,
                    "end_line": 11,
                    "commit_sha": "demo7a1c",
                    "url": "https://github.com/demo-candidate-walkthrough/demo-study-planner/blob/demo7a1c/app/main.py#L1-L11",
                    "snippet": api_snippet,
                    "snippet_start_line": 1,
                    "snippet_end_line": 11,
                    "matched_line": 6,
                    "explanation": "DEMO DATA: Implements FastAPI REST endpoint with typed route parameters and HTTP error response.",
                    "checks": {
                        "file_exists": True,
                        "lines_valid": True,
                        "authored": True,
                        "not_fork": True,
                        "signature_found": True,
                    },
                    "integrity": [
                        {
                            "id": "line_share",
                            "label": "Cited lines written by the candidate",
                            "status": "ok",
                            "written": 11,
                            "cited": 11,
                            "detail": "All cited lines written in candidate commits.",
                        },
                    ],
                    "record": {
                        "commit_sha": "demo7a1c",
                        "path": "app/main.py",
                        "start_line": 1,
                        "end_line": 11,
                        "snippet_sha256": snippet_sha256(api_snippet),
                        "retrieved_at": _CREATED_AT,
                        "verifier_version": "2026-10-24",
                        "checks": ["file_exists", "lines_valid", "authored", "not_fork", "signature_found"],
                        "rules_applied": ["applied:code_citation"],
                    },
                }
            ],
            "source_evidence": [
                {
                    "source": "resume",
                    "mention": "DEMO DATA: Built REST API backend using FastAPI.",
                    "confidence": 0.85,
                    "verification_status": "verified",
                }
            ],
        },
        {
            "skill_id": "sql",
            "name": catalogue["sql"]["name"],
            "level": "Applied",
            "certified": False,
            "evidence": [
                {
                    "type": "code",
                    "repo": "demo-study-planner",
                    "file_path": "app/db.py",
                    "start_line": 1,
                    "end_line": 3,
                    "commit_sha": "demo7a1c",
                    "url": "https://github.com/demo-candidate-walkthrough/demo-study-planner/blob/demo7a1c/app/db.py#L1-L3",
                    "snippet": sql_snippet,
                    "snippet_start_line": 1,
                    "snippet_end_line": 3,
                    "matched_line": 2,
                    "explanation": "DEMO DATA: Parameterized SQL query execution with LIMIT and filtering.",
                    "checks": {
                        "file_exists": True,
                        "lines_valid": True,
                        "authored": True,
                        "not_fork": True,
                        "signature_found": True,
                    },
                    "integrity": [
                        {
                            "id": "line_share",
                            "label": "Cited lines written by the candidate",
                            "status": "ok",
                            "written": 3,
                            "cited": 3,
                            "detail": "All cited lines written in candidate commits.",
                        },
                    ],
                    "record": {
                        "commit_sha": "demo7a1c",
                        "path": "app/db.py",
                        "start_line": 1,
                        "end_line": 3,
                        "snippet_sha256": snippet_sha256(sql_snippet),
                        "retrieved_at": _CREATED_AT,
                        "verifier_version": "2026-10-24",
                        "checks": ["file_exists", "lines_valid", "authored", "not_fork", "signature_found"],
                        "rules_applied": ["applied:code_citation"],
                    },
                }
            ],
            "source_evidence": [
                {
                    "source": "resume",
                    "mention": "DEMO DATA: SQL query optimization and database design coursework.",
                    "confidence": 0.7,
                    "verification_status": "verified",
                }
            ],
        },
        {
            "skill_id": "git",
            "name": catalogue["git"]["name"],
            "level": "Used",
            "certified": False,
            "evidence": [
                {
                    "type": "commit",
                    "repo": "demo-study-planner",
                    "file_path": ".git",
                    "commit_sha": "demo7a1c",
                    "start_line": 0,
                    "end_line": 0,
                    "url": "https://github.com/demo-candidate-walkthrough/demo-study-planner/commits",
                    "explanation": "DEMO DATA: Authored 14 commits in demo repository history.",
                    "checks": {
                        "file_exists": True,
                        "lines_valid": True,
                        "authored": True,
                        "not_fork": True,
                        "signature_found": True,
                    },
                    "integrity": [
                        {
                            "id": "commit_spread",
                            "label": "Work spread over time",
                            "status": "ok",
                            "detail": "Commits spread over several development days.",
                        }
                    ],
                }
            ],
        },
        {
            "skill_id": "unit-testing",
            "name": catalogue["unit-testing"]["name"],
            "level": "Claimed",
            "certified": False,
            "evidence": [],
            "source_evidence": [
                {
                    "source": "resume",
                    "mention": "DEMO DATA (fictional; unverified): practiced writing basic unit tests in coursework.",
                    "confidence": 0.2,
                    "verification_status": "pending",
                }
            ],
        },
        {
            "skill_id": "docker",
            "name": catalogue["docker"]["name"],
            "level": "Claimed",
            "certified": False,
            "evidence": [],
            "source_evidence": [
                {
                    "source": "resume",
                    "mention": "DEMO DATA (fictional; unverified): introductory knowledge of Docker containerization.",
                    "confidence": 0.2,
                    "verification_status": "pending",
                }
            ],
        },
        {
            "skill_id": "postgresql",
            "name": catalogue["postgresql"]["name"],
            "level": "Claimed",
            "certified": False,
            "evidence": [],
            "source_evidence": [
                {
                    "source": "resume",
                    "mention": "DEMO DATA (fictional; unverified): studied relational databases including PostgreSQL.",
                    "confidence": 0.2,
                    "verification_status": "pending",
                }
            ],
        },
        {
            "skill_id": "cicd",
            "name": catalogue["cicd"]["name"],
            "level": "Claimed",
            "certified": False,
            "evidence": [],
            "source_evidence": [
                {
                    "source": "resume",
                    "mention": "DEMO DATA (fictional; unverified): familiar with CI/CD deployment automation.",
                    "confidence": 0.2,
                    "verification_status": "pending",
                }
            ],
        },
    ]

    coverage = {
        "repos_found": 2,
        "repos_analysed": 2,
        "source_files_total": 6,
        "source_files_read": 6,
        "lines_sent_to_ai": 320,
        "repos": [
            {
                "name": "demo-study-planner",
                "files_found": 4,
                "files_read": 4,
                "skipped": [],
            },
            {
                "name": "demo-auth-service",
                "files_found": 2,
                "files_read": 2,
                "skipped": [],
            },
        ],
        "notes": [],
    }

    growth_tasks = [
        {
            "skill_id": "unit-testing",
            "target_repo": "demo-study-planner",
            "task": "DEMO DATA: Write pytest test suite in tests/test_main.py covering FastAPI endpoint responses and error conditions in app/main.py.",
            "evidence_it_will_create": "DEMO DATA: Tests committing to tests/test_main.py targeting app/main.py will raise Unit Testing to Applied and rest-api to Demonstrated.",
        },
        {
            "skill_id": "docker",
            "target_repo": "demo-study-planner",
            "task": "DEMO DATA: Add a multi-stage Dockerfile packaging the Study Planner service with non-root security context.",
            "evidence_it_will_create": "DEMO DATA: A Dockerfile committed to the repository root provides config evidence that upgrades Docker to Used.",
        },
        {
            "skill_id": "cicd",
            "target_repo": "demo-study-planner",
            "task": "DEMO DATA: Create a GitHub Actions workflow in .github/workflows/ci.yml running linting and tests on pull requests.",
            "evidence_it_will_create": "DEMO DATA: Workflow files committed to .github/workflows elevate CI/CD to Used.",
        },
        {
            "skill_id": "postgresql",
            "target_repo": "demo-study-planner",
            "task": "DEMO DATA: Configure an async PostgreSQL connection pool in app/db.py replacing SQLite for production persistence.",
            "evidence_it_will_create": "DEMO DATA: Direct asyncpg/psycopg connection configuration elevates PostgreSQL to Used.",
        },
    ]

    interview_kit = [
        {
            "skill_id": "python",
            "questions": [
                {
                    "q": "DEMO DATA: In demo-study-planner app/models.py lines 1–11, why did you use Pydantic BaseModel with Field constraints instead of standard Python dataclasses?",
                    "good_answer_mentions": "Mentions runtime validation, automatic deserialization, type coercion, and error schema integration.",
                },
                {
                    "q": "DEMO DATA: In demo-study-planner app/models.py, how does the model handle missing or null due_date values during instantiation?",
                    "good_answer_mentions": "Explains default field behavior, datetime parsing rules, and ValidationError handling.",
                },
            ],
        },
        {
            "skill_id": "rest-api",
            "questions": [
                {
                    "q": "DEMO DATA: In demo-study-planner app/main.py lines 1–11, how is HTTP 404 signaled when an item_id does not exist?",
                    "good_answer_mentions": "Cites HTTPException(status_code=404), REST resource semantics, and consistent error message payloads.",
                },
                {
                    "q": "DEMO DATA: What idempotency considerations apply if get_study_item was converted to a PUT or PATCH endpoint?",
                    "good_answer_mentions": "Discusses HTTP verb semantics, partial updates, and concurrency safeguards.",
                },
            ],
        },
    ]

    reports = [
        {
            "filename": "DEMO DATA - Study Planner Architecture Overview",
            "claims": [
                {
                    "skill_id": "python",
                    "name": "Python",
                    "quote": "DEMO DATA: Core domain models implemented in Python with Pydantic.",
                    "status": "corroborated",
                },
                {
                    "skill_id": "rest-api",
                    "name": "REST APIs",
                    "quote": "DEMO DATA: Study Planner exposes standard HTTP JSON endpoints.",
                    "status": "corroborated",
                },
            ],
            "dropped": [],
            "repo_links": [{"repo": "demo-study-planner", "status": "own"}],
        }
    ]

    identity = [
        {
            "id": "account_ownership",
            "label": "Applicant controls this GitHub account",
            "status": "unknown",
            "detail": "Demo passport (DEMO DATA); account ownership is not checked.",
        },
        {
            "id": "resume_github_link",
            "label": "Resume links to this GitHub account",
            "status": "ok",
            "detail": "The resume links to github.com/demo-candidate-walkthrough.",
        },
    ]

    return {
        "id": "demo-sample-walkthrough-01",
        "created_at": _CREATED_AT,
        "updated_at": _CREATED_AT,
        "github_username": "demo-candidate-walkthrough",
        "target_role": "Backend Developer Intern",
        "sources": {
            "repos": 2,
            "gists": 0,
            "resume": True,
            "certificates": 0,
            "reports": len(reports),
        },
        "coverage": coverage,
        "skills": skills,
        "rejected_claims": [],
        "role_match": match_role(skills, "Backend Developer Intern", coverage=coverage),
        "growth_tasks": growth_tasks,
        "interview_kit": interview_kit,
        "reports": reports,
        "identity": identity,
        "is_demo": True,
    }


def seed_demo_passports() -> None:
    """Idempotently register the fixed fictional samples in the trusted demo registry."""
    for sample in _SAMPLES:
        save_trusted_demo_passport(_build_sample(sample))
    save_trusted_demo_passport(_build_walkthrough_sample())
