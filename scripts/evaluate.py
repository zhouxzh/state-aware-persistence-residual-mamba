#!/usr/bin/env python
"""Compatibility entry point for the active S-only financial workflow."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from experiments.financial.s_only import main


if __name__ == "__main__":
    main()
