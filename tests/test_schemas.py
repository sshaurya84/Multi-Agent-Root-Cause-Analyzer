import pytest
from pydantic import ValidationError

from schemas.findings import AnomalyEvent, LogFindings
from schemas.report import Hypothesis, RootCauseReport


def test_anomaly_event_valid():
    event = AnomalyEvent(
        timestamp="081109 203618",
        service="dfs.DataNode",
        event_type="IOException",
        description="Connection reset by peer on block receiver",
        severity="high",
    )
    assert event.timestamp == "081109 203618"
    assert event.severity == "high"


def test_anomaly_event_invalid_severity():
    with pytest.raises(ValidationError):
        AnomalyEvent(
            timestamp="081109 203618",
            service="dfs.DataNode",
            event_type="IOException",
            description="Connection reset by peer",
            severity="extreme",
        )


def test_log_findings_valid():
    findings = LogFindings(
        anomalies=[
            AnomalyEvent(
                timestamp="081109 203618",
                service="dfs.DataNode",
                event_type="IOException",
                description="Connection reset by peer",
                severity="high",
            ),
            AnomalyEvent(
                timestamp="081109 203627",
                service="dfs.DataNode",
                event_type="IOException",
                description="Broken pipe during block transfer",
                severity="medium",
            ),
        ],
        affected_services=["dfs.DataNode", "dfs.FSNamesystem"],
        timeline_summary="Multiple DataNode IO errors followed by under-replication warnings",
        earliest_anomaly_timestamp="081109 203618",
        log_volume_analyzed=30,
    )
    assert len(findings.anomalies) == 2
    assert "dfs.DataNode" in findings.affected_services
    assert findings.log_volume_analyzed == 30


def test_log_findings_missing_field():
    with pytest.raises(ValidationError):
        LogFindings(
            anomalies=[],
            affected_services=["dfs.DataNode"],
            timeline_summary="Summary",
            # missing earliest_anomaly_timestamp and log_volume_analyzed
        )


def test_hypothesis_valid():
    h = Hypothesis(
        rank=1,
        root_cause="Network partition causing DataNode isolation",
        confidence="high",
        evidence=["Connection reset errors on multiple nodes", "Heartbeat timeouts"],
        suggested_actions=["Check network switches", "Review firewall rules"],
    )
    assert h.rank == 1
    assert h.confidence == "high"


def test_hypothesis_invalid_confidence():
    with pytest.raises(ValidationError):
        Hypothesis(
            rank=1,
            root_cause="Unknown",
            confidence="very_high",
            evidence=[],
            suggested_actions=[],
        )


def test_root_cause_report_valid():
    report = RootCauseReport(
        incident_summary="DataNode failures due to network partition",
        hypotheses=[
            Hypothesis(
                rank=1,
                root_cause="Network partition in rack1",
                confidence="high",
                evidence=["Connection refused errors", "Heartbeat timeouts"],
                suggested_actions=["Restore network connectivity"],
            ),
            Hypothesis(
                rank=2,
                root_cause="Switch failure",
                confidence="medium",
                evidence=["Multiple nodes in same rack affected"],
                suggested_actions=["Replace faulty switch"],
            ),
        ],
        most_likely_cause="Network partition in rack1",
        immediate_actions=["Restore network", "Trigger block re-replication"],
        knowledge_base_patterns_matched=["network_partition", "cascading_failure"],
    )
    assert len(report.hypotheses) == 2
    assert report.most_likely_cause == "Network partition in rack1"
    assert "network_partition" in report.knowledge_base_patterns_matched


def test_root_cause_report_missing_field():
    with pytest.raises(ValidationError):
        RootCauseReport(
            incident_summary="Some incident",
            hypotheses=[],
            # missing most_likely_cause, immediate_actions, knowledge_base_patterns_matched
        )


if __name__ == "__main__":
    test_anomaly_event_valid()
    test_anomaly_event_invalid_severity()
    test_log_findings_valid()
    test_log_findings_missing_field()
    test_hypothesis_valid()
    test_hypothesis_invalid_confidence()
    test_root_cause_report_valid()
    test_root_cause_report_missing_field()
    print("All schema tests passed!")
