from pydantic import BaseModel
from typing import Literal


class Hypothesis(BaseModel):
    rank: int
    root_cause: str
    confidence: Literal["low", "medium", "high"]
    evidence: list[str]
    suggested_actions: list[str]


class RootCauseReport(BaseModel):
    incident_summary: str
    hypotheses: list[Hypothesis]
    most_likely_cause: str
    immediate_actions: list[str]
    knowledge_base_patterns_matched: list[str]
