import argparse
import json
import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from pipeline.rca_pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent Root Cause Analyzer — Analyze server logs and produce structured RCA reports."
    )
    parser.add_argument("log_file", help="Path to the log file to analyze")
    parser.add_argument(
        "-o", "--output-dir",
        default="output",
        help="Directory to save the report (default: output/)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not os.path.exists(args.log_file):
        print(f"Error: Log file not found: {args.log_file}", file=sys.stderr)
        sys.exit(1)

    report = run_pipeline(args.log_file)

    report_json = json.loads(report.model_dump_json(indent=2))
    print(json.dumps(report_json, indent=2))

    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(args.output_dir, f"report_{timestamp}.json")
    with open(output_path, "w") as f:
        json.dump(report_json, f, indent=2)

    print(f"\nReport saved to: {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
