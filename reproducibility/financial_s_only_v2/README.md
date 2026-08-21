# financial_s_only_retrospective_v2

This is a tracked, checksum-covered completed result contract.
It uses target-only S inputs, frozen pre-2023 family selections, and a
retrospective 2023-01-01 to 2026-06-30 evaluation window.

Run `python scripts/data.py release-setup --release v2` before training.
Run `python scripts/reproduce.py --workflow financial-s-only --release v2 --stage verify` to inspect completeness.
Run `python scripts/analyze.py analysis --release financial_s_only_v2 --output-dir docs/analysis/financial_s_only_v2` to regenerate derived summaries after verification.

The release contains 5,940 learned horizon rows, 324 deterministic rows, and
5,940 retained learned checkpoints. It is retrospective. The complete V2
checkpoint reload and array-equality replay audit was verified locally on
2026-08-21 (`5,940/5,940` entries, no problems); regenerate that local record
with `--stage replay-verify` when replay outputs are available.
