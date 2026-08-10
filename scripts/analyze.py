#!/usr/bin/env python
"""Audit and rebuild financial benchmark analysis artifacts."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

COMMANDS = {
    "audit": "utils.financial.audit",
    "metrics": "utils.financial.results",
    "mamba-report": "utils.financial.mamba_rerun_report",
    "normalize": "utils.financial.identifiers",
    "forecast-plots": "utils.financial.forecast_plots",
    "profile": "utils.financial.profile",
    "report": "utils.financial.report",
    "runtime": "utils.financial.runtime",
}

NO_ARGUMENT_ACTIONS = {
    "profile": "Run the matched CUDA microbenchmark and replace the local timing CSV.",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument("action", choices=sorted(COMMANDS))
    if len(sys.argv) == 1 or sys.argv[1] in {"-h", "--help"}:
        parser.print_help()
        return
    args, remainder = parser.parse_known_args()
    if args.action in NO_ARGUMENT_ACTIONS and remainder in (["-h"], ["--help"]):
        print(f"usage: {parser.prog} {args.action}\n\n{NO_ARGUMENT_ACTIONS[args.action]}")
        return
    sys.argv = [f"{parser.prog} {args.action}", *remainder]
    importlib.import_module(COMMANDS[args.action]).main()


if __name__ == "__main__":
    main()
