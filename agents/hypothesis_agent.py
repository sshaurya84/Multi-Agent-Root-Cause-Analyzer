import os
import time
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from schemas.findings import LogFindings
from schemas.report import RootCauseReport
from knowledge_base.loader import query_knowledge_base, init_knowledge_base

load_dotenv()

HYPOTHESIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are an expert site reliability engineer performing root cause analysis. "
        "You will receive structured log analysis findings and matching failure patterns "
        "from a knowledge base.\n\n"
        "Your task is to:\n"
        "1. Reason step by step through the timeline of anomalies\n"
        "2. Cross-reference the anomalies with the known failure patterns\n"
        "3. Produce ranked root cause hypotheses with confidence levels\n\n"
        "IMPORTANT RULES:\n"
        "- Reason through the timeline of anomalies BEFORE assigning confidence levels\n"
        "- Only cite evidence that actually appears in the LogFindings\n"
        "- Rank hypotheses from most likely to least likely\n"
        "- Assign confidence as 'high' only when multiple pieces of evidence converge\n"
        "- Suggest concrete, actionable remediation steps\n"
        "- Include which knowledge base patterns matched in your report"
    )),
    ("human", (
        "## Log Analysis Findings\n"
        "{findings_json}\n\n"
        "## Matching Knowledge Base Patterns\n"
        "{kb_patterns}\n\n"
        "Based on the findings and known patterns, produce a root cause analysis report "
        "with ranked hypotheses."
    )),
])


def _get_llm():
    return ChatGroq(
        model="llama3-8b-8192",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY"),
    )


def _build_kb_query(findings: LogFindings) -> str:
    """Build a search query from the most important parts of the findings."""
    parts = [findings.timeline_summary]
    for anomaly in findings.anomalies[:5]:
        parts.append(f"{anomaly.event_type}: {anomaly.description}")
    return " ".join(parts)


def hypothesize(findings: LogFindings) -> RootCauseReport:
    """Take LogFindings from Agent 1, query KB, and produce a RootCauseReport."""
    init_knowledge_base()

    query = _build_kb_query(findings)
    kb_results = query_knowledge_base(query, n_results=3)

    kb_patterns_text = ""
    for i, pattern in enumerate(kb_results, 1):
        kb_patterns_text += (
            f"### Pattern {i}: {pattern['metadata']['name']}\n"
            f"Root Cause: {pattern['metadata']['root_cause']}\n"
            f"Resolution: {pattern['metadata']['resolution']}\n"
            f"Symptoms: {pattern['metadata']['symptoms']}\n\n"
        )

    findings_json = findings.model_dump_json(indent=2)

    llm = _get_llm()
    structured_llm = llm.with_structured_output(RootCauseReport)
    chain = HYPOTHESIS_PROMPT | structured_llm

    max_retries = 3
    for attempt in range(max_retries):
        try:
            report = chain.invoke({
                "findings_json": findings_json,
                "kb_patterns": kb_patterns_text,
            })
            return report
        except Exception:
            if attempt >= max_retries - 1:
                raise
            time.sleep(2 ** (attempt + 1))
