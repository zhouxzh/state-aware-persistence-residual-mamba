#!/usr/bin/env python
"""Manage financial reference data."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

COMMANDS = {
    "download": "utils.financial.download",
    "prepare": "utils.financial.prepare",
    "preflight": "utils.financial.preflight",
    "diagnose": "utils.financial.diagnostics",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument("action", choices=sorted(COMMANDS))
    if len(sys.argv) == 1 or sys.argv[1] in {"-h", "--help"}:
        parser.print_help()
        return
    args, remainder = parser.parse_known_args()
    sys.argv = [f"{parser.prog} {args.action}", *remainder]
    outcome = importlib.import_module(COMMANDS[args.action]).main()
    if isinstance(outcome, int):
        raise SystemExit(outcome)


if __name__ == "__main__":
    main()
