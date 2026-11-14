"""Structured readiness roadmap.

The passport already lists one growth task per gap skill ("Next up"). This builder turns the
role requirements into an ordered, multi-step plan: must-have gaps first, then nice-to-haves,
then level upgrades for skills that are met only weakly. Deterministic (no LLM call), built
from the stored passport, so it is cheap to compute at view time and stable to test.
"""

from typing import Any

_EFFORT_LABELS = {"S": "a focused session", "M": "a few days", "L": "a week or more"}
_NEXT_LEVEL = {"Claimed": "Used", "Used": "Applied", "Applied": "Demonstrated"}


def _gap_step(requirement: dict[str, Any], growth_task: dict[str, Any] | None, order: int) -> dict[str, Any]:
    name = requirement.get("name") or requirement.get("skill_id", "")
    min_level = requirement.get("min_level") or "Applied"
    actions = [
        f"Review {name} fundamentals with the official docs or a focused tutorial.",
    ]
    if growth_task:
        actions.append(f"Build it in {growth_task['target_repo']}: {growth_task['task']}")
        if growth_task.get("evidence_it_will_create"):
            actions.append(f"Make sure the work creates proof: {growth_task['evidence_it_will_create']}")
    else:
        actions.append(f"Add real, committed {name} work to one of your repositories.")
    actions.append("Push the commits and run Re-check on this passport so the new evidence is counted.")
    return {
        "order": order,
        "skill_id": requirement.get("skill_id"),
        "skill_name": name,
        "importance": requirement.get("importance"),
        "title": f"Close the {name} gap (needs {min_level})",
        "current": requirement.get("student_level") or "Not found",
        "target_level": min_level,
        "effort": "M" if requirement.get("importance") == "must" else "S",
        "actions": actions,
    }


def _upgrade_step(requirement: dict[str, Any], order: int) -> dict[str, Any] | None:
    level = requirement.get("student_level")
    target = _NEXT_LEVEL.get(level or "")
    if not target:
        return None
    name = requirement.get("name") or requirement.get("skill_id", "")
    return {
        "order": order,
        "skill_id": requirement.get("skill_id"),
        "skill_name": name,
        "importance": requirement.get("importance"),
        "title": f"Raise {name} from {level} to {target}",
        "current": level,
        "target_level": target,
        "effort": "S",
        "actions": [
            f"Extend the cited {name} code (or add tests that cover it) so the evidence shows your own work, not just usage.",
            "Push the commits and run Re-check on this passport.",
        ],
    }


def build_roadmap(passport: dict[str, Any]) -> dict[str, Any]:
    role_match = passport.get("role_match") or {}
    requirements = role_match.get("requirements") or []
    growth_by_skill = {
        task.get("skill_id"): task for task in (passport.get("growth_tasks") or []) if task.get("skill_id")
    }

    order = 0
    phases: list[dict[str, Any]] = []

    must_gaps = [r for r in requirements if r.get("importance") == "must" and r.get("status") != "met"]
    if must_gaps:
        steps = []
        for requirement in must_gaps:
            order += 1
            steps.append(_gap_step(requirement, growth_by_skill.get(requirement.get("skill_id")), order))
        phases.append({
            "phase": len(phases) + 1,
            "title": "Close must-have gaps",
            "why": "These block the role; recruiters see them first.",
            "steps": steps,
        })

    nice_gaps = [r for r in requirements if r.get("importance") != "must" and r.get("status") != "met"]
    if nice_gaps:
        steps = []
        for requirement in nice_gaps:
            order += 1
            steps.append(_gap_step(requirement, growth_by_skill.get(requirement.get("skill_id")), order))
        phases.append({
            "phase": len(phases) + 1,
            "title": "Close nice-to-have gaps",
            "why": "Not blockers, but they separate you from other candidates.",
            "steps": steps,
        })

    upgrades = []
    for requirement in requirements:
        if requirement.get("status") == "met" and requirement.get("student_level") in _NEXT_LEVEL:
            step = _upgrade_step(requirement, order + 1)
            if step:
                order += 1
                upgrades.append(step)
    if upgrades:
        phases.append({
            "phase": len(phases) + 1,
            "title": "Strengthen existing evidence",
            "why": "Usage-level evidence counts, but Applied and Demonstrated carry the interview.",
            "steps": upgrades,
        })

    total_steps = sum(len(phase["steps"]) for phase in phases)
    return {
        "role_name": role_match.get("role_name") or passport.get("target_role"),
        "phases": phases,
        "total_steps": total_steps,
        "effort_legend": _EFFORT_LABELS,
        "empty": total_steps == 0,
    }
