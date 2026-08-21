# V2 Derived Analysis

These tables are derived from the checksum-covered
`reproducibility/financial_s_only_v2` release. They are not a second evaluation
protocol and do not modify the frozen metric tables.

Generate them with:

```bash
conda run --no-capture-output -n sci-agent python scripts/analyze.py analysis \
  --release financial_s_only_v2 \
  --output-dir docs/analysis/financial_s_only_v2
```

`model_summary.csv`, `horizon_summary.csv`, `family_summary.csv`, and
`target_summary.csv` contain rank-based summaries. `regime_gated_cell_metrics.csv`
contains all 108 target-horizon cells for the proposed model, including raw
target-scale MAE/RMSE, path RMSSE, ranks, signed RMSSE deltas, and ratios to
named references. `seed_stability.csv` records the five learned-seed dispersion
and rank summaries. `summary.json` records the release counts and bounded
headline findings; `analysis_manifest.json` binds every output to source hashes
and transformation definitions.

Path RMSSE is the pooled ranking metric. Raw MAE and RMSE are not averaged across
different target scales; cross-target summaries use explicitly named ratios,
primarily Regime-Gated Mamba divided by LastValue.
