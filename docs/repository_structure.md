# Repository Structure

| Location | Ownership |
| --- | --- |
| `data/financial/` | Local raw sources, v1 panels, v2 target files, and data manifests. Ignored by Git. |
| `model/` | Proposed Regime-Gated Mamba and comparison model implementations. |
| `layers/` | Shared Mamba, embedding, normalization, decomposition, and attention layers. |
| `data_provider/` | Dataset classes and DataLoader construction. |
| `experiments/financial/` | Active S-only orchestration, learned runner, deterministic references, and shared evaluation helpers. |
| `utils/financial/` | Active data, release, evidence, profile, report, target, and archive utilities. |
| `configs/` | Three active configurations: data sources, v1 release, and v2 release. |
| `reproducibility/financial_s_only_v1/` | Tracked v1 release contract. |
| `reproducibility/financial_s_only_v2/` | Tracked v2 release contract. |
| `docs/` | Technical reference for the software and later manuscript drafting. |
| `backup/` | Ignored recoverable local archive; no active code reads it. |

## Supported Commands

```text
python scripts/data.py {download,prepare,preflight,materialize-targets,release-setup}
python scripts/evaluate.py --release {v1,v2} --stage {setup,plan,deterministic,train,replay,profile,report,verify}
python scripts/reproduce.py --workflow financial-s-only --release {v1,v2} --stage ...
python scripts/analyze.py {profile,report}
```

`run.py` remains a low-level manual experiment interface. It is not the reproducible
release path. The intended user-facing workflow is `scripts/reproduce.py` with the
single `financial-s-only` workflow.

There are no user-facing subdirectories inside `scripts/`. Old mixed S/MS and
publication-specific modules were removed rather than left as parallel entry points.
