# Multi-Agent Root Cause Analyzer

A two-agent LangChain pipeline that analyzes raw server logs and produces structured root cause analysis reports. Built to demonstrate how multi-agent architectures with structured data contracts outperform monolithic single-agent approaches for complex reasoning tasks.

## Why I Built This

Every on-call engineer has been there: it's 3 AM, a production incident is unfolding, and you're staring at thousands of log lines trying to piece together what went wrong. The mental process is always the same: first you scan for anomalies, then you cross-reference what you find against known failure patterns, and finally you form hypotheses about root cause. I built this project to automate that exact workflow using a multi-agent LLM pipeline, where each agent handles one cognitive step with a well-defined data contract between them. The result is faster, more structured incident diagnosis that catches patterns a sleep-deprived human might miss.

## Architecture

```
                    Multi-Agent RCA Pipeline
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │   Raw Logs (.log file)                                  │
  │        │                                                │
  │        ▼                                                │
  │   ┌──────────────────────┐                              │
  │   │  Agent 1: Log        │                              │
  │   │  Analyzer            │                              │
  │   │  (ChatGroq + LLM)    │                              │
  │   │                      │                              │
  │   │  - Reads raw logs    │                              │
  │   │  - Chunks 50-line    │                              │
  │   │    blocks            │                              │
  │   │  - Extracts anomalies│                              │
  │   └──────────┬───────────┘                              │
  │              │                                          │
  │              ▼                                          │
  │   ┌──────────────────────┐                              │
  │   │  LogFindings         │  ◄── Pydantic Schema         │
  │   │  (Structured Data)   │      Enforced by LLM         │
  │   │                      │                              │
  │   │  - anomalies[]       │                              │
  │   │  - affected_services │                              │
  │   │  - timeline_summary  │                              │
  │   └──────────┬───────────┘                              │
  │              │                                          │
  │              ▼                                          │
  │   ┌──────────────────────┐    ┌─────────────────────┐   │
  │   │  Agent 2: Hypothesis │◄───│  ChromaDB           │   │
  │   │  Agent               │    │  Knowledge Base     │   │
  │   │  (ChatGroq + LLM)    │    │                     │   │
  │   │                      │    │  17 failure patterns │   │
  │   │  - Queries KB        │    │  with symptoms,     │   │
  │   │  - Chain-of-thought  │    │  causes, resolutions│   │
  │   │  - Ranks hypotheses  │    └─────────────────────┘   │
  │   └──────────┬───────────┘                              │
  │              │                                          │
  │              ▼                                          │
  │   ┌──────────────────────┐                              │
  │   │  RootCauseReport     │  ◄── Pydantic Schema         │
  │   │  (Structured Output) │      Enforced by LLM         │
  │   │                      │                              │
  │   │  - hypotheses[]      │                              │
  │   │  - most_likely_cause │                              │
  │   │  - immediate_actions │                              │
  │   └──────────────────────┘                              │
  │                                                         │
  └─────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### Why Two Agents Instead of One?

A single agent asked to go from raw logs to root cause in one shot has to juggle too many concerns simultaneously: parsing log formats, identifying anomalies, assessing severity, cross-referencing patterns, and formulating hypotheses. By splitting this into two agents with a structured handoff, each agent can focus on what it does best. Agent 1 is a specialist in log parsing and anomaly extraction. Agent 2 is a specialist in causal reasoning and hypothesis ranking. The Pydantic schema between them acts as a contract that makes the data flow explicit and debuggable.

### Why Pydantic Schemas at the Boundary?

Without structured output enforcement, LLMs produce inconsistent formats that break downstream processing. Using LangChain's `.with_structured_output()` with Pydantic models means the LLM is constrained to produce valid, typed data. If Agent 1 returns malformed findings, Pydantic catches it immediately rather than letting garbage propagate to Agent 2. This is the same principle as typed interfaces in software engineering: contracts between components prevent entire categories of bugs.

### Why ChromaDB Over Simple Keyword Lookup?

Failure patterns don't always match exact keywords. A log saying "connection refused" should match a knowledge base entry about "network partition" even though those phrases share no words. ChromaDB uses semantic embeddings (via the all-MiniLM-L6-v2 model) to find conceptually similar patterns, not just lexical matches. This means the knowledge base gets smarter without needing hand-crafted keyword mappings.

## Benchmark Results

The benchmark evaluates both approaches on 20 labeled HDFS log samples using a 3-point scoring rubric per sample:

1. **Root cause identification**: Does `most_likely_cause` mention the correct category?
2. **Service identification**: Are the correct affected services found in the report?
3. **High-confidence accuracy**: Does at least one hypothesis have the right cause with `confidence: "high"`?

To run the benchmark yourself:

```bash
python benchmark/evaluate.py
```

Results will be printed to stdout and saved to `output/benchmark_results.json`.

> **Note:** Benchmark results depend on the Groq API and the llama3-8b-8192 model. Results may vary slightly between runs due to LLM non-determinism, but the two-agent pipeline consistently outperforms the single-agent baseline due to the structured intermediate reasoning step and knowledge base augmentation.

## Project Structure

```
multi-agent-rca/
├── agents/
│   ├── log_analyzer.py        # Agent 1: Raw logs → LogFindings
│   └── hypothesis_agent.py    # Agent 2: LogFindings → RootCauseReport
├── schemas/
│   ├── findings.py            # LogFindings + AnomalyEvent Pydantic models
│   └── report.py              # RootCauseReport + Hypothesis Pydantic models
├── knowledge_base/
│   ├── loader.py              # ChromaDB init + query functions
│   └── failure_patterns.json  # 17 seed failure patterns
├── data/
│   └── sample_logs/           # HDFS log samples (4 demos + 20 benchmark)
├── pipeline/
│   └── rca_pipeline.py        # Wires Agent 1 → Agent 2
├── benchmark/
│   ├── evaluate.py            # Two-agent vs single-agent comparison
│   └── labels.json            # Ground truth for 20 benchmark samples
├── tests/                     # Schema, agent, and KB tests
├── main.py                    # CLI entrypoint
├── requirements.txt
├── .env.example
└── README.md
```

## How to Run

### Prerequisites

- Python 3.10+
- A free [Groq API key](https://console.groq.com/keys)

### Setup

```bash
# Clone the repository
git clone https://github.com/sshaurya84/Multi-Agent-Root-Cause-Analyzer.git
cd Multi-Agent-Root-Cause-Analyzer

# Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure your API key
cp .env.example .env
# Edit .env and add your Groq API key
```

### Analyze a Log File

```bash
python main.py data/sample_logs/hdfs_sample_1.log -v
```

This will:
1. Read the log file
2. Run Agent 1 (Log Analyzer) to extract structured findings
3. Run Agent 2 (Hypothesis Agent) to produce ranked root cause hypotheses
4. Print the JSON report to stdout
5. Save the report to `output/report_YYYYMMDD_HHMMSS.json`

### Run the Benchmark

```bash
python benchmark/evaluate.py
```

### Run Tests

```bash
# Schema validation tests (no API key needed)
python tests/test_schemas.py

# Knowledge base tests (no API key needed)
python tests/test_knowledge_base.py

# Agent tests (requires GROQ_API_KEY)
python tests/test_log_analyzer.py
python tests/test_hypothesis_agent.py
```

## What I Learned

**The Pydantic boundary was the best decision.** Early prototypes without structured output produced wildly inconsistent formats between Agent 1 and Agent 2. Adding `.with_structured_output()` eliminated an entire class of integration bugs and made debugging trivial: if something went wrong, I could inspect the exact `LogFindings` object at the boundary.

**Chunking was harder than expected.** HDFS logs can be thousands of lines. Naively feeding them all to the LLM either exceeded the context window or produced shallow analysis. Splitting into 50-line chunks and merging findings required careful deduplication logic to avoid counting the same anomaly twice when it appeared at chunk boundaries.

**ChromaDB's semantic search was surprisingly effective.** I expected to need careful prompt engineering to get useful KB matches, but the default MiniLM embeddings did a good job matching symptom descriptions to failure patterns even when the vocabulary didn't overlap. The distance scores in query results provided a useful confidence signal.

**Rate limiting on the free tier is real.** The Groq free tier has strict rate limits (30 requests/minute). The benchmark script needed retry logic with exponential backoff to avoid crashing mid-evaluation. In a production system, this would need proper queue management.

**If I were to do this again,** I'd add a third agent for remediation planning that takes the `RootCauseReport` and generates runbooks, and I'd implement streaming output so the user sees partial results as each agent completes rather than waiting for the full pipeline.

## Tech Stack

- **Python 3.10+**
- **LangChain + LangChain-Groq**: LLM orchestration and structured output
- **Groq API** (llama3-8b-8192): Fast, free-tier LLM inference
- **Pydantic v2**: Data validation and typed contracts between agents
- **ChromaDB**: Vector database for semantic failure pattern matching
- **python-dotenv**: Environment variable management
