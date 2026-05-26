from pydantic import BaseModel
from typing import Literal


class AnomalyEvent(BaseModel):
    timestamp: str
    service: str
    event_type: str
    description: str
    severity: Literal["low", "medium", "high", "critical"]


class LogFindings(BaseModel):
    anomalies: list[AnomalyEvent]
    affected_services: list[str]
    timeline_summary: str
    earliest_anomaly_timestamp: str
    log_volume_analyzed: int
