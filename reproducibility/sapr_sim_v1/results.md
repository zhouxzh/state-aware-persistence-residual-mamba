# SAPR SIM_V1 Results

This report is generated solely from frozen `sim_v1` task archives. It does not pool V2/V3 or real-data results.

## Decision

- `T0_safety_pass`: `True`
- `T2_leakage_pass`: `False`
- `T8_random_walk_pass`: `True`
- `patch_candidate_groups`: `['T4', 'T6']`
- `patch_claim_pass`: `False`
- `gate_open_evidence`: `True`
- `gate_close_evidence`: `False`
- `state_gate_claim_pass`: `False`

## Coverage

| Mechanism | true stable | true visible | true unseen | detector stable | detector change |
|---|---:|---:|---:|---:|---:|
| stable | 3400 | 0 | 0 | 2765 | 635 |
| visible_level_shift | 795 | 905 | 0 | 1286 | 414 |
| future_jump | 1600 | 0 | 100 | 1243 | 457 |
| continuing_trend | 0 | 1700 | 0 | 1436 | 264 |
| trend_break | 795 | 905 | 0 | 1367 | 333 |
| stable_season | 3400 | 0 | 0 | 2874 | 526 |
| seasonal_change | 795 | 905 | 0 | 1370 | 330 |
| variance_shift | 795 | 905 | 0 | 1282 | 418 |
| random_walk | 1700 | 0 | 0 | 1347 | 353 |

## Frozen Comparisons

Negative estimates favor the left model. Bootstrap units are independent test sequences after averaging matched seeds. Holm adjustment is within the frozen A-H family.

| family | group | comparison | H | metric | n | estimate | 95% CI | Holm p |
|---|---|---|---:|---|---:|---:|---|---:|
| A | T0 | M2 - M0 | 12 | relative_series_rmse | 200 | -0.244639 | [-0.254901, -0.234797] | 0 |
| A | T0 | M3 - M0 | 12 | relative_series_rmse | 200 | -0.248106 | [-0.257905, -0.238260] | 0 |
| B | T2 | M1 - M0 | 12 | series_rmse_difference | 100 | -0.165137 | [-0.260071, -0.079269] | 0.001 |
| B | T2 | DLinear - M0 | 12 | series_rmse_difference | 100 | -0.174261 | [-0.262552, -0.094008] | 0 |
| B | T2 | M2 - M0 | 12 | series_rmse_difference | 100 | -0.317750 | [-0.434074, -0.210371] | 0 |
| B | T2 | M3 - M0 | 12 | series_rmse_difference | 100 | -0.323873 | [-0.441915, -0.218440] | 0 |
| C | T3 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.064985 | [-0.079560, -0.050579] | 0 |
| C | T3 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.056978 | [-0.068186, -0.045806] | 0 |
| C | T4 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.101277 | [-0.117444, -0.084677] | 0 |
| C | T4 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.031282 | [-0.045142, -0.017503] | 0 |
| C | T6 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.124815 | [-0.148154, -0.101890] | 0 |
| C | T6 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.075251 | [-0.091676, -0.058726] | 0 |
| D | T0 | M3 - M3-constant-gate | 12 | series_rmse_difference | 200 | -0.000838 | [-0.002912, 0.001238] | 1 |
| D | T2 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.000583 | [-0.012651, 0.010533] | 1 |
| D | T3 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.002946 | [-0.008474, 0.002390] | 1 |
| D | T4 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.028339 | [-0.040338, -0.016457] | 0 |
| D | T6 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.001453 | [-0.007549, 0.004863] | 1 |
| D | T7 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.015499 | [-0.033054, 0.001359] | 1 |
| D | T8 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.064396 | [-0.085487, -0.044360] | 0 |
| D | T0 | M3 - M0 | 12 | series_rmse_difference | 200 | -0.404060 | [-0.424370, -0.383797] | 0 |
| D | T2 | M3 - M0 | 12 | series_rmse_difference | 100 | -0.323873 | [-0.438633, -0.218205] | 0 |
| D | T7 | M3 - M0 | 12 | series_rmse_difference | 100 | -1.227941 | [-1.355426, -1.103955] | 0 |
| D | T8 | M3 - M0 | 12 | series_rmse_difference | 100 | 0.058790 | [0.037531, 0.081591] | 0 |
| E | T7 | M1 - M0 | 12 | series_rmse_difference | 100 | -0.764404 | [-0.863903, -0.665083] | 0 |
| E | T7 | M2 - M0 | 12 | series_rmse_difference | 100 | -1.199049 | [-1.320995, -1.075781] | 0 |
| E | T7 | M3 - M0 | 12 | series_rmse_difference | 100 | -1.227941 | [-1.354151, -1.104025] | 0 |
| F | T1 | M1 - M0 | 12 | series_rmse_difference | 100 | -0.254357 | [-0.291257, -0.217530] | 0 |
| F | T1 | DLinear - M0 | 12 | series_rmse_difference | 100 | -0.271152 | [-0.310375, -0.234190] | 0 |
| F | T1 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.105137 | [-0.130675, -0.080892] | 0 |
| F | T1 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.088343 | [-0.110316, -0.066993] | 0 |
| F | T4 | M2 - M0 | 12 | series_rmse_difference | 100 | -0.314043 | [-0.343715, -0.283256] | 0 |
| F | T4 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.101277 | [-0.117584, -0.085070] | 0 |
| F | T4 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.031282 | [-0.045378, -0.017267] | 0 |
| F | T6 | M2 - M0 | 12 | series_rmse_difference | 100 | -1.100701 | [-1.157070, -1.045041] | 0 |
| F | T6 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.124815 | [-0.147885, -0.101022] | 0 |
| F | T6 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.075251 | [-0.091806, -0.058479] | 0 |
| G | T8 | M1 - M0 | 12 | series_rmse_difference | 100 | 0.414350 | [0.354207, 0.474251] | 0 |
| G | T8 | DLinear - M0 | 12 | series_rmse_difference | 100 | 0.528543 | [0.468254, 0.588565] | 0 |
| G | T8 | M2 - M0 | 12 | series_rmse_difference | 100 | 0.141532 | [0.109996, 0.173896] | 0 |
| G | T8 | M3 - M0 | 12 | series_rmse_difference | 100 | 0.058790 | [0.037215, 0.081525] | 0 |
| H | T5 | M0 - SeasonalNaive | 12 | series_rmse_difference | 200 | 0.519884 | [0.485722, 0.555178] | 0 |
| H | T5 | M2 - SeasonalNaive | 12 | series_rmse_difference | 200 | -0.469217 | [-0.482697, -0.455647] | 0 |
| H | T5 | M3 - SeasonalNaive | 12 | series_rmse_difference | 200 | -0.479718 | [-0.493445, -0.465834] | 0 |
| A | T0 | M2 - M0 | 24 | relative_series_rmse | 200 | -0.256031 | [-0.264711, -0.247503] | 0 |
| A | T0 | M3 - M0 | 24 | relative_series_rmse | 200 | -0.259418 | [-0.267960, -0.250867] | 0 |
| B | T2 | M1 - M0 | 24 | series_rmse_difference | 100 | -0.183651 | [-0.270239, -0.102353] | 0 |
| B | T2 | DLinear - M0 | 24 | series_rmse_difference | 100 | -0.181080 | [-0.263856, -0.106461] | 0 |
| B | T2 | M2 - M0 | 24 | series_rmse_difference | 100 | -0.310169 | [-0.417456, -0.215320] | 0 |
| B | T2 | M3 - M0 | 24 | series_rmse_difference | 100 | -0.315607 | [-0.424206, -0.216550] | 0 |
| C | T3 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.073230 | [-0.086140, -0.060283] | 0 |
| C | T3 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.072240 | [-0.082495, -0.061939] | 0 |
| C | T4 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.140689 | [-0.156695, -0.124558] | 0 |
| C | T4 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.066173 | [-0.079742, -0.052596] | 0 |
| C | T6 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.218915 | [-0.241066, -0.196573] | 0 |
| C | T6 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.141133 | [-0.159003, -0.123319] | 0 |
| D | T0 | M3 - M3-constant-gate | 24 | series_rmse_difference | 200 | -0.000070 | [-0.001790, 0.001616] | 1 |
| D | T2 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.002369 | [-0.013811, 0.007332] | 1 |
| D | T3 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.000292 | [-0.004780, 0.004029] | 1 |
| D | T4 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.036067 | [-0.046846, -0.025044] | 0 |
| D | T6 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | 0.002554 | [-0.001909, 0.007010] | 1 |
| D | T7 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.014936 | [-0.031295, 0.002059] | 1 |
| D | T8 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.057792 | [-0.080496, -0.036068] | 0 |
| D | T0 | M3 - M0 | 24 | series_rmse_difference | 200 | -0.432205 | [-0.451862, -0.412971] | 0 |
| D | T2 | M3 - M0 | 24 | series_rmse_difference | 100 | -0.315607 | [-0.427100, -0.217721] | 0 |
| D | T7 | M3 - M0 | 24 | series_rmse_difference | 100 | -1.302231 | [-1.425045, -1.178365] | 0 |
| D | T8 | M3 - M0 | 24 | series_rmse_difference | 100 | 0.057433 | [0.036607, 0.080213] | 0 |
| E | T7 | M1 - M0 | 24 | series_rmse_difference | 100 | -0.828497 | [-0.930040, -0.724700] | 0 |
| E | T7 | M2 - M0 | 24 | series_rmse_difference | 100 | -1.269609 | [-1.388045, -1.154425] | 0 |
| E | T7 | M3 - M0 | 24 | series_rmse_difference | 100 | -1.302231 | [-1.425714, -1.183645] | 0 |
| F | T1 | M1 - M0 | 24 | series_rmse_difference | 100 | -0.292328 | [-0.332016, -0.255058] | 0 |
| F | T1 | DLinear - M0 | 24 | series_rmse_difference | 100 | -0.288381 | [-0.327377, -0.251040] | 0 |
| F | T1 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.100137 | [-0.122306, -0.079116] | 0 |
| F | T1 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.104084 | [-0.123393, -0.085728] | 0 |
| F | T4 | M2 - M0 | 24 | series_rmse_difference | 100 | -0.407828 | [-0.441574, -0.374243] | 0 |
| F | T4 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.140689 | [-0.156191, -0.124702] | 0 |
| F | T4 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.066173 | [-0.079130, -0.052474] | 0 |
| F | T6 | M2 - M0 | 24 | series_rmse_difference | 100 | -1.049832 | [-1.087119, -1.012503] | 0 |
| F | T6 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.218915 | [-0.240816, -0.196751] | 0 |
| F | T6 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.141133 | [-0.159228, -0.123365] | 0 |
| G | T8 | M1 - M0 | 24 | series_rmse_difference | 100 | 0.374980 | [0.321195, 0.429898] | 0 |
| G | T8 | DLinear - M0 | 24 | series_rmse_difference | 100 | 0.472721 | [0.411712, 0.531974] | 0 |
| G | T8 | M2 - M0 | 24 | series_rmse_difference | 100 | 0.131154 | [0.099078, 0.164034] | 0 |
| G | T8 | M3 - M0 | 24 | series_rmse_difference | 100 | 0.057433 | [0.036659, 0.079302] | 0 |
| H | T5 | M0 - SeasonalNaive | 24 | series_rmse_difference | 200 | 0.613831 | [0.581121, 0.647419] | 0 |
| H | T5 | M2 - SeasonalNaive | 24 | series_rmse_difference | 200 | -0.448489 | [-0.458353, -0.438458] | 0 |
| H | T5 | M3 - SeasonalNaive | 24 | series_rmse_difference | 200 | -0.473468 | [-0.482819, -0.463797] | 0 |
| A | T0 | M2 - M0 | 48 | relative_series_rmse | 200 | -0.260946 | [-0.269496, -0.252849] | 0 |
| A | T0 | M3 - M0 | 48 | relative_series_rmse | 200 | -0.264590 | [-0.272958, -0.256234] | 0 |
| B | T2 | M1 - M0 | 48 | series_rmse_difference | 100 | -0.194192 | [-0.279011, -0.117603] | 0 |
| B | T2 | DLinear - M0 | 48 | series_rmse_difference | 100 | -0.186665 | [-0.265174, -0.112654] | 0 |
| B | T2 | M2 - M0 | 48 | series_rmse_difference | 100 | -0.310553 | [-0.408121, -0.219595] | 0 |
| B | T2 | M3 - M0 | 48 | series_rmse_difference | 100 | -0.320215 | [-0.426550, -0.225875] | 0 |
| C | T3 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.106399 | [-0.120472, -0.092769] | 0 |
| C | T3 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.090212 | [-0.100874, -0.079730] | 0 |
| C | T4 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.243825 | [-0.261358, -0.226083] | 0 |
| C | T4 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.172686 | [-0.186120, -0.158761] | 0 |
| C | T6 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.274859 | [-0.295767, -0.253786] | 0 |
| C | T6 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.140555 | [-0.155736, -0.125871] | 0 |
| D | T0 | M3 - M3-constant-gate | 48 | series_rmse_difference | 200 | -0.000166 | [-0.001599, 0.001239] | 1 |
| D | T2 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.006455 | [-0.017756, 0.002234] | 1 |
| D | T3 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | 0.008927 | [0.005618, 0.012189] | 0 |
| D | T4 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.023970 | [-0.032987, -0.014662] | 0 |
| D | T6 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.000613 | [-0.003840, 0.002692] | 1 |
| D | T7 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.013889 | [-0.027275, -0.000288] | 0.7786 |
| D | T8 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.071159 | [-0.099708, -0.042853] | 0 |
| D | T0 | M3 - M0 | 48 | series_rmse_difference | 200 | -0.446290 | [-0.465626, -0.427154] | 0 |
| D | T2 | M3 - M0 | 48 | series_rmse_difference | 100 | -0.320215 | [-0.422985, -0.227689] | 0 |
| D | T7 | M3 - M0 | 48 | series_rmse_difference | 100 | -1.338092 | [-1.454670, -1.222079] | 0 |
| D | T8 | M3 - M0 | 48 | series_rmse_difference | 100 | 0.050861 | [0.031869, 0.070872] | 0 |
| E | T7 | M1 - M0 | 48 | series_rmse_difference | 100 | -0.865732 | [-0.964252, -0.768716] | 0 |
| E | T7 | M2 - M0 | 48 | series_rmse_difference | 100 | -1.309197 | [-1.424982, -1.197298] | 0 |
| E | T7 | M3 - M0 | 48 | series_rmse_difference | 100 | -1.338092 | [-1.458928, -1.216798] | 0 |
| F | T1 | M1 - M0 | 48 | series_rmse_difference | 100 | -0.316496 | [-0.354084, -0.279317] | 0 |
| F | T1 | DLinear - M0 | 48 | series_rmse_difference | 100 | -0.308720 | [-0.347018, -0.271164] | 0 |
| F | T1 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.083784 | [-0.101199, -0.066997] | 0 |
| F | T1 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.091560 | [-0.107701, -0.075176] | 0 |
| F | T4 | M2 - M0 | 48 | series_rmse_difference | 100 | -0.693522 | [-0.732287, -0.652084] | 0 |
| F | T4 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.243825 | [-0.261187, -0.226201] | 0 |
| F | T4 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.172686 | [-0.185980, -0.158624] | 0 |
| F | T6 | M2 - M0 | 48 | series_rmse_difference | 100 | -1.956865 | [-2.002080, -1.913294] | 0 |
| F | T6 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.274859 | [-0.295992, -0.254254] | 0 |
| F | T6 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.140555 | [-0.155935, -0.125551] | 0 |
| G | T8 | M1 - M0 | 48 | series_rmse_difference | 100 | 0.304138 | [0.255641, 0.351683] | 0 |
| G | T8 | DLinear - M0 | 48 | series_rmse_difference | 100 | 0.419137 | [0.357556, 0.483568] | 0 |
| G | T8 | M2 - M0 | 48 | series_rmse_difference | 100 | 0.129649 | [0.098860, 0.162346] | 0 |
| G | T8 | M3 - M0 | 48 | series_rmse_difference | 100 | 0.050861 | [0.031988, 0.070900] | 0 |
| H | T5 | M0 - SeasonalNaive | 48 | series_rmse_difference | 200 | 0.504185 | [0.485440, 0.522955] | 0 |
| H | T5 | M2 - SeasonalNaive | 48 | series_rmse_difference | 200 | -0.439803 | [-0.446931, -0.432420] | 0 |
| H | T5 | M3 - SeasonalNaive | 48 | series_rmse_difference | 200 | -0.458980 | [-0.465911, -0.451941] | 0 |
| A | T0 | M2 - M0 | 96 | relative_series_rmse | 200 | -0.262942 | [-0.271154, -0.254765] | 0 |
| A | T0 | M3 - M0 | 96 | relative_series_rmse | 200 | -0.266505 | [-0.275010, -0.257981] | 0 |
| B | T2 | M1 - M0 | 96 | series_rmse_difference | 100 | -0.067717 | [-0.157230, 0.017049] | 0.3768 |
| B | T2 | DLinear - M0 | 96 | series_rmse_difference | 100 | -0.082020 | [-0.175451, 0.008442] | 0.3056 |
| B | T2 | M2 - M0 | 96 | series_rmse_difference | 100 | -0.034649 | [-0.165792, 0.092456] | 0.81 |
| B | T2 | M3 - M0 | 96 | series_rmse_difference | 100 | -0.054647 | [-0.184780, 0.071738] | 0.81 |
| C | T3 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.240107 | [-0.254466, -0.225614] | 0 |
| C | T3 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.209349 | [-0.220444, -0.198268] | 0 |
| C | T4 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.536267 | [-0.558911, -0.513376] | 0 |
| C | T4 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.531983 | [-0.550918, -0.513430] | 0 |
| C | T6 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.275157 | [-0.292913, -0.257784] | 0 |
| C | T6 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.132245 | [-0.145144, -0.119420] | 0 |
| D | T0 | M3 - M3-constant-gate | 96 | series_rmse_difference | 200 | -0.000271 | [-0.001557, 0.000905] | 1 |
| D | T2 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.016089 | [-0.030288, -0.001404] | 0.5616 |
| D | T3 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | 0.021971 | [0.018435, 0.025643] | 0 |
| D | T4 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.029530 | [-0.041761, -0.016640] | 0 |
| D | T6 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.004920 | [-0.008091, -0.001703] | 0.0798 |
| D | T7 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.011537 | [-0.024142, 0.002179] | 1 |
| D | T8 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.092290 | [-0.124725, -0.061185] | 0 |
| D | T0 | M3 - M0 | 96 | series_rmse_difference | 200 | -0.452408 | [-0.472475, -0.433074] | 0 |
| D | T2 | M3 - M0 | 96 | series_rmse_difference | 100 | -0.054647 | [-0.185983, 0.068870] | 1 |
| D | T7 | M3 - M0 | 96 | series_rmse_difference | 100 | -1.351837 | [-1.473308, -1.231263] | 0 |
| D | T8 | M3 - M0 | 96 | series_rmse_difference | 100 | 0.047893 | [0.024348, 0.071813] | 0 |
| E | T7 | M1 - M0 | 96 | series_rmse_difference | 100 | -0.837222 | [-0.933374, -0.739076] | 0 |
| E | T7 | M2 - M0 | 96 | series_rmse_difference | 100 | -1.322779 | [-1.438482, -1.207944] | 0 |
| E | T7 | M3 - M0 | 96 | series_rmse_difference | 100 | -1.351837 | [-1.474792, -1.232712] | 0 |
| F | T1 | M1 - M0 | 96 | series_rmse_difference | 100 | -0.291342 | [-0.329791, -0.253020] | 0 |
| F | T1 | DLinear - M0 | 96 | series_rmse_difference | 100 | -0.277177 | [-0.317446, -0.237125] | 0 |
| F | T1 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.103214 | [-0.120364, -0.085408] | 0 |
| F | T1 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.117379 | [-0.135516, -0.099291] | 0 |
| F | T4 | M2 - M0 | 96 | series_rmse_difference | 100 | -1.501874 | [-1.552665, -1.451500] | 0 |
| F | T4 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.536267 | [-0.558962, -0.513428] | 0 |
| F | T4 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.531983 | [-0.550764, -0.513207] | 0 |
| F | T6 | M2 - M0 | 96 | series_rmse_difference | 100 | -1.942677 | [-1.984514, -1.902167] | 0 |
| F | T6 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.275157 | [-0.293139, -0.258147] | 0 |
| F | T6 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.132245 | [-0.145206, -0.119799] | 0 |
| G | T8 | M1 - M0 | 96 | series_rmse_difference | 100 | 0.281894 | [0.226666, 0.335227] | 0 |
| G | T8 | DLinear - M0 | 96 | series_rmse_difference | 100 | 0.436347 | [0.363536, 0.509456] | 0 |
| G | T8 | M2 - M0 | 96 | series_rmse_difference | 100 | 0.147490 | [0.102301, 0.193221] | 0 |
| G | T8 | M3 - M0 | 96 | series_rmse_difference | 100 | 0.047893 | [0.024215, 0.071895] | 0 |
| H | T5 | M0 - SeasonalNaive | 96 | series_rmse_difference | 200 | 0.514974 | [0.497476, 0.532489] | 0 |
| H | T5 | M2 - SeasonalNaive | 96 | series_rmse_difference | 200 | -0.435981 | [-0.441649, -0.430301] | 0 |
| H | T5 | M3 - SeasonalNaive | 96 | series_rmse_difference | 200 | -0.457186 | [-0.462508, -0.451938] | 0 |

## Detector Audit

| Mechanism | true label | origins | detector stable | detector change | change rate |
|---|---|---:|---:|---:|---:|
| continuing_trend | visible_change | 1700 | 1436 | 264 | 0.1553 |
| future_jump | stable | 1600 | 1157 | 443 | 0.2769 |
| future_jump | unseen_change | 100 | 86 | 14 | 0.1400 |
| random_walk | stable | 1700 | 1347 | 353 | 0.2076 |
| seasonal_change | stable | 795 | 638 | 157 | 0.1975 |
| seasonal_change | visible_change | 905 | 732 | 173 | 0.1912 |
| stable | stable | 3400 | 2765 | 635 | 0.1868 |
| stable_season | stable | 3400 | 2874 | 526 | 0.1547 |
| trend_break | stable | 795 | 643 | 152 | 0.1912 |
| trend_break | visible_change | 905 | 724 | 181 | 0.2000 |
| variance_shift | stable | 795 | 616 | 179 | 0.2252 |
| variance_shift | visible_change | 905 | 666 | 239 | 0.2641 |
| visible_level_shift | stable | 795 | 634 | 161 | 0.2025 |
| visible_level_shift | visible_change | 905 | 652 | 253 | 0.2796 |
