"""CLI to run the pipeline on files or an input directory."""

from __future__ import annotations

import argparse
from pathlib import Path

from main import build_pipeline
from src.utils.io import collect_input_files


def main() -> None:
    """Run the auto-adjudication pipeline from the command line."""
    parser = argparse.ArgumentParser(description="Run the AB PMJAY claim pipeline.")
    parser.add_argument("--input-dir", default="data/input", help="Directory containing claim documents.")
    parser.add_argument("--claim-id", default=None, help="Optional claim identifier.")
    args = parser.parse_args()

    files = [str(path) for path in collect_input_files(args.input_dir)]
    if not files:
        sample = Path(args.input_dir) / "claim_form.png"
        sample.parent.mkdir(parents=True, exist_ok=True)
        sample.touch(exist_ok=True)
        files = [str(sample)]

    payload = build_pipeline().run(files, claim_id=args.claim_id)
    print(payload["decision"])


if __name__ == "__main__":
    main()
