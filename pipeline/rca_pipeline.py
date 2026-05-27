import logging

from schemas.findings import LogFindings
from schemas.report import RootCauseReport
from agents.log_analyzer import analyze
from agents.hypothesis_agent import hypothesize

logger = logging.getLogger(__name__)


def run_pipeline(log_file_path: str) -> RootCauseReport:
    """Run the full two-agent RCA pipeline: log analysis -> hypothesis generation."""
    logger.info("Reading log file: %s", log_file_path)
    with open(log_file_path, "r") as f:
        raw_logs = f.read()

    line_count = len(raw_logs.strip().splitlines())
    logger.info("Analyzing %d log lines...", line_count)

    findings: LogFindings = analyze(raw_logs)
    logger.info(
        "Found %d anomalies across %d services",
        len(findings.anomalies),
        len(findings.affected_services),
    )

    logger.info("Querying knowledge base and generating hypotheses...")
    report: RootCauseReport = hypothesize(findings)
    logger.info(
        "Generated %d hypotheses. Most likely cause: %s",
        len(report.hypotheses),
        report.most_likely_cause,
    )

    return report
