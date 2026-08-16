# Repository Structure

| Location | Ownership |
| --- | --- |
| `data/financial/` | Local raw sources, v1 panels, v2 target files, and data manifests. Ignored by Git. |
| `model/` | Proposed Regime-Gated Mamba and comparison model implementations. |
| `layers/` | Shared Mamba, embedding, normalization, decomposition, and attention layers. |
| `data_provider/` | Dataset classes and DataLoader construction. |
| `experiments/financial/` | Active S-only orchestration, learned runner, deterministic references, and evaluation helpers. |
| `utils/financial/` | Data, release, evidence, report, profile, figure, and archive utilities. |
| `configs/` | Three active configurations: provider sources, v1 release, and v2 release. |
| `reproducibility/financial_s_only_v1/` | Tracked, checksum-covered v1 evidence contract. |
| `reproducibility/financial_s_only_v2/` | Tracked v2 data and deterministic-evidence contract. |
| `docs/` | Technical reference, figures, and manuscript-supporting evidence map. |
| `backup/` | Ignored recoverable local archive; no active code reads it. |

## Supported Commands

```text
python scripts/data.py {download,prepare,preflight,materialize-targets,release-setup}
python scripts/evaluate.py --release {v1,v2} --stage {setup,plan,deterministic,train,replay,replay-verify,profile,report,verify}
python scripts/reproduce.py --workflow financial-s-only --release {v1,v2} --stage ...
python scripts/analyze.py {figures,profile,report}
```

`run.py` is a low-level manual experiment interface, not the reproducible release
path. The intended public workflow is `scripts/reproduce.py` with the single
`financial-s-only` workflow. There are no user-facing subdirectories inside
`scripts/`; old mixed S/MS and publication-specific entry points were removed
rather than left as competing interfaces.
