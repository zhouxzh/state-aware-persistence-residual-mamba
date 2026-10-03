"""Compatibility command entry point for SAPR-Mamba data preflight."""

from __future__ import annotations

import json

from experiments.sapr_mamba.run import preflight


def main() -> None:
    print(json.dumps(preflight(), indent=2, sort_keys=True))
