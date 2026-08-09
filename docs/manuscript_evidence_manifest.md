# Manuscript Evidence Manifest

Updated: 2026-08-09

Use these evidence IDs when drafting or reviewing the manuscript. A factual sentence
should cite one or more IDs in the internal notes, table source column, or manuscript
provenance record. The IDs are local repository references, not external citations.

## Evidence records

| ID | Evidence | Source | Status and permitted use |
| --- | --- | --- | --- |
| E01 | Frozen protocol, splits, horizons, seeds, and R6 overrides | `configs/pms_mamba_v3.json` | Frozen; authoritative for Methods |
| E02 | R6 implementation and forward path | `model/PMS_Mamba.py` | Current source; audit before release |
| E03 | Gate promotion decision | `results/nonstationary_analysis_v5/gate/promotion_decision.json` | Completed; selection evidence |
| E04 | Gate aggregate metrics | `results/nonstationary_analysis_v5/gate/config_summary.csv` | Completed; exact R6/B0/NS values |
| E05 | Gate task/seed rows | `results/nonstationary_analysis_v5/gate/run_summary.csv` | Completed; task-level wins and audit |
| E06 | Matched inference profile | `results/nonstationary_analysis_v5/profile/matched_inference_profile.csv` | Provisional; repair metadata before publication |
| E07 | Profile protocol and interpretation | `docs/computational_profile.md` | Current narrative; no throughput claim yet |
| E08 | Historical common metric suite | `results/nonstationary_metric_suite/model_common_metric_summary.csv` | Context only; earlier PMS-Mamba-PD |
| E09 | Dataset descriptions and split audit | `docs/current_data.md` | Current narrative; verify against manifests |
| E10 | Dataset manifests and hashes | `data/financial/manifests/` | Reproducibility source |
| E11 | Detailed R6 architecture figure | `docs/figures/pmsv5_r6_architecture_tikz_rgb.png` and `.pdf` | Publication asset |
| E12 | Architecture source | `manuscript/figures/pmsv5_r6_architecture.tex` | Editable publication source |
| E13 | Historical architecture gallery | `docs/figures/all_model_architecture_gallery_tikz_rgb.png` and `.pdf` | Supplementary/context only |
| E14 | Remaining final-test and profile tasks | `docs/next_optimization_plan.md` | Blocking checklist |
| E15 | Manuscript wording and claim boundary | `docs/manuscript_writing_brief.md` | Reusable writing scaffold |

## Claim map

| Claim ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| C01 | R6 is the selected PMS-Mamba configuration | E01, E03, E04 | Supported on the 2022 gate |
| C02 | R6 balanced RMSSE is 6.0095 on the locked gate | E04 | Supported; report with gate label |
| C03 | R6 improves 15.00% vs B0 and 17.90% vs retuned NS-Mamba-D | E03, E04 | Supported; gate only |
| C04 | R6 wins six of eight tasks vs B0 and eight of eight vs retuned NS-Mamba-D | E03, E05 | Supported; descriptive |
| C05 | B0 is better than R6 on both FX gate tasks | E05 | Supported; descriptive stress case |
| C06 | R6 has lower recorded CUDA latency and allocated memory than PatchTST and TimesNet | E06, E07 | Provisional; metadata repair required |
| C07 | R6 is more accurate than PatchTST or TimesNet on the financial test | None yet | Unsupported; do not write |
| C08 | R6 is the best long-horizon model | None yet | Unsupported; requires horizon 252 final test |
| C09 | Historical PMS-Mamba-PD results establish R6 performance | E08 | Unsupported; configuration mismatch |
| C10 | Forecast gains imply trading profitability | None | Unsupported; requires economic evaluation |

## Artifact-to-manuscript map

| Manuscript location | Primary evidence IDs | Required check |
| --- | --- | --- |
| Introduction | E09, E14 | Keep motivation separate from results |
| Method | E01, E02, E11, E12 | Match text to implementation |
| Data and protocol | E01, E09, E10 | Verify dates, rows, and hashes |
| Selection result | E03, E04, E05 | Label as 2022 merge gate |
| Final accuracy result | Pending final output | Include all baselines and horizon 252 |
| Efficiency result | E06, E07 plus repaired profile | Include hardware/software metadata |
| Historical comparison | E08 | Label earlier PMS-Mamba-PD explicitly |
| Reproducibility | E01, E02, E10, E12 | Add commit, environment, and checksums |

## Evidence integrity rules

1. Never merge gate, historical-suite, smoke, and final-test values into one ranking.
2. Keep row-level predictions and metric rows so every aggregate can be recomputed.
3. Mark any result with an unknown config hash, commit, seed, or manifest as excluded
   until provenance is restored.
4. Do not use `FIN_SMOKE` artifacts as final evidence.
5. Record whether a number is a mean, median, confidence interval, or single run.

