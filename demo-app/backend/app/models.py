"""Pydantic schemas matching the frontend types."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    skill: Literal["docx", "internal-comms", "slack-gif-creator"]


class RunResponse(BaseModel):
    run_id: str


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
