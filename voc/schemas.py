"""Agent contracts — the Pydantic models every LLM stage must return.

These models ARE the interface. The orchestrator never trusts raw model text;
it parses into one of these or the call counts as a failure (invariant I3).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

# Closed vocabulary for feature areas. Mirrors the planted themes in the
# synthetic data (01_themes/themes.json) plus an 'other' escape hatch.
FeatureArea = Literal[
    "billing",
    "food_tracking",
    "device_sync",
    "onboarding",
    "login_stability",
    "coaching",
    "personalization",
    "other",
]

ChurnFlag = Literal["cancel", "refund", "competitor", "uninstall"]


# --- Stage 2: pain-point extractor (local LLM) ------------------------------
class PainPoint(BaseModel):
    issue: str = Field(max_length=120, description="Short normalized problem statement.")
    feature_area: FeatureArea
    severity: int = Field(ge=1, le=5)
    quote: str = Field(description="Copied verbatim from the source; verified in stage 4.")


class ExtractionResult(BaseModel):
    """Zero pain points is valid — not every item carries a complaint."""
    pain_points: list[PainPoint] = Field(default_factory=list)


# --- Stage 3: theme namer (local LLM) ---------------------------------------
class ThemeName(BaseModel):
    label: str = Field(max_length=60)
    summary: str = Field(max_length=200, description="Redacted; safe to send to cloud (I4).")


# --- Stage 5: churn classifier (local LLM, residual pass) -------------------
class ChurnJudgment(BaseModel):
    flags: list[ChurnFlag] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


# --- Stage 6: roadmap recommender (cloud LLM, Groq) -------------------------
class Recommendation(BaseModel):
    title: str
    rationale: str
    theme_ids: list[str] = Field(description="Must reference real theme ids; validated post-hoc.")


class RoadmapResult(BaseModel):
    """List order IS the ranking."""
    recommendations: list[Recommendation] = Field(default_factory=list)


# --- Stage 7: critic / verifier (cloud LLM, Gemini) -------------------------
class Verdict(BaseModel):
    verdict: Literal["approve", "reject"]
    reason: Optional[Literal["vague", "uncited", "unsupported"]] = None

    @model_validator(mode="after")
    def _reason_matches_verdict(self) -> "Verdict":
        if self.verdict == "reject" and self.reason is None:
            raise ValueError("a 'reject' verdict must include a reason")
        if self.verdict == "approve" and self.reason is not None:
            raise ValueError("an 'approve' verdict must not include a reason")
        return self
