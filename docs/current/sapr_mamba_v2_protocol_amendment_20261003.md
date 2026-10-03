# SAPR-Mamba V2 Protocol Amendment

V1 artifacts are retained as development evidence. V2 is the first unified
confirmation protocol for this implementation.

V1's synthetic and real task matrices completed, but fixed ETS/ARIMA candidates
could emit numerical or convergence warnings without a corresponding `failures.csv`
entry. The original plan requires statistical non-convergence to be retained as a
failure with the fixed persistence fallback.

V2 keeps the verified public raw sources, causal state features, model geometry,
seeds, splits, metrics, and primary comparisons. It changes only this failure
accounting rule: `ConvergenceWarning` or `RuntimeWarning` during a statistical fit
invalidates that fit, writes the warning to `failures.csv`, and invokes the
predefined persistence fallback where no valid candidate remains.

V2 uses independent paths `configs/data/results/reproducibility/docs/*/sapr_mamba_v2`.
It does not overwrite or pool V1 artifacts.
