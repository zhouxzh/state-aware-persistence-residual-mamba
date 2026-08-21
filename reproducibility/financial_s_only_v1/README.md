# financial_s_only_retrospective_v1

This is a tracked, checksum-covered completed result contract.
It uses target-only S inputs, frozen pre-2023 family selections, and a
retrospective 2023-01-01 to 2026-06-30 evaluation window.

Run `python scripts/data.py release-setup --release v1` before training.
Run `python scripts/reproduce.py --workflow financial-s-only --release v1 --stage verify` to inspect completeness.
The detailed current analysis is the separate V2 record at
`docs/v2_evaluation_record.md`; V1 remains a four-target historical release.
