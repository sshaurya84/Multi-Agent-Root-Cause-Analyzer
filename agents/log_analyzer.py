import os
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from schemas.findings import AnomalyEvent, LogFindings

load_dotenv()

CHUNK_SIZE = 50

LOG_ANALYZER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are an expert log analyst for distributed systems. "
        "Analyze the following raw server log lines and extract structured findings.\n\n"
        "For each anomaly you find, identify:\n"
        "- The timestamp from the log line\n"
        "- The service/component that generated it (e.g. dfs.DataNode, dfs.FSNamesystem)\n"
        "- The event type (e.g. IOException, OutOfMemoryError, DiskError, HeartbeatTimeout)\n"
        "- A concise description of what happened\n"
        "- Severity: 'low' for INFO-level oddities, 'medium' for warnings, "
        "'high' for errors, 'critical' for data-loss or node-death events\n\n"
        "Also provide:\n"
        "- A list of all affected services\n"
        "- A timeline summary describing the sequence of events\n"
        "- The earliest anomaly timestamp\n"
        "- The total number of log lines analyzed\n\n"
        "Focus on WARN and ERROR level entries. "
        "Ignore routine INFO messages unless they indicate an unusual condition."
    )),
    ("human", "Analyze these log lines:\n\n{log_lines}"),
])


def _get_llm():
    return ChatGroq(
        model="llama3-8b-8192",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY"),
    )


def _chunk_lines(raw_logs: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    lines = raw_logs.strip().splitlines()
    chunks = []
    for i in range(0, len(lines), chunk_size):
        chunk = "\n".join(lines[i:i + chunk_size])
        chunks.append(chunk)
    return chunks


def _merge_findings(findings_list: list[LogFindings]) -> LogFindings:
    all_anomalies: list[AnomalyEvent] = []
    all_services: set[str] = set()
    summaries: list[str] = []
    earliest = ""
    total_volume = 0

    for f in findings_list:
        all_anomalies.extend(f.anomalies)
        all_services.update(f.affected_services)
        summaries.append(f.timeline_summary)
        total_volume += f.log_volume_analyzed
        if f.earliest_anomaly_timestamp:
            if not earliest or f.earliest_anomaly_timestamp < earliest:
                earliest = f.earliest_anomaly_timestamp

    seen = set()
    deduped: list[AnomalyEvent] = []
    for a in all_anomalies:
        key = (a.timestamp, a.service, a.event_type)
        if key not in seen:
            seen.add(key)
            deduped.append(a)

    return LogFindings(
        anomalies=deduped,
        affected_services=sorted(all_services),
        timeline_summary=" | ".join(summaries),
        earliest_anomaly_timestamp=earliest,
        log_volume_analyzed=total_volume,
    )


def analyze(raw_logs: str) -> LogFindings:
    """Analyze raw log text and return structured LogFindings."""
    llm = _get_llm()
    structured_llm = llm.with_structured_output(LogFindings)
    chain = LOG_ANALYZER_PROMPT | structured_llm

    chunks = _chunk_lines(raw_logs)
    findings_list: list[LogFindings] = []

    for i, chunk in enumerate(chunks):
        line_count = len(chunk.splitlines())
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                result = chain.invoke({"log_lines": chunk})
                result.log_volume_analyzed = line_count
                findings_list.append(result)
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                wait = 2 ** retry_count
                time.sleep(wait)

    if len(findings_list) == 1:
        return findings_list[0]
    return _merge_findings(findings_list)
