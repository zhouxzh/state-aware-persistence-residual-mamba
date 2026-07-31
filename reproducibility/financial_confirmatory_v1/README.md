# Financial Confirmatory V1 Reproducibility Snapshot

This tracked snapshot freezes the nonstationary forecasting reference benchmark
configuration used for the financial data family. It contains no raw or processed
market data.

Contents:

- `protocol/financial_benchmark.json`: frozen evaluation protocol.
- `selection/`: 16 validation-only Optuna selection files covering eight tasks and
  nine learned models.
- `manifests/`: source provenance, processed-data hashes, split/task definitions,
  data-quality metadata, and selection-safe nonstationarity diagnostics.
- `SHA256SUMS`: integrity hashes for every snapshot payload file.

The files under `selection/` are publication snapshots of the runtime files normally
stored in `results/optuna/`. Do not move or edit the runtime copies while completing
the frozen benchmark. To execute the final benchmark, acquire permitted source data,
recreate and verify `data/financial/`, then place the selection files at the runtime
paths expected by `scripts/financial/run_financial_benchmark.py`.

This snapshot records validation selection only. It contains no protected final-test
predictions, final metrics, checkpoints, or claims of confirmatory performance.
