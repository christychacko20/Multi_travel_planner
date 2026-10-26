from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class TravelRequest(BaseModel):
    origin: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=2, max_length=100)
    days: int = Field(gt=0, le=30)
    travelers: int = Field(default=1, gt=0, le=20)
    budget: Decimal = Field(gt=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    start_date: date | None = None
    end_date: date | None = None
    preferences: list[str] = Field(default_factory=list)


class RunRequest(BaseModel):
    task: str = Field(default="Plan my trip", min_length=1, max_length=2_000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    travel: TravelRequest | None = None


class ResumeRequest(BaseModel):
    approved: bool


class RunResponse(BaseModel):
    run_id: str
    status: str
    response: str | None = None
    error: str | None = None
    audit: list[str] = Field(default_factory=list)
