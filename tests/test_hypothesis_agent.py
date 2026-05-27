"""
Test for Agent 2: Hypothesis Agent.
Feeds a hand-crafted LogFindings through the agent and validates the RootCauseReport.
Requires GROQ_API_KEY to be set in .env.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.findings import AnomalyEvent, LogFindings
from agents.hypothesis_agent import hypothesize


def test_hypothesis_agent():
    findings = LogFindings(
        anomalies=[
            AnomalyEvent(
                timestamp="081109 203618",
                service="dfs.DataNode",
                event_type="IOException",
                description="Connection reset by peer on block receiver for blk_-1608999687919862906",
                severity="high",
            ),
            AnomalyEvent(
                timestamp="081109 203627",
                service="dfs.DataNode",
                event_type="IOException",
                description="Broken pipe during block transfer for blk_-6670958622368987959",
                severity="high",
            ),
            AnomalyEvent(
                timestamp="081109 203650",
                service="dfs.ReplicationMonitor",
                event_type="UnderReplication",
                description="Block blk_-1608999687919862906 is under-replicated: expected 3, actual 1",
                severity="critical",
            ),
            AnomalyEvent(
                timestamp="081109 203710",
                service="dfs.ReplicationMonitor",
                event_type="ZeroReplica",
                description="Block blk_2550793407016982932 has 0 replicas. Needs immediate attention.",
                severity="critical",
            ),
        ],
        affected_services=["dfs.DataNode", "dfs.FSNamesystem", "dfs.ReplicationMonitor"],
        timeline_summary=(
            "Multiple DataNode IO errors (connection reset, broken pipe) starting at 203618, "
            "followed by under-replicated blocks detected at 203650, "
            "culminating in a block with 0 replicas at 203710."
        ),
        earliest_anomaly_timestamp="081109 203618",
        log_volume_analyzed=30,
    )

    print("Generating hypotheses from hand-crafted LogFindings...")
    report = hypothesize(findings)

    print("\n=== RootCauseReport ===")
    print(json.dumps(report.model_dump(), indent=2))

    assert report.incident_summary, "Should have incident summary"
    assert len(report.hypotheses) >= 2, "Should have at least 2 hypotheses"
    assert report.most_likely_cause, "Should identify most likely cause"
    assert len(report.immediate_actions) > 0, "Should suggest actions"

    for h in report.hypotheses:
        assert h.confidence in ("low", "medium", "high")
        assert h.rank > 0

    ranks = [h.rank for h in report.hypotheses]
    assert ranks == sorted(ranks), "Hypotheses should be ranked in order"

    print("\nAll hypothesis agent assertions passed!")


if __name__ == "__main__":
    test_hypothesis_agent()
