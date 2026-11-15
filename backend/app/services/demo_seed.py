"""Backend-owned fictional passports used by the read-only recruiter demo."""

from typing import Any

from app.services.framework import skill_map
from app.services.role_match import match_role
from app.services.storage import save_trusted_demo_passport

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


def seed_demo_passports() -> None:
    """Idempotently register the fixed fictional samples in the trusted demo registry."""
    for sample in _SAMPLES:
        save_trusted_demo_passport(_build_sample(sample))
