#!/usr/bin/env python
"""Retain checkpoints and replay forecasts from saved weights."""

import argparse
import importlib
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


WORKFLOWS = {
    "financial-s-only": "experiments.financial.s_only",
    "sapr-mamba": "experiments.sapr_mamba.run",
    "sapr-mamba-analysis": "experiments.sapr_mamba.analyze",
}


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--workflow", choices=sorted(WORKFLOWS), default="financial-s-only")
    args, remainder = parser.parse_known_args()
    sys.argv = [sys.argv[0], *remainder]
    importlib.import_module(WORKFLOWS[args.workflow]).main()


if __name__ == "__main__":
    main()
