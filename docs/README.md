# Technical Documentation

This directory is the technical record for the reviewer-facing software release. It
contains the data specification, model definition, completed evaluation record, and
commands required to reproduce or audit the supplied artifacts. It does not contain
manuscript material.

| Document | Purpose |
| --- | --- |
| [data_reference.md](data_reference.md) | Financial reference panels, tasks, splits, and data-policy boundary. |
| [model_reference.md](model_reference.md) | Regime-Gated Mamba architecture, comparisons, and canonical model names. |
| [evaluation_record.md](evaluation_record.md) | Completed evaluation, horizon-specific performance, and limitations. |
| [computational_profile.md](computational_profile.md) | Matched CUDA inference microbenchmark. |
| [final_evaluation_record.md](final_evaluation_record.md) | Frozen evaluation protocol and status. |
| [evidence_registry.md](evidence_registry.md) | Files that substantiate technical statements. |
| [reproducibility.md](reproducibility.md) | Environment setup, workflow, and validation commands. |
| [results_inventory.md](results_inventory.md) | Retained manuscript evidence versus archived local workspaces. |

| Canonical ID | Reader-facing name | Role |
| --- | --- | --- |
| `RegimeGatedMamba` | Regime-Gated Mamba | Selected proposed model. |
| `MultiScalePatchMamba` | Multi-Scale Patch Mamba | Architectural ablation. |
| `InvertedMamba` | Inverted Mamba | Mamba baseline. |
| `DecompositionMamba` | Decomposition Mamba | Mamba baseline. |
| `MultiScaleDecompositionMamba` | Multi-Scale Decomposition Mamba | Mamba baseline. |

Frozen records retain a `source_model_id` column so historical runs remain auditable
without exposing implementation-era model names as public identities.
