# Independent External Confirmation

## Scope

V7 Traffic Hourly and V8 KDD Cup 2018 were prepared and frozen after the
V3-V6 diagnostics. Neither source contributed test outcomes to V3-V6 model
selection. Both sources used chronological train, validation, and test ranges;
all comparison tables are based on per-series seed means and paired bootstrap
inference.

## Confirmed Evidence

- V7 Traffic: M2 improved over M1 at horizons 3, 6, 12, and 24 after Holm
  adjustment. M3 did not improve over M2 at any all-state horizon.
- V8 KDD Cup 2018: M2 improved over M1 at horizon 6 for all and change-state
  units after Holm adjustment. M3 did not improve over M2 at any all-state
  horizon after Holm adjustment.
- V6 validation-selected model mixing was independently challenged by V7
  Traffic: the selected mixture was worse than M3 at horizons 3, 6, and 24.

## Allowed Claim

The evidence supports a bounded claim that ungated Mamba residual forecasting
can improve on the linear residual comparator in some independent domains and
horizons. It does not support a universal advantage, nor a cross-domain
confirmatory benefit of state-gated M3 over ungated M2.

## Consequence

The M3 gate remains a mechanism hypothesis with synthetic support and
domain-heterogeneous real evidence. Any future M3 claim requires a new,
predeclared mechanism-specific design with adequate stable-state coverage and
fresh external sources.
