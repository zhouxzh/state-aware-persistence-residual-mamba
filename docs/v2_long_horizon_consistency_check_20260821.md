# V2 Supplement Long-Horizon Consistency Check

## Decision

The local run is a post hoc, non-independent V2 long-horizon consistency and
replay supplement. It is recorded as `financial_s_only_v2_supplement`; it is not
a new primary release, ranking, or confirmatory conclusion. The manuscript
remains V2-primary.

The legacy internal run ID is retained in commands and historical records so that
the run remains auditable. The compact release is named
`financial_s_only_v2_supplement`; this rename is a scientific classification, not
a rewrite of the underlying evidence.

## Remote Verification

Read-only preflight at `2026-08-21 19:35:54 CST` reported:

- remote: `zhong@ace2:/home/zhong/Documents/pms-mamba-financial-forecasting`;
- branch `main`, commit `8f53a8925aff607afb4575ed93890d49d8523f8d`;
- 65 dirty entries, with no active training, analysis, Optuna, or benchmark process;
- idle RTX 5090 D and approximately 265 GB free on the execution volume.

The remote release contract is
`reproducibility/financial_s_only_v2_supplement/`. Its `release_status.json`
reports `verified`, 540/540 learned rows, zero problems, and evidence status
`retrospective_supplement`. The remote replay record at
`results/financial_s_only_v2_supplement/replay/replay_validation.json` reports
540/540 validated entries, zero problems, zero maximum prediction/truth
differences, and exact date matches. The release checksum manifest SHA-256 is
`03057b85904519f833333a8bd0bf629d97629e1abd5d1b6a860d7e39df0c198d`.

The compact supplement remains outside the tracked Git tree because it is not
part of the V2-primary manuscript evidence. The verified local contract and
ignored forecast/checkpoint artifacts are available for audit on this machine;
any future staged copy must verify stable files and the published checksum
manifest first.

## Why It Is Not Independent

The check reuses all 18 V2 target-only series, the same data hashes and split
boundaries, the same retrospective evaluation window (2023-01-01 through
2026-06-30), the same frozen pre-2023 family selections, and the same five seeds.
It retains only Regime-Gated Mamba and Ungated Regime-Linear Mamba at horizons
60, 120, and 252 (18 x 2 x 5 x 3 = 540 learned cells); it adds no deterministic
references, baseline reruns, new target data, new selection search, or untouched
test period.

Direct V2-versus-supplement comparisons for the shared long-horizon cells agree
to floating-point tolerance (maximum absolute differences were below 5e-7 for
the reported path metrics). The apparent change in multiplicity-adjusted p-values
when only three horizons are considered is a change in the comparison family,
not new information. It must not replace the V2 full-family inference or update
the 14-method ranking.

## Reporting Boundary

Use the checksum-covered V2 release for all primary tables, figures, rankings,
baseline comparisons, and manuscript numbers. If the consistency check is ever
mentioned, call it a "post hoc V2 long-horizon consistency/replay check" and state
that it is non-independent and retrospective. It may support an audit or a
carefully bounded supplementary robustness sentence only; it cannot support a
fresh generalization claim, prospective claim, overall superiority claim, or
speed claim.

Historical synchronization snapshots and manifests are preserved unchanged.
They describe their observation time and are not current evidence decisions.
