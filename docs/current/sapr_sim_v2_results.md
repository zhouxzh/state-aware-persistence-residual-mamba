# SAPR SIM_V2 Results

This report is generated solely from frozen `sim_v2` task archives. It does not pool V2/V3 or real-data results.

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
| stable | 3400 | 0 | 0 | 2681 | 719 |
| visible_level_shift | 795 | 905 | 0 | 1318 | 382 |
| future_jump | 1600 | 0 | 100 | 1209 | 491 |
| continuing_trend | 0 | 1700 | 0 | 1406 | 294 |
| trend_break | 795 | 905 | 0 | 1366 | 334 |
| stable_season | 3400 | 0 | 0 | 2854 | 546 |
| seasonal_change | 795 | 905 | 0 | 1368 | 332 |
| variance_shift | 795 | 905 | 0 | 1285 | 415 |
| random_walk | 1700 | 0 | 0 | 1331 | 369 |

## Frozen Comparisons

Negative estimates favor the left model. Bootstrap units are independent test sequences after averaging matched seeds. Holm adjustment is within the frozen A-H family.

| family | group | comparison | H | metric | n | estimate | 95% CI | Holm p |
|---|---|---|---:|---|---:|---:|---|---:|
| A | T0 | M2 - M0 | 12 | relative_series_rmse | 200 | -0.257212 | [-0.268301, -0.245728] | 0 |
| A | T0 | M3 - M0 | 12 | relative_series_rmse | 200 | -0.258828 | [-0.270060, -0.247262] | 0 |
| B | T2 | M1 - M0 | 12 | series_rmse_difference | 100 | -0.296822 | [-0.398505, -0.204061] | 0 |
| B | T2 | DLinear - M0 | 12 | series_rmse_difference | 100 | -0.328454 | [-0.430403, -0.234004] | 0 |
| B | T2 | M2 - M0 | 12 | series_rmse_difference | 100 | -0.432560 | [-0.538580, -0.331708] | 0 |
| B | T2 | M3 - M0 | 12 | series_rmse_difference | 100 | -0.443867 | [-0.551134, -0.342256] | 0 |
| C | T3 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.069992 | [-0.080671, -0.059149] | 0 |
| C | T3 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.088767 | [-0.099299, -0.077674] | 0 |
| C | T4 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.082958 | [-0.106112, -0.059109] | 0 |
| C | T4 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.115591 | [-0.137077, -0.093816] | 0 |
| C | T6 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.152090 | [-0.172724, -0.131033] | 0 |
| C | T6 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.140647 | [-0.157546, -0.123698] | 0 |
| D | T0 | M3 - M3-constant-gate | 12 | series_rmse_difference | 200 | -0.000538 | [-0.002791, 0.001705] | 1 |
| D | T2 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.012437 | [-0.025805, -0.000099] | 0.6318 |
| D | T3 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.024579 | [-0.030486, -0.019010] | 0 |
| D | T4 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.028240 | [-0.041442, -0.015647] | 0 |
| D | T6 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.009174 | [-0.014916, -0.003689] | 0.0128 |
| D | T7 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.003840 | [-0.020251, 0.012002] | 1 |
| D | T8 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.040034 | [-0.060701, -0.019636] | 0.004 |
| D | T0 | M3 - M0 | 12 | series_rmse_difference | 200 | -0.429765 | [-0.452320, -0.406802] | 0 |
| D | T2 | M3 - M0 | 12 | series_rmse_difference | 100 | -0.443867 | [-0.553517, -0.344589] | 0 |
| D | T7 | M3 - M0 | 12 | series_rmse_difference | 100 | -1.271686 | [-1.395468, -1.151882] | 0 |
| D | T8 | M3 - M0 | 12 | series_rmse_difference | 100 | 0.086273 | [0.063652, 0.109549] | 0 |
| E | T7 | M1 - M0 | 12 | series_rmse_difference | 100 | -0.749854 | [-0.858634, -0.647275] | 0 |
| E | T7 | M2 - M0 | 12 | series_rmse_difference | 100 | -1.268625 | [-1.384071, -1.152705] | 0 |
| E | T7 | M3 - M0 | 12 | series_rmse_difference | 100 | -1.271686 | [-1.395282, -1.153149] | 0 |
| F | T1 | M1 - M0 | 12 | series_rmse_difference | 100 | -0.252273 | [-0.289697, -0.215564] | 0 |
| F | T1 | DLinear - M0 | 12 | series_rmse_difference | 100 | -0.265282 | [-0.305210, -0.225920] | 0 |
| F | T1 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.104805 | [-0.129003, -0.081009] | 0 |
| F | T1 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.091795 | [-0.111345, -0.071987] | 0 |
| F | T4 | M2 - M0 | 12 | series_rmse_difference | 100 | -0.297059 | [-0.332550, -0.261598] | 0 |
| F | T4 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.082958 | [-0.106382, -0.058472] | 0 |
| F | T4 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.115591 | [-0.137318, -0.093655] | 0 |
| F | T6 | M2 - M0 | 12 | series_rmse_difference | 100 | -1.093025 | [-1.149630, -1.037131] | 0 |
| F | T6 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.152090 | [-0.173334, -0.131506] | 0 |
| F | T6 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.140647 | [-0.157251, -0.124052] | 0 |
| G | T8 | M1 - M0 | 12 | series_rmse_difference | 100 | 0.427114 | [0.370324, 0.483729] | 0 |
| G | T8 | DLinear - M0 | 12 | series_rmse_difference | 100 | 0.522380 | [0.460538, 0.583214] | 0 |
| G | T8 | M2 - M0 | 12 | series_rmse_difference | 100 | 0.152507 | [0.123347, 0.181240] | 0 |
| G | T8 | M3 - M0 | 12 | series_rmse_difference | 100 | 0.086273 | [0.063484, 0.109146] | 0 |
| H | T5 | M0 - SeasonalNaive | 12 | series_rmse_difference | 200 | 0.542395 | [0.505225, 0.580119] | 0 |
| H | T5 | M2 - SeasonalNaive | 12 | series_rmse_difference | 200 | -0.467410 | [-0.482230, -0.453004] | 0 |
| H | T5 | M3 - SeasonalNaive | 12 | series_rmse_difference | 200 | -0.472573 | [-0.487035, -0.458489] | 0 |
| A | T0 | M2 - M0 | 24 | relative_series_rmse | 200 | -0.269847 | [-0.279881, -0.259880] | 0 |
| A | T0 | M3 - M0 | 24 | relative_series_rmse | 200 | -0.271991 | [-0.281994, -0.261934] | 0 |
| B | T2 | M1 - M0 | 24 | series_rmse_difference | 100 | -0.321277 | [-0.420550, -0.228149] | 0 |
| B | T2 | DLinear - M0 | 24 | series_rmse_difference | 100 | -0.354385 | [-0.451043, -0.259603] | 0 |
| B | T2 | M2 - M0 | 24 | series_rmse_difference | 100 | -0.473824 | [-0.583475, -0.372622] | 0 |
| B | T2 | M3 - M0 | 24 | series_rmse_difference | 100 | -0.480122 | [-0.590898, -0.377865] | 0 |
| C | T3 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.079171 | [-0.090332, -0.068412] | 0 |
| C | T3 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.129903 | [-0.141991, -0.117881] | 0 |
| C | T4 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.120736 | [-0.141760, -0.099996] | 0 |
| C | T4 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.249962 | [-0.269464, -0.230947] | 0 |
| C | T6 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.236822 | [-0.256392, -0.216854] | 0 |
| C | T6 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.131518 | [-0.145499, -0.117270] | 0 |
| D | T0 | M3 - M3-constant-gate | 24 | series_rmse_difference | 200 | -0.000850 | [-0.002686, 0.000913] | 1 |
| D | T2 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.005466 | [-0.015906, 0.004303] | 1 |
| D | T3 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.025440 | [-0.030282, -0.020652] | 0 |
| D | T4 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.021774 | [-0.034250, -0.010015] | 0.004 |
| D | T6 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.004840 | [-0.009052, -0.000729] | 0.294 |
| D | T7 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.001349 | [-0.014823, 0.011233] | 1 |
| D | T8 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.041303 | [-0.063484, -0.019040] | 0.0068 |
| D | T0 | M3 - M0 | 24 | series_rmse_difference | 200 | -0.463771 | [-0.486575, -0.440579] | 0 |
| D | T2 | M3 - M0 | 24 | series_rmse_difference | 100 | -0.480122 | [-0.590355, -0.376916] | 0 |
| D | T7 | M3 - M0 | 24 | series_rmse_difference | 100 | -1.317175 | [-1.434184, -1.203881] | 0 |
| D | T8 | M3 - M0 | 24 | series_rmse_difference | 100 | 0.072748 | [0.049262, 0.095739] | 0 |
| E | T7 | M1 - M0 | 24 | series_rmse_difference | 100 | -0.813909 | [-0.913487, -0.713060] | 0 |
| E | T7 | M2 - M0 | 24 | series_rmse_difference | 100 | -1.311180 | [-1.421637, -1.201270] | 0 |
| E | T7 | M3 - M0 | 24 | series_rmse_difference | 100 | -1.317175 | [-1.433716, -1.204592] | 0 |
| F | T1 | M1 - M0 | 24 | series_rmse_difference | 100 | -0.287914 | [-0.324311, -0.251770] | 0 |
| F | T1 | DLinear - M0 | 24 | series_rmse_difference | 100 | -0.305598 | [-0.343485, -0.267295] | 0 |
| F | T1 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.103363 | [-0.123628, -0.083627] | 0 |
| F | T1 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.085679 | [-0.102106, -0.069084] | 0 |
| F | T4 | M2 - M0 | 24 | series_rmse_difference | 100 | -0.420440 | [-0.462589, -0.378145] | 0 |
| F | T4 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.120736 | [-0.141076, -0.099986] | 0 |
| F | T4 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.249962 | [-0.268819, -0.230709] | 0 |
| F | T6 | M2 - M0 | 24 | series_rmse_difference | 100 | -1.025865 | [-1.062938, -0.989153] | 0 |
| F | T6 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.236822 | [-0.256653, -0.217318] | 0 |
| F | T6 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.131518 | [-0.145893, -0.117345] | 0 |
| G | T8 | M1 - M0 | 24 | series_rmse_difference | 100 | 0.358139 | [0.298300, 0.415525] | 0 |
| G | T8 | DLinear - M0 | 24 | series_rmse_difference | 100 | 0.486989 | [0.418074, 0.557378] | 0 |
| G | T8 | M2 - M0 | 24 | series_rmse_difference | 100 | 0.142977 | [0.111175, 0.174784] | 0 |
| G | T8 | M3 - M0 | 24 | series_rmse_difference | 100 | 0.072748 | [0.049720, 0.095539] | 0 |
| H | T5 | M0 - SeasonalNaive | 24 | series_rmse_difference | 200 | 0.624117 | [0.587908, 0.660078] | 0 |
| H | T5 | M2 - SeasonalNaive | 24 | series_rmse_difference | 200 | -0.458077 | [-0.467767, -0.448177] | 0 |
| H | T5 | M3 - SeasonalNaive | 24 | series_rmse_difference | 200 | -0.470359 | [-0.480201, -0.460696] | 0 |
| A | T0 | M2 - M0 | 48 | relative_series_rmse | 200 | -0.278390 | [-0.288187, -0.268442] | 0 |
| A | T0 | M3 - M0 | 48 | relative_series_rmse | 200 | -0.279417 | [-0.289082, -0.269554] | 0 |
| B | T2 | M1 - M0 | 48 | series_rmse_difference | 100 | -0.337310 | [-0.430338, -0.247487] | 0 |
| B | T2 | DLinear - M0 | 48 | series_rmse_difference | 100 | -0.353745 | [-0.453984, -0.260511] | 0 |
| B | T2 | M2 - M0 | 48 | series_rmse_difference | 100 | -0.484066 | [-0.592292, -0.384446] | 0 |
| B | T2 | M3 - M0 | 48 | series_rmse_difference | 100 | -0.485904 | [-0.589536, -0.385764] | 0 |
| C | T3 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.089771 | [-0.100946, -0.078729] | 0 |
| C | T3 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.189521 | [-0.202932, -0.175967] | 0 |
| C | T4 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.244887 | [-0.267635, -0.222663] | 0 |
| C | T4 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.524921 | [-0.549698, -0.500798] | 0 |
| C | T6 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.298612 | [-0.319593, -0.276992] | 0 |
| C | T6 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.131444 | [-0.142562, -0.120567] | 0 |
| D | T0 | M3 - M3-constant-gate | 48 | series_rmse_difference | 200 | 0.000376 | [-0.001141, 0.001837] | 1 |
| D | T2 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.001682 | [-0.009412, 0.005327] | 1 |
| D | T3 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.029075 | [-0.033995, -0.024554] | 0 |
| D | T4 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.022354 | [-0.036229, -0.008997] | 0.0128 |
| D | T6 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.011257 | [-0.015722, -0.006617] | 0 |
| D | T7 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.003656 | [-0.014505, 0.006079] | 1 |
| D | T8 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.056294 | [-0.080849, -0.032135] | 0 |
| D | T0 | M3 - M0 | 48 | series_rmse_difference | 200 | -0.483222 | [-0.506938, -0.460718] | 0 |
| D | T2 | M3 - M0 | 48 | series_rmse_difference | 100 | -0.485904 | [-0.592278, -0.387685] | 0 |
| D | T7 | M3 - M0 | 48 | series_rmse_difference | 100 | -1.376763 | [-1.489435, -1.266270] | 0 |
| D | T8 | M3 - M0 | 48 | series_rmse_difference | 100 | 0.058217 | [0.030998, 0.083734] | 0.004 |
| E | T7 | M1 - M0 | 48 | series_rmse_difference | 100 | -0.923515 | [-1.022447, -0.829306] | 0 |
| E | T7 | M2 - M0 | 48 | series_rmse_difference | 100 | -1.368994 | [-1.475791, -1.257184] | 0 |
| E | T7 | M3 - M0 | 48 | series_rmse_difference | 100 | -1.376763 | [-1.490664, -1.265383] | 0 |
| F | T1 | M1 - M0 | 48 | series_rmse_difference | 100 | -0.315846 | [-0.353247, -0.278471] | 0 |
| F | T1 | DLinear - M0 | 48 | series_rmse_difference | 100 | -0.329922 | [-0.368505, -0.292594] | 0 |
| F | T1 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.088761 | [-0.104587, -0.072312] | 0 |
| F | T1 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.074684 | [-0.088263, -0.061216] | 0 |
| F | T4 | M2 - M0 | 48 | series_rmse_difference | 100 | -0.757737 | [-0.810317, -0.705665] | 0 |
| F | T4 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.244887 | [-0.267971, -0.222638] | 0 |
| F | T4 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.524921 | [-0.549449, -0.500730] | 0 |
| F | T6 | M2 - M0 | 48 | series_rmse_difference | 100 | -1.949850 | [-1.995726, -1.905696] | 0 |
| F | T6 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.298612 | [-0.319885, -0.277570] | 0 |
| F | T6 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.131444 | [-0.142788, -0.120163] | 0 |
| G | T8 | M1 - M0 | 48 | series_rmse_difference | 100 | 0.280259 | [0.220348, 0.338872] | 0 |
| G | T8 | DLinear - M0 | 48 | series_rmse_difference | 100 | 0.397997 | [0.326943, 0.467277] | 0 |
| G | T8 | M2 - M0 | 48 | series_rmse_difference | 100 | 0.144877 | [0.106395, 0.182222] | 0 |
| G | T8 | M3 - M0 | 48 | series_rmse_difference | 100 | 0.058217 | [0.031816, 0.083801] | 0 |
| H | T5 | M0 - SeasonalNaive | 48 | series_rmse_difference | 200 | 0.509631 | [0.491150, 0.527927] | 0 |
| H | T5 | M2 - SeasonalNaive | 48 | series_rmse_difference | 200 | -0.445244 | [-0.451963, -0.438435] | 0 |
| H | T5 | M3 - SeasonalNaive | 48 | series_rmse_difference | 200 | -0.458404 | [-0.465147, -0.451940] | 0 |
| A | T0 | M2 - M0 | 96 | relative_series_rmse | 200 | -0.278771 | [-0.288274, -0.269541] | 0 |
| A | T0 | M3 - M0 | 96 | relative_series_rmse | 200 | -0.279506 | [-0.288699, -0.270216] | 0 |
| B | T2 | M1 - M0 | 96 | series_rmse_difference | 100 | 0.009247 | [-0.108978, 0.126378] | 1 |
| B | T2 | DLinear - M0 | 96 | series_rmse_difference | 100 | 0.007914 | [-0.122406, 0.138748] | 1 |
| B | T2 | M2 - M0 | 96 | series_rmse_difference | 100 | 0.007723 | [-0.149604, 0.162917] | 1 |
| B | T2 | M3 - M0 | 96 | series_rmse_difference | 100 | 0.010563 | [-0.151883, 0.170255] | 1 |
| C | T3 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.212856 | [-0.224212, -0.201374] | 0 |
| C | T3 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.357257 | [-0.369417, -0.344246] | 0 |
| C | T4 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.642203 | [-0.667162, -0.616484] | 0 |
| C | T4 | M2 - DLinear | 96 | series_rmse_difference | 100 | -1.008284 | [-1.031764, -0.984764] | 0 |
| C | T6 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.322014 | [-0.339879, -0.304121] | 0 |
| C | T6 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.149824 | [-0.160226, -0.139368] | 0 |
| D | T0 | M3 - M3-constant-gate | 96 | series_rmse_difference | 200 | 0.000740 | [-0.000678, 0.002042] | 1 |
| D | T2 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.004365 | [-0.021200, 0.011329] | 1 |
| D | T3 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.024544 | [-0.029123, -0.020183] | 0 |
| D | T4 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.078569 | [-0.095868, -0.061417] | 0 |
| D | T6 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.014824 | [-0.018357, -0.011269] | 0 |
| D | T7 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.005610 | [-0.016276, 0.003983] | 1 |
| D | T8 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.073883 | [-0.105416, -0.043043] | 0 |
| D | T0 | M3 - M0 | 96 | series_rmse_difference | 200 | -0.485755 | [-0.508426, -0.463127] | 0 |
| D | T2 | M3 - M0 | 96 | series_rmse_difference | 100 | 0.010563 | [-0.156247, 0.168340] | 1 |
| D | T7 | M3 - M0 | 96 | series_rmse_difference | 100 | -1.427857 | [-1.540992, -1.317568] | 0 |
| D | T8 | M3 - M0 | 96 | series_rmse_difference | 100 | 0.062370 | [0.031748, 0.091877] | 0 |
| E | T7 | M1 - M0 | 96 | series_rmse_difference | 100 | -0.925812 | [-1.020106, -0.829880] | 0 |
| E | T7 | M2 - M0 | 96 | series_rmse_difference | 100 | -1.421099 | [-1.527930, -1.314539] | 0 |
| E | T7 | M3 - M0 | 96 | series_rmse_difference | 100 | -1.427857 | [-1.537456, -1.320105] | 0 |
| F | T1 | M1 - M0 | 96 | series_rmse_difference | 100 | -0.304580 | [-0.342977, -0.266456] | 0 |
| F | T1 | DLinear - M0 | 96 | series_rmse_difference | 100 | -0.321558 | [-0.360190, -0.282690] | 0 |
| F | T1 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.105110 | [-0.121387, -0.088307] | 0 |
| F | T1 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.088132 | [-0.102093, -0.073691] | 0 |
| F | T4 | M2 - M0 | 96 | series_rmse_difference | 100 | -1.674903 | [-1.732190, -1.617412] | 0 |
| F | T4 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.642203 | [-0.667131, -0.616572] | 0 |
| F | T4 | M2 - DLinear | 96 | series_rmse_difference | 100 | -1.008284 | [-1.032246, -0.984400] | 0 |
| F | T6 | M2 - M0 | 96 | series_rmse_difference | 100 | -1.948919 | [-1.989311, -1.909247] | 0 |
| F | T6 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.322014 | [-0.340329, -0.303990] | 0 |
| F | T6 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.149824 | [-0.160240, -0.139436] | 0 |
| G | T8 | M1 - M0 | 96 | series_rmse_difference | 100 | 0.233731 | [0.158499, 0.310572] | 0 |
| G | T8 | DLinear - M0 | 96 | series_rmse_difference | 100 | 0.303950 | [0.227466, 0.379459] | 0 |
| G | T8 | M2 - M0 | 96 | series_rmse_difference | 100 | 0.162435 | [0.116058, 0.208201] | 0 |
| G | T8 | M3 - M0 | 96 | series_rmse_difference | 100 | 0.062370 | [0.031457, 0.091975] | 0 |
| H | T5 | M0 - SeasonalNaive | 96 | series_rmse_difference | 200 | 0.516560 | [0.499127, 0.534098] | 0 |
| H | T5 | M2 - SeasonalNaive | 96 | series_rmse_difference | 200 | -0.441424 | [-0.446333, -0.436577] | 0 |
| H | T5 | M3 - SeasonalNaive | 96 | series_rmse_difference | 200 | -0.453698 | [-0.458650, -0.448748] | 0 |

## Detector Audit

| Mechanism | true label | origins | detector stable | detector change | change rate |
|---|---|---:|---:|---:|---:|
| continuing_trend | visible_change | 1700 | 1406 | 294 | 0.1729 |
| future_jump | stable | 1600 | 1133 | 467 | 0.2919 |
| future_jump | unseen_change | 100 | 76 | 24 | 0.2400 |
| random_walk | stable | 1700 | 1331 | 369 | 0.2171 |
| seasonal_change | stable | 795 | 627 | 168 | 0.2113 |
| seasonal_change | visible_change | 905 | 741 | 164 | 0.1812 |
| stable | stable | 3400 | 2681 | 719 | 0.2115 |
| stable_season | stable | 3400 | 2854 | 546 | 0.1606 |
| trend_break | stable | 795 | 633 | 162 | 0.2038 |
| trend_break | visible_change | 905 | 733 | 172 | 0.1901 |
| variance_shift | stable | 795 | 635 | 160 | 0.2013 |
| variance_shift | visible_change | 905 | 650 | 255 | 0.2818 |
| visible_level_shift | stable | 795 | 645 | 150 | 0.1887 |
| visible_level_shift | visible_change | 905 | 673 | 232 | 0.2564 |
