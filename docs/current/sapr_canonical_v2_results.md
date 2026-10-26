# SAPR CANONICAL_V2 Results

This report is generated solely from frozen `canonical_v2` task archives. It does not pool V2/V3 or real-data results.

## Decision

- `T0_safety_pass`: `True`
- `T2_leakage_pass`: `True`
- `T8_random_walk_pass`: `True`
- `patch_candidate_groups`: `['T4', 'T6']`
- `patch_claim_pass`: `True`
- `gate_open_evidence`: `True`
- `gate_close_evidence`: `False`
- `state_gate_claim_pass`: `False`

## Coverage

| Mechanism | true stable | true visible | true unseen | detector stable | detector change |
|---|---:|---:|---:|---:|---:|
| stable | 3400 | 0 | 0 | 2809 | 591 |
| visible_level_shift | 795 | 905 | 0 | 1305 | 395 |
| future_jump | 1600 | 0 | 100 | 1200 | 500 |
| continuing_trend | 0 | 1700 | 0 | 1467 | 233 |
| trend_break | 795 | 905 | 0 | 1400 | 300 |
| stable_season | 3400 | 0 | 0 | 2810 | 590 |
| seasonal_change | 795 | 905 | 0 | 1433 | 267 |
| variance_shift | 795 | 905 | 0 | 1295 | 405 |
| random_walk | 1700 | 0 | 0 | 1356 | 344 |
| gradual_drift | 795 | 905 | 0 | 1403 | 297 |
| weak_change | 795 | 905 | 0 | 1386 | 314 |

## Frozen Comparisons

Negative estimates favor the left model. Bootstrap units are independent test sequences after averaging matched seeds. Holm adjustment is within the frozen A-H family.

| family | group | comparison | H | metric | n | estimate | 95% CI | Holm p |
|---|---|---|---:|---|---:|---:|---|---:|
| A | T0 | M2 - M0 | 12 | relative_series_rmse | 200 | -0.248054 | [-0.258695, -0.237787] | 0 |
| A | T0 | M3 - M0 | 12 | relative_series_rmse | 200 | -0.250354 | [-0.260855, -0.240020] | 0 |
| B | T2 | M1 - M0 | 12 | series_rmse_difference | 100 | 0.202395 | [0.049443, 0.363721] | 0.0688 |
| B | T2 | DLinear - M0 | 12 | series_rmse_difference | 100 | 0.208879 | [0.046602, 0.381436] | 0.0896 |
| B | T2 | M2 - M0 | 12 | series_rmse_difference | 100 | 0.071197 | [0.017790, 0.126993] | 0.0684 |
| B | T2 | M3 - M0 | 12 | series_rmse_difference | 100 | 0.023528 | [-0.005846, 0.059967] | 0.2832 |
| C | T3 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.075828 | [-0.091730, -0.060233] | 0 |
| C | T3 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.082883 | [-0.099080, -0.067007] | 0 |
| C | T4 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.060441 | [-0.080805, -0.040255] | 0 |
| C | T4 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.057576 | [-0.079265, -0.036581] | 0 |
| C | T6 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.194697 | [-0.221475, -0.167764] | 0 |
| C | T6 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.113288 | [-0.133478, -0.093461] | 0 |
| D | T0 | M3 - M3-constant-gate | 12 | series_rmse_difference | 200 | -0.004732 | [-0.006706, -0.002782] | 0 |
| D | T2 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.014088 | [-0.055310, 0.030234] | 1 |
| D | T3 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.034205 | [-0.039767, -0.028714] | 0 |
| D | T4 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.021424 | [-0.031856, -0.010687] | 0 |
| D | T6 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.016122 | [-0.021804, -0.010547] | 0 |
| D | T7 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.029348 | [-0.045550, -0.013977] | 0.0024 |
| D | T8 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.035355 | [-0.049826, -0.020065] | 0 |
| D | T0 | M3 - M0 | 12 | series_rmse_difference | 200 | -0.410617 | [-0.431801, -0.389929] | 0 |
| D | T2 | M3 - M0 | 12 | series_rmse_difference | 100 | 0.023528 | [-0.005485, 0.060202] | 0.7416 |
| D | T7 | M3 - M0 | 12 | series_rmse_difference | 100 | -1.149955 | [-1.274054, -1.028520] | 0 |
| D | T8 | M3 - M0 | 12 | series_rmse_difference | 100 | 0.034234 | [0.020936, 0.049120] | 0 |
| E | T7 | M1 - M0 | 12 | series_rmse_difference | 100 | -0.666024 | [-0.760877, -0.568615] | 0 |
| E | T7 | M2 - M0 | 12 | series_rmse_difference | 100 | -1.128806 | [-1.249633, -1.009754] | 0 |
| E | T7 | M3 - M0 | 12 | series_rmse_difference | 100 | -1.149955 | [-1.276580, -1.028710] | 0 |
| F | T1 | M1 - M0 | 12 | series_rmse_difference | 100 | -0.213768 | [-0.247091, -0.181545] | 0 |
| F | T1 | DLinear - M0 | 12 | series_rmse_difference | 100 | -0.224892 | [-0.256900, -0.193332] | 0 |
| F | T1 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.122862 | [-0.149997, -0.096605] | 0 |
| F | T1 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.111738 | [-0.135445, -0.087991] | 0 |
| F | T4 | M2 - M0 | 12 | series_rmse_difference | 100 | -0.260296 | [-0.292025, -0.228126] | 0 |
| F | T4 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.060441 | [-0.080616, -0.040791] | 0 |
| F | T4 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.057576 | [-0.078876, -0.036289] | 0 |
| F | T6 | M2 - M0 | 12 | series_rmse_difference | 100 | -1.060447 | [-1.119585, -1.000375] | 0 |
| F | T6 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.194697 | [-0.221413, -0.168017] | 0 |
| F | T6 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.113288 | [-0.133875, -0.093678] | 0 |
| G | T8 | M1 - M0 | 12 | series_rmse_difference | 100 | 0.246898 | [0.202766, 0.291074] | 0 |
| G | T8 | DLinear - M0 | 12 | series_rmse_difference | 100 | 0.334251 | [0.287297, 0.381031] | 0 |
| G | T8 | M2 - M0 | 12 | series_rmse_difference | 100 | 0.074912 | [0.053729, 0.100047] | 0 |
| G | T8 | M3 - M0 | 12 | series_rmse_difference | 100 | 0.034234 | [0.020577, 0.049422] | 0 |
| H | T5 | M0 - SeasonalNaive | 12 | series_rmse_difference | 200 | 0.566763 | [0.529096, 0.603365] | 0 |
| H | T5 | M2 - SeasonalNaive | 12 | series_rmse_difference | 200 | -0.453712 | [-0.467025, -0.440568] | 0 |
| H | T5 | M3 - SeasonalNaive | 12 | series_rmse_difference | 200 | -0.469300 | [-0.482522, -0.456109] | 0 |
| A | T0 | M2 - M0 | 24 | relative_series_rmse | 200 | -0.261275 | [-0.270558, -0.252005] | 0 |
| A | T0 | M3 - M0 | 24 | relative_series_rmse | 200 | -0.264525 | [-0.273845, -0.255168] | 0 |
| B | T2 | M1 - M0 | 24 | series_rmse_difference | 100 | 0.279222 | [0.133470, 0.427110] | 0 |
| B | T2 | DLinear - M0 | 24 | series_rmse_difference | 100 | 0.250060 | [0.058995, 0.445296] | 0.0896 |
| B | T2 | M2 - M0 | 24 | series_rmse_difference | 100 | 0.096032 | [0.038684, 0.155713] | 0.006 |
| B | T2 | M3 - M0 | 24 | series_rmse_difference | 100 | 0.032548 | [0.002421, 0.073305] | 0.131 |
| C | T3 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.085190 | [-0.101175, -0.069467] | 0 |
| C | T3 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.128925 | [-0.145707, -0.111792] | 0 |
| C | T4 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.131112 | [-0.152947, -0.108912] | 0 |
| C | T4 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.301948 | [-0.327635, -0.276087] | 0 |
| C | T6 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.312052 | [-0.335625, -0.288928] | 0 |
| C | T6 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.194933 | [-0.213939, -0.176614] | 0 |
| D | T0 | M3 - M3-constant-gate | 24 | series_rmse_difference | 200 | -0.006210 | [-0.008011, -0.004496] | 0 |
| D | T2 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.026732 | [-0.060255, 0.007243] | 0.7416 |
| D | T3 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.041187 | [-0.046774, -0.035878] | 0 |
| D | T4 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.034280 | [-0.043903, -0.024458] | 0 |
| D | T6 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.027296 | [-0.031925, -0.022666] | 0 |
| D | T7 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.027672 | [-0.042378, -0.015078] | 0 |
| D | T8 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.031885 | [-0.044657, -0.018735] | 0 |
| D | T0 | M3 - M0 | 24 | series_rmse_difference | 200 | -0.445117 | [-0.466520, -0.424274] | 0 |
| D | T2 | M3 - M0 | 24 | series_rmse_difference | 100 | 0.032548 | [0.002542, 0.072926] | 0.2304 |
| D | T7 | M3 - M0 | 24 | series_rmse_difference | 100 | -1.273881 | [-1.385194, -1.162415] | 0 |
| D | T8 | M3 - M0 | 24 | series_rmse_difference | 100 | 0.023505 | [0.011333, 0.037001] | 0.0024 |
| E | T7 | M1 - M0 | 24 | series_rmse_difference | 100 | -0.720958 | [-0.810654, -0.632548] | 0 |
| E | T7 | M2 - M0 | 24 | series_rmse_difference | 100 | -1.250592 | [-1.358618, -1.143624] | 0 |
| E | T7 | M3 - M0 | 24 | series_rmse_difference | 100 | -1.273881 | [-1.385242, -1.164636] | 0 |
| F | T1 | M1 - M0 | 24 | series_rmse_difference | 100 | -0.239138 | [-0.273440, -0.206160] | 0 |
| F | T1 | DLinear - M0 | 24 | series_rmse_difference | 100 | -0.265813 | [-0.301909, -0.230333] | 0 |
| F | T1 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.126698 | [-0.149013, -0.104149] | 0 |
| F | T1 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.100024 | [-0.118887, -0.081519] | 0 |
| F | T4 | M2 - M0 | 24 | series_rmse_difference | 100 | -0.377408 | [-0.414846, -0.338707] | 0 |
| F | T4 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.131112 | [-0.153246, -0.109484] | 0 |
| F | T4 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.301948 | [-0.327991, -0.275897] | 0 |
| F | T6 | M2 - M0 | 24 | series_rmse_difference | 100 | -1.010718 | [-1.052741, -0.969073] | 0 |
| F | T6 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.312052 | [-0.335615, -0.289325] | 0 |
| F | T6 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.194933 | [-0.213821, -0.176682] | 0 |
| G | T8 | M1 - M0 | 24 | series_rmse_difference | 100 | 0.188727 | [0.146010, 0.233524] | 0 |
| G | T8 | DLinear - M0 | 24 | series_rmse_difference | 100 | 0.322264 | [0.264529, 0.381085] | 0 |
| G | T8 | M2 - M0 | 24 | series_rmse_difference | 100 | 0.063037 | [0.041903, 0.085284] | 0 |
| G | T8 | M3 - M0 | 24 | series_rmse_difference | 100 | 0.023505 | [0.011591, 0.037003] | 0 |
| H | T5 | M0 - SeasonalNaive | 24 | series_rmse_difference | 200 | 0.627552 | [0.593946, 0.660841] | 0 |
| H | T5 | M2 - SeasonalNaive | 24 | series_rmse_difference | 200 | -0.453982 | [-0.463639, -0.444156] | 0 |
| H | T5 | M3 - SeasonalNaive | 24 | series_rmse_difference | 200 | -0.469616 | [-0.479115, -0.460101] | 0 |
| A | T0 | M2 - M0 | 48 | relative_series_rmse | 200 | -0.269169 | [-0.277881, -0.260078] | 0 |
| A | T0 | M3 - M0 | 48 | relative_series_rmse | 200 | -0.273287 | [-0.282132, -0.264208] | 0 |
| B | T2 | M1 - M0 | 48 | series_rmse_difference | 100 | 0.250538 | [0.093638, 0.409481] | 0.0144 |
| B | T2 | DLinear - M0 | 48 | series_rmse_difference | 100 | 0.332026 | [0.132813, 0.542564] | 0.0176 |
| B | T2 | M2 - M0 | 48 | series_rmse_difference | 100 | 0.108389 | [0.031099, 0.191587] | 0.056 |
| B | T2 | M3 - M0 | 48 | series_rmse_difference | 100 | 0.035156 | [0.003914, 0.069246] | 0.131 |
| C | T3 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.134889 | [-0.153725, -0.115718] | 0 |
| C | T3 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.118589 | [-0.135979, -0.101302] | 0 |
| C | T4 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.377156 | [-0.404171, -0.350307] | 0 |
| C | T4 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.330998 | [-0.355901, -0.306233] | 0 |
| C | T6 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.403970 | [-0.426513, -0.381583] | 0 |
| C | T6 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.239288 | [-0.258191, -0.220353] | 0 |
| D | T0 | M3 - M3-constant-gate | 48 | series_rmse_difference | 200 | -0.007344 | [-0.009011, -0.005760] | 0 |
| D | T2 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.019129 | [-0.061570, 0.025589] | 1 |
| D | T3 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.045268 | [-0.050557, -0.040250] | 0 |
| D | T4 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.065762 | [-0.076485, -0.055388] | 0 |
| D | T6 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.032843 | [-0.037564, -0.028312] | 0 |
| D | T7 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.030531 | [-0.045703, -0.018141] | 0 |
| D | T8 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.034587 | [-0.047278, -0.022252] | 0 |
| D | T0 | M3 - M0 | 48 | series_rmse_difference | 200 | -0.466492 | [-0.487197, -0.446087] | 0 |
| D | T2 | M3 - M0 | 48 | series_rmse_difference | 100 | 0.035156 | [0.003223, 0.071317] | 0.2304 |
| D | T7 | M3 - M0 | 48 | series_rmse_difference | 100 | -1.325799 | [-1.433925, -1.218803] | 0 |
| D | T8 | M3 - M0 | 48 | series_rmse_difference | 100 | 0.016469 | [0.004776, 0.028741] | 0.044 |
| E | T7 | M1 - M0 | 48 | series_rmse_difference | 100 | -0.792800 | [-0.878321, -0.707884] | 0 |
| E | T7 | M2 - M0 | 48 | series_rmse_difference | 100 | -1.297557 | [-1.406573, -1.192155] | 0 |
| E | T7 | M3 - M0 | 48 | series_rmse_difference | 100 | -1.325799 | [-1.433122, -1.219492] | 0 |
| F | T1 | M1 - M0 | 48 | series_rmse_difference | 100 | -0.274805 | [-0.307482, -0.243951] | 0 |
| F | T1 | DLinear - M0 | 48 | series_rmse_difference | 100 | -0.275273 | [-0.308622, -0.242994] | 0 |
| F | T1 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.101808 | [-0.119434, -0.084804] | 0 |
| F | T1 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.101340 | [-0.117290, -0.085385] | 0 |
| F | T4 | M2 - M0 | 48 | series_rmse_difference | 100 | -0.722678 | [-0.769376, -0.676909] | 0 |
| F | T4 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.377156 | [-0.404307, -0.349717] | 0 |
| F | T4 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.330998 | [-0.355960, -0.306573] | 0 |
| F | T6 | M2 - M0 | 48 | series_rmse_difference | 100 | -1.933405 | [-1.976419, -1.889670] | 0 |
| F | T6 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.403970 | [-0.426864, -0.381116] | 0 |
| F | T6 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.239288 | [-0.257874, -0.220841] | 0 |
| G | T8 | M1 - M0 | 48 | series_rmse_difference | 100 | 0.153270 | [0.113831, 0.192513] | 0 |
| G | T8 | DLinear - M0 | 48 | series_rmse_difference | 100 | 0.278807 | [0.228173, 0.329485] | 0 |
| G | T8 | M2 - M0 | 48 | series_rmse_difference | 100 | 0.064311 | [0.042389, 0.086702] | 0 |
| G | T8 | M3 - M0 | 48 | series_rmse_difference | 100 | 0.016469 | [0.004455, 0.028934] | 0.0116 |
| H | T5 | M0 - SeasonalNaive | 48 | series_rmse_difference | 200 | 0.501536 | [0.483429, 0.519961] | 0 |
| H | T5 | M2 - SeasonalNaive | 48 | series_rmse_difference | 200 | -0.451789 | [-0.458666, -0.445008] | 0 |
| H | T5 | M3 - SeasonalNaive | 48 | series_rmse_difference | 200 | -0.468827 | [-0.475617, -0.462153] | 0 |
| A | T0 | M2 - M0 | 96 | relative_series_rmse | 200 | -0.271861 | [-0.280279, -0.263505] | 0 |
| A | T0 | M3 - M0 | 96 | relative_series_rmse | 200 | -0.275590 | [-0.283834, -0.267230] | 0 |
| B | T2 | M1 - M0 | 96 | series_rmse_difference | 100 | 0.345548 | [0.144566, 0.553147] | 0.013 |
| B | T2 | DLinear - M0 | 96 | series_rmse_difference | 100 | 0.418789 | [0.181825, 0.662645] | 0.006 |
| B | T2 | M2 - M0 | 96 | series_rmse_difference | 100 | 0.141516 | [0.013316, 0.277705] | 0.131 |
| B | T2 | M3 - M0 | 96 | series_rmse_difference | 100 | 0.017406 | [-0.030557, 0.069853] | 0.5108 |
| C | T3 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.341813 | [-0.362103, -0.321958] | 0 |
| C | T3 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.328805 | [-0.347396, -0.310160] | 0 |
| C | T4 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.949991 | [-0.981126, -0.918311] | 0 |
| C | T4 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.902069 | [-0.928726, -0.875117] | 0 |
| C | T6 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.399565 | [-0.419461, -0.379585] | 0 |
| C | T6 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.263852 | [-0.282556, -0.245184] | 0 |
| D | T0 | M3 - M3-constant-gate | 96 | series_rmse_difference | 200 | -0.006657 | [-0.008240, -0.005197] | 0 |
| D | T2 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.023981 | [-0.084534, 0.038836] | 1 |
| D | T3 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.043330 | [-0.047895, -0.038773] | 0 |
| D | T4 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.169292 | [-0.181940, -0.156889] | 0 |
| D | T6 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.035296 | [-0.039570, -0.031157] | 0 |
| D | T7 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.031858 | [-0.046962, -0.019678] | 0 |
| D | T8 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.041772 | [-0.058314, -0.025324] | 0 |
| D | T0 | M3 - M0 | 96 | series_rmse_difference | 200 | -0.472905 | [-0.492816, -0.453307] | 0 |
| D | T2 | M3 - M0 | 96 | series_rmse_difference | 100 | 0.017406 | [-0.029810, 0.068918] | 1 |
| D | T7 | M3 - M0 | 96 | series_rmse_difference | 100 | -1.356210 | [-1.462998, -1.251898] | 0 |
| D | T8 | M3 - M0 | 96 | series_rmse_difference | 100 | 0.019676 | [0.004883, 0.034447] | 0.0702 |
| E | T7 | M1 - M0 | 96 | series_rmse_difference | 100 | -0.778521 | [-0.862129, -0.696540] | 0 |
| E | T7 | M2 - M0 | 96 | series_rmse_difference | 100 | -1.327404 | [-1.435888, -1.221054] | 0 |
| E | T7 | M3 - M0 | 96 | series_rmse_difference | 100 | -1.356210 | [-1.464249, -1.249814] | 0 |
| F | T1 | M1 - M0 | 96 | series_rmse_difference | 100 | -0.265094 | [-0.296516, -0.234443] | 0 |
| F | T1 | DLinear - M0 | 96 | series_rmse_difference | 100 | -0.250873 | [-0.282072, -0.220259] | 0 |
| F | T1 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.105875 | [-0.123880, -0.088355] | 0 |
| F | T1 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.120096 | [-0.136895, -0.103878] | 0 |
| F | T4 | M2 - M0 | 96 | series_rmse_difference | 100 | -1.610733 | [-1.664308, -1.557819] | 0 |
| F | T4 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.949991 | [-0.981430, -0.918028] | 0 |
| F | T4 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.902069 | [-0.928959, -0.875283] | 0 |
| F | T6 | M2 - M0 | 96 | series_rmse_difference | 100 | -1.933387 | [-1.971669, -1.894841] | 0 |
| F | T6 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.399565 | [-0.419439, -0.378958] | 0 |
| F | T6 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.263852 | [-0.282808, -0.244887] | 0 |
| G | T8 | M1 - M0 | 96 | series_rmse_difference | 100 | 0.144451 | [0.097035, 0.189709] | 0 |
| G | T8 | DLinear - M0 | 96 | series_rmse_difference | 100 | 0.248482 | [0.194507, 0.303685] | 0 |
| G | T8 | M2 - M0 | 96 | series_rmse_difference | 100 | 0.084275 | [0.057452, 0.111581] | 0 |
| G | T8 | M3 - M0 | 96 | series_rmse_difference | 100 | 0.019676 | [0.004426, 0.034431] | 0.0126 |
| H | T5 | M0 - SeasonalNaive | 96 | series_rmse_difference | 200 | 0.508141 | [0.491015, 0.525554] | 0 |
| H | T5 | M2 - SeasonalNaive | 96 | series_rmse_difference | 200 | -0.445661 | [-0.450750, -0.440645] | 0 |
| H | T5 | M3 - SeasonalNaive | 96 | series_rmse_difference | 200 | -0.465206 | [-0.469958, -0.460429] | 0 |

## Detector Audit

| Mechanism | true label | origins | detector stable | detector change | change rate |
|---|---|---:|---:|---:|---:|
| continuing_trend | visible_change | 1700 | 1467 | 233 | 0.1371 |
| future_jump | stable | 1600 | 1118 | 482 | 0.3013 |
| future_jump | unseen_change | 100 | 82 | 18 | 0.1800 |
| gradual_drift | stable | 795 | 650 | 145 | 0.1824 |
| gradual_drift | visible_change | 905 | 753 | 152 | 0.1680 |
| random_walk | stable | 1700 | 1356 | 344 | 0.2024 |
| seasonal_change | stable | 795 | 665 | 130 | 0.1635 |
| seasonal_change | visible_change | 905 | 768 | 137 | 0.1514 |
| stable | stable | 3400 | 2809 | 591 | 0.1738 |
| stable_season | stable | 3400 | 2810 | 590 | 0.1735 |
| trend_break | stable | 795 | 640 | 155 | 0.1950 |
| trend_break | visible_change | 905 | 760 | 145 | 0.1602 |
| variance_shift | stable | 795 | 640 | 155 | 0.1950 |
| variance_shift | visible_change | 905 | 655 | 250 | 0.2762 |
| visible_level_shift | stable | 795 | 634 | 161 | 0.2025 |
| visible_level_shift | visible_change | 905 | 671 | 234 | 0.2586 |
| weak_change | stable | 795 | 665 | 130 | 0.1635 |
| weak_change | visible_change | 905 | 721 | 184 | 0.2033 |
