"""Read-only data routes — list skills, fetch summary + SKILL.md per round."""

from __future__ import annotations

from fastapi import APIRouter

from app.services import data_loader

router = APIRouter()


@router.get("/api/skills")
def list_skills() -> list[dict]:
    return data_loader.list_skills()


@router.get("/api/skills/{skill}/summary")
def get_summary(skill: str) -> dict:
    return data_loader.get_summary(skill)


@router.get("/api/skills/{skill}/skill-md")
def get_skill_md(skill: str, round: int) -> dict:
    effective_round, content = data_loader.get_skill_md(skill, round)
    return {
        "requested_round": round,
        "round": effective_round,
        "content": content,
        "fallback": effective_round != round,
    }


@router.get("/api/skills/{skill}/available-rounds")
def get_available_rounds(skill: str) -> dict:
    return {"rounds": data_loader.available_rounds(skill)}
