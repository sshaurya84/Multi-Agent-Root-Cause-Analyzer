"""
Test for Agent 1: Log Analyzer.
Feeds a real HDFS log sample through the agent and validates the output.
Requires GROQ_API_KEY to be set in .env.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.log_analyzer import analyze


def test_log_analyzer():
    sample_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "sample_logs", "hdfs_sample_1.log",
    )
    with open(sample_path, "r") as f:
        raw_logs = f.read()

    print(f"Analyzing {len(raw_logs.splitlines())} log lines...")
    findings = analyze(raw_logs)

    print("\n=== LogFindings Result ===")
    print(json.dumps(findings.model_dump(), indent=2))

    assert len(findings.anomalies) > 0, "Should find at least one anomaly"
    assert len(findings.affected_services) > 0, "Should identify affected services"
    assert findings.timeline_summary, "Should have a timeline summary"
    assert findings.earliest_anomaly_timestamp, "Should have earliest timestamp"
    assert findings.log_volume_analyzed > 0, "Should report volume analyzed"

    for anomaly in findings.anomalies:
        assert anomaly.severity in ("low", "medium", "high", "critical")
        assert anomaly.timestamp
        assert anomaly.service
        assert anomaly.event_type

    print("\nAll assertions passed!")


if __name__ == "__main__":
    test_log_analyzer()
