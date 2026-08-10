#!/usr/bin/env python
"""Retain candidate checkpoints and replay forecasts from saved weights."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from experiments.financial.reproduce import main


if __name__ == "__main__":
    main()
