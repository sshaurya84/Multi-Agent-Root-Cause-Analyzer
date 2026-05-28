"""
Benchmark: Two-agent pipeline vs single-agent baseline.

Runs both approaches on 20 labeled HDFS log samples and scores them
using a 3-point rubric per sample:
  1. Does most_likely_cause mention the correct root cause category?
  2. Are the correct affected services identified?
  3. Does at least one hypothesis have the right root cause with high confidence?
"""
import json
import os
import sys
import time
import logging

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from schemas.report import RootCauseReport
from pipeline.rca_pipeline import run_pipeline

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LABELS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "labels.json")
_LOGS_DIR = os.path.join(_BASE_DIR, "data", "sample_logs")

SINGLE_AGENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are an expert log analyst and site reliability engineer. "
        "Analyze the following raw server logs and produce a root cause analysis report. "
        "Identify the most likely root cause, list hypotheses ranked by likelihood, "
        "and suggest immediate actions. Be thorough and specific."
    )),
    ("human", "Analyze these logs and produce a root cause report:\n\n{raw_logs}"),
])


def _get_llm():
    return ChatGroq(
        model="llama3-8b-8192",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY"),
    )


def run_single_agent(log_file_path: str) -> RootCauseReport:
    """Single-agent baseline: raw logs directly to RootCauseReport in one shot."""
    with open(log_file_path, "r") as f:
        raw_logs = f.read()

    llm = _get_llm()
    structured_llm = llm.with_structured_output(RootCauseReport)
    chain = SINGLE_AGENT_PROMPT | structured_llm

    return chain.invoke({"raw_logs": raw_logs})


def score_report(report: RootCauseReport, label: dict) -> dict:
    """Score a report against the ground truth label. Returns dict with 3 scores."""
    scores = {"cause_correct": 0, "services_correct": 0, "high_confidence_correct": 0}

    cause_keywords = label["root_cause_category"].lower().split()
    most_likely = report.most_likely_cause.lower()
    if any(kw in most_likely for kw in cause_keywords):
        scores["cause_correct"] = 1

    expected_services = set(s.lower() for s in label["affected_services"])
    found_services = set()
    for h in report.hypotheses:
        found_services.update(w.lower() for w in h.evidence)
    found_services_text = " ".join(found_services).lower()

    all_report_text = (
        report.incident_summary.lower() + " " +
        " ".join(h.root_cause.lower() + " " + " ".join(h.evidence).lower() for h in report.hypotheses)
    )
    matched_services = sum(1 for s in expected_services if s in all_report_text)
    if matched_services >= len(expected_services) * 0.5:
        scores["services_correct"] = 1

    for h in report.hypotheses:
        h_text = h.root_cause.lower()
        if h.confidence == "high" and any(kw in h_text for kw in cause_keywords):
            scores["high_confidence_correct"] = 1
            break

    return scores


def run_benchmark():
    """Run the full benchmark comparing two-agent vs single-agent."""
    with open(_LABELS_FILE, "r") as f:
        labels = json.load(f)

    print("=" * 70)
    print("Multi-Agent RCA Benchmark: Two-Agent vs Single-Agent")
    print("=" * 70)
    print(f"\nEvaluating {len(labels)} labeled log samples...\n")

    two_agent_scores = []
    single_agent_scores = []
    results = []

    for i, label in enumerate(labels):
        log_path = os.path.join(_LOGS_DIR, label["log_file"])
        if not os.path.exists(log_path):
            print(f"  [{i+1:2d}/20] SKIP - {label['log_file']} not found")
            continue

        print(f"  [{i+1:2d}/20] {label['log_file']} ({label['root_cause_category']})")

        # Two-agent pipeline
        try:
            two_agent_report = run_pipeline(log_path)
            two_score = score_report(two_agent_report, label)
            time.sleep(3)
        except Exception as e:
            print(f"         Two-agent ERROR: {e}")
            two_score = {"cause_correct": 0, "services_correct": 0, "high_confidence_correct": 0}

        # Single-agent baseline
        try:
            single_agent_report = run_single_agent(log_path)
            single_score = score_report(single_agent_report, label)
            time.sleep(3)
        except Exception as e:
            print(f"         Single-agent ERROR: {e}")
            single_score = {"cause_correct": 0, "services_correct": 0, "high_confidence_correct": 0}

        two_total = sum(two_score.values())
        single_total = sum(single_score.values())
        print(f"         Two-agent: {two_total}/3 | Single-agent: {single_total}/3")

        two_agent_scores.append(two_score)
        single_agent_scores.append(single_score)
        results.append({
            "log_file": label["log_file"],
            "category": label["root_cause_category"],
            "two_agent": two_score,
            "single_agent": single_score,
        })

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    two_cause = sum(s["cause_correct"] for s in two_agent_scores)
    two_svc = sum(s["services_correct"] for s in two_agent_scores)
    two_conf = sum(s["high_confidence_correct"] for s in two_agent_scores)
    two_total = two_cause + two_svc + two_conf

    single_cause = sum(s["cause_correct"] for s in single_agent_scores)
    single_svc = sum(s["services_correct"] for s in single_agent_scores)
    single_conf = sum(s["high_confidence_correct"] for s in single_agent_scores)
    single_total = single_cause + single_svc + single_conf

    n = len(two_agent_scores)
    max_total = n * 3

    print(f"\n{'Metric':<35} {'Two-Agent':>12} {'Single-Agent':>14}")
    print("-" * 63)
    print(f"{'Correct root cause identified':<35} {two_cause:>8}/{n:<3} {single_cause:>10}/{n:<3}")
    print(f"{'Affected services matched':<35} {two_svc:>8}/{n:<3} {single_svc:>10}/{n:<3}")
    print(f"{'High-confidence correct hypothesis':<35} {two_conf:>8}/{n:<3} {single_conf:>10}/{n:<3}")
    print("-" * 63)
    print(f"{'TOTAL':<35} {two_total:>8}/{max_total:<3} {single_total:>10}/{max_total:<3}")
    print(f"{'Accuracy':<35} {two_total/max_total*100:>7.1f}%    {single_total/max_total*100:>9.1f}%")

    # Save results
    os.makedirs(os.path.join(_BASE_DIR, "output"), exist_ok=True)
    results_path = os.path.join(_BASE_DIR, "output", "benchmark_results.json")
    with open(results_path, "w") as f:
        json.dump({
            "summary": {
                "two_agent_total": two_total,
                "single_agent_total": single_total,
                "max_score": max_total,
                "samples_evaluated": n,
                "two_agent_accuracy": round(two_total / max_total * 100, 1) if max_total > 0 else 0,
                "single_agent_accuracy": round(single_total / max_total * 100, 1) if max_total > 0 else 0,
            },
            "detailed_results": results,
        }, f, indent=2)

    print(f"\nDetailed results saved to: {results_path}")
    return two_total, single_total


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_benchmark()
