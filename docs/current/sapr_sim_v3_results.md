# SAPR SIM_V3 Results

This report is generated solely from frozen `sim_v3` task archives. It does not pool V2/V3 or real-data results.

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
| stable | 3400 | 0 | 0 | 2797 | 603 |
| visible_level_shift | 795 | 905 | 0 | 1317 | 383 |
| future_jump | 1600 | 0 | 100 | 1166 | 534 |
| continuing_trend | 0 | 1700 | 0 | 1454 | 246 |
| trend_break | 795 | 905 | 0 | 1404 | 296 |
| stable_season | 3400 | 0 | 0 | 2849 | 551 |
| seasonal_change | 795 | 905 | 0 | 1444 | 256 |
| variance_shift | 795 | 905 | 0 | 1292 | 408 |
| random_walk | 1700 | 0 | 0 | 1391 | 309 |

## Frozen Comparisons

Negative estimates favor the left model. Bootstrap units are independent test sequences after averaging matched seeds. Holm adjustment is within the frozen A-H family.

| family | group | comparison | H | metric | n | estimate | 95% CI | Holm p |
|---|---|---|---:|---|---:|---:|---|---:|
| A | T0 | M2 - M0 | 12 | relative_series_rmse | 200 | -0.230266 | [-0.242439, -0.217650] | 0 |
| A | T0 | M3 - M0 | 12 | relative_series_rmse | 200 | -0.239301 | [-0.251325, -0.226853] | 0 |
| B | T2 | M1 - M0 | 12 | series_rmse_difference | 100 | 0.053875 | [-0.096288, 0.203669] | 1 |
| B | T2 | DLinear - M0 | 12 | series_rmse_difference | 100 | 0.103940 | [-0.073962, 0.278843] | 1 |
| B | T2 | M2 - M0 | 12 | series_rmse_difference | 100 | 0.070756 | [0.000704, 0.146226] | 0.726 |
| B | T2 | M3 - M0 | 12 | series_rmse_difference | 100 | 0.013244 | [-0.026944, 0.057272] | 1 |
| C | T3 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.096693 | [-0.113922, -0.079942] | 0 |
| C | T3 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.076994 | [-0.093598, -0.060280] | 0 |
| C | T4 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.079942 | [-0.100483, -0.059231] | 0 |
| C | T4 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.065583 | [-0.089029, -0.041460] | 0 |
| C | T6 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.160264 | [-0.186105, -0.134857] | 0 |
| C | T6 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.087820 | [-0.104706, -0.070748] | 0 |
| D | T0 | M3 - M3-constant-gate | 12 | series_rmse_difference | 200 | -0.004993 | [-0.007267, -0.002790] | 0 |
| D | T2 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.050782 | [-0.090320, -0.012463] | 0.1368 |
| D | T3 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.014976 | [-0.021536, -0.008973] | 0 |
| D | T4 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.005669 | [-0.016311, 0.005135] | 1 |
| D | T6 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.013145 | [-0.020010, -0.006442] | 0.0038 |
| D | T7 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.034823 | [-0.053428, -0.017492] | 0 |
| D | T8 | M3 - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.047187 | [-0.058308, -0.035794] | 0 |
| D | T0 | M3 - M0 | 12 | series_rmse_difference | 200 | -0.392046 | [-0.415708, -0.368248] | 0 |
| D | T2 | M3 - M0 | 12 | series_rmse_difference | 100 | 0.013244 | [-0.026114, 0.059570] | 1 |
| D | T7 | M3 - M0 | 12 | series_rmse_difference | 100 | -1.203557 | [-1.362283, -1.054845] | 0 |
| D | T8 | M3 - M0 | 12 | series_rmse_difference | 100 | 0.015791 | [0.006190, 0.025374] | 0.015 |
| E | T7 | M1 - M0 | 12 | series_rmse_difference | 100 | -0.650281 | [-0.777638, -0.528707] | 0 |
| E | T7 | M2 - M0 | 12 | series_rmse_difference | 100 | -1.138406 | [-1.284811, -0.993905] | 0 |
| E | T7 | M3 - M0 | 12 | series_rmse_difference | 100 | -1.203557 | [-1.356796, -1.052205] | 0 |
| F | T1 | M1 - M0 | 12 | series_rmse_difference | 100 | -0.187952 | [-0.218196, -0.158216] | 0 |
| F | T1 | DLinear - M0 | 12 | series_rmse_difference | 100 | -0.210008 | [-0.239874, -0.179382] | 0 |
| F | T1 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.132701 | [-0.163028, -0.103388] | 0 |
| F | T1 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.110646 | [-0.135846, -0.087059] | 0 |
| F | T4 | M2 - M0 | 12 | series_rmse_difference | 100 | -0.298511 | [-0.329202, -0.265738] | 0 |
| F | T4 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.079942 | [-0.101011, -0.058840] | 0 |
| F | T4 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.065583 | [-0.088777, -0.041482] | 0 |
| F | T6 | M2 - M0 | 12 | series_rmse_difference | 100 | -1.058120 | [-1.117596, -0.998819] | 0 |
| F | T6 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.160264 | [-0.185185, -0.135554] | 0 |
| F | T6 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.087820 | [-0.104724, -0.071265] | 0 |
| G | T8 | M1 - M0 | 12 | series_rmse_difference | 100 | 0.193415 | [0.156371, 0.231894] | 0 |
| G | T8 | DLinear - M0 | 12 | series_rmse_difference | 100 | 0.343594 | [0.290945, 0.395662] | 0 |
| G | T8 | M2 - M0 | 12 | series_rmse_difference | 100 | 0.065898 | [0.046648, 0.085558] | 0 |
| G | T8 | M3 - M0 | 12 | series_rmse_difference | 100 | 0.015791 | [0.006032, 0.025403] | 0.0104 |
| H | T5 | M0 - SeasonalNaive | 12 | series_rmse_difference | 200 | 0.589896 | [0.551592, 0.627887] | 0 |
| H | T5 | M2 - SeasonalNaive | 12 | series_rmse_difference | 200 | -0.431225 | [-0.445518, -0.416367] | 0 |
| H | T5 | M3 - SeasonalNaive | 12 | series_rmse_difference | 200 | -0.439195 | [-0.453489, -0.424706] | 0 |
| A | T0 | M2 - M0 | 24 | relative_series_rmse | 200 | -0.244633 | [-0.255230, -0.234243] | 0 |
| A | T0 | M3 - M0 | 24 | relative_series_rmse | 200 | -0.254715 | [-0.264807, -0.244047] | 0 |
| B | T2 | M1 - M0 | 24 | series_rmse_difference | 100 | 0.113690 | [-0.040610, 0.267825] | 1 |
| B | T2 | DLinear - M0 | 24 | series_rmse_difference | 100 | 0.160866 | [-0.034455, 0.352241] | 1 |
| B | T2 | M2 - M0 | 24 | series_rmse_difference | 100 | 0.066695 | [0.002812, 0.128364] | 0.6336 |
| B | T2 | M3 - M0 | 24 | series_rmse_difference | 100 | -0.003071 | [-0.042209, 0.038078] | 1 |
| C | T3 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.097577 | [-0.114235, -0.081196] | 0 |
| C | T3 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.076791 | [-0.092230, -0.062066] | 0 |
| C | T4 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.138995 | [-0.159553, -0.118874] | 0 |
| C | T4 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.113242 | [-0.132634, -0.092967] | 0 |
| C | T6 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.231260 | [-0.251068, -0.211427] | 0 |
| C | T6 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.145559 | [-0.161861, -0.129158] | 0 |
| D | T0 | M3 - M3-constant-gate | 24 | series_rmse_difference | 200 | -0.005219 | [-0.007119, -0.003424] | 0 |
| D | T2 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.073749 | [-0.118449, -0.031064] | 0.0068 |
| D | T3 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.011765 | [-0.018454, -0.005672] | 0 |
| D | T4 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.012218 | [-0.021590, -0.003070] | 0.0832 |
| D | T6 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.010163 | [-0.014586, -0.005844] | 0 |
| D | T7 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.030531 | [-0.045807, -0.016330] | 0 |
| D | T8 | M3 - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.037159 | [-0.050314, -0.024082] | 0 |
| D | T0 | M3 - M0 | 24 | series_rmse_difference | 200 | -0.427285 | [-0.450447, -0.405217] | 0 |
| D | T2 | M3 - M0 | 24 | series_rmse_difference | 100 | -0.003071 | [-0.042279, 0.038296] | 1 |
| D | T7 | M3 - M0 | 24 | series_rmse_difference | 100 | -1.307301 | [-1.446651, -1.171536] | 0 |
| D | T8 | M3 - M0 | 24 | series_rmse_difference | 100 | 0.012721 | [0.002429, 0.023058] | 0.1584 |
| E | T7 | M1 - M0 | 24 | series_rmse_difference | 100 | -0.703214 | [-0.817501, -0.592088] | 0 |
| E | T7 | M2 - M0 | 24 | series_rmse_difference | 100 | -1.244046 | [-1.375351, -1.113957] | 0 |
| E | T7 | M3 - M0 | 24 | series_rmse_difference | 100 | -1.307301 | [-1.446856, -1.171384] | 0 |
| F | T1 | M1 - M0 | 24 | series_rmse_difference | 100 | -0.225365 | [-0.256549, -0.195245] | 0 |
| F | T1 | DLinear - M0 | 24 | series_rmse_difference | 100 | -0.239818 | [-0.271421, -0.207020] | 0 |
| F | T1 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.129101 | [-0.153842, -0.105475] | 0 |
| F | T1 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.114648 | [-0.135420, -0.095000] | 0 |
| F | T4 | M2 - M0 | 24 | series_rmse_difference | 100 | -0.412038 | [-0.444464, -0.379643] | 0 |
| F | T4 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.138995 | [-0.159175, -0.118719] | 0 |
| F | T4 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.113242 | [-0.132777, -0.093710] | 0 |
| F | T6 | M2 - M0 | 24 | series_rmse_difference | 100 | -0.973929 | [-1.012981, -0.934173] | 0 |
| F | T6 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.231260 | [-0.251125, -0.211813] | 0 |
| F | T6 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.145559 | [-0.162323, -0.128987] | 0 |
| G | T8 | M1 - M0 | 24 | series_rmse_difference | 100 | 0.151210 | [0.112137, 0.189824] | 0 |
| G | T8 | DLinear - M0 | 24 | series_rmse_difference | 100 | 0.301291 | [0.246834, 0.356729] | 0 |
| G | T8 | M2 - M0 | 24 | series_rmse_difference | 100 | 0.056111 | [0.036996, 0.075004] | 0 |
| G | T8 | M3 - M0 | 24 | series_rmse_difference | 100 | 0.012721 | [0.002376, 0.022943] | 0.0372 |
| H | T5 | M0 - SeasonalNaive | 24 | series_rmse_difference | 200 | 0.653925 | [0.617884, 0.690439] | 0 |
| H | T5 | M2 - SeasonalNaive | 24 | series_rmse_difference | 200 | -0.426878 | [-0.437391, -0.416553] | 0 |
| H | T5 | M3 - SeasonalNaive | 24 | series_rmse_difference | 200 | -0.440493 | [-0.450776, -0.430024] | 0 |
| A | T0 | M2 - M0 | 48 | relative_series_rmse | 200 | -0.254496 | [-0.264187, -0.244843] | 0 |
| A | T0 | M3 - M0 | 48 | relative_series_rmse | 200 | -0.263535 | [-0.273168, -0.253929] | 0 |
| B | T2 | M1 - M0 | 48 | series_rmse_difference | 100 | 0.135897 | [-0.007442, 0.277908] | 0.8764 |
| B | T2 | DLinear - M0 | 48 | series_rmse_difference | 100 | 0.170779 | [-0.031120, 0.370618] | 1 |
| B | T2 | M2 - M0 | 48 | series_rmse_difference | 100 | 0.029690 | [-0.044787, 0.104909] | 1 |
| B | T2 | M3 - M0 | 48 | series_rmse_difference | 100 | -0.009817 | [-0.061045, 0.039984] | 1 |
| C | T3 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.139928 | [-0.158460, -0.121963] | 0 |
| C | T3 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.120208 | [-0.136319, -0.104064] | 0 |
| C | T4 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.321565 | [-0.345262, -0.297665] | 0 |
| C | T4 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.287871 | [-0.309614, -0.266158] | 0 |
| C | T6 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.349004 | [-0.369579, -0.328316] | 0 |
| C | T6 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.188380 | [-0.203153, -0.173396] | 0 |
| D | T0 | M3 - M3-constant-gate | 48 | series_rmse_difference | 200 | -0.005730 | [-0.007464, -0.004117] | 0 |
| D | T2 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.054414 | [-0.103245, -0.007485] | 0.22 |
| D | T3 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.008083 | [-0.014877, -0.002158] | 0.0784 |
| D | T4 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.022609 | [-0.031910, -0.013749] | 0 |
| D | T6 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.037824 | [-0.044199, -0.032001] | 0 |
| D | T7 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.023560 | [-0.037980, -0.010879] | 0 |
| D | T8 | M3 - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.034140 | [-0.050480, -0.018178] | 0.0038 |
| D | T0 | M3 - M0 | 48 | series_rmse_difference | 200 | -0.447845 | [-0.469188, -0.426468] | 0 |
| D | T2 | M3 - M0 | 48 | series_rmse_difference | 100 | -0.009817 | [-0.059680, 0.040796] | 1 |
| D | T7 | M3 - M0 | 48 | series_rmse_difference | 100 | -1.302931 | [-1.431752, -1.176290] | 0 |
| D | T8 | M3 - M0 | 48 | series_rmse_difference | 100 | 0.013438 | [0.000495, 0.026003] | 0.3762 |
| E | T7 | M1 - M0 | 48 | series_rmse_difference | 100 | -0.767646 | [-0.878367, -0.658728] | 0 |
| E | T7 | M2 - M0 | 48 | series_rmse_difference | 100 | -1.250807 | [-1.373808, -1.130046] | 0 |
| E | T7 | M3 - M0 | 48 | series_rmse_difference | 100 | -1.302931 | [-1.431338, -1.176790] | 0 |
| F | T1 | M1 - M0 | 48 | series_rmse_difference | 100 | -0.256662 | [-0.287469, -0.227290] | 0 |
| F | T1 | DLinear - M0 | 48 | series_rmse_difference | 100 | -0.254304 | [-0.286405, -0.222085] | 0 |
| F | T1 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.104797 | [-0.124004, -0.086128] | 0 |
| F | T1 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.107154 | [-0.124790, -0.089912] | 0 |
| F | T4 | M2 - M0 | 48 | series_rmse_difference | 100 | -0.730624 | [-0.767236, -0.693409] | 0 |
| F | T4 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.321565 | [-0.345453, -0.297897] | 0 |
| F | T4 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.287871 | [-0.309602, -0.266488] | 0 |
| F | T6 | M2 - M0 | 48 | series_rmse_difference | 100 | -1.903031 | [-1.946011, -1.860811] | 0 |
| F | T6 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.349004 | [-0.370170, -0.328314] | 0 |
| F | T6 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.188380 | [-0.203738, -0.173391] | 0 |
| G | T8 | M1 - M0 | 48 | series_rmse_difference | 100 | 0.110421 | [0.072070, 0.148683] | 0 |
| G | T8 | DLinear - M0 | 48 | series_rmse_difference | 100 | 0.211151 | [0.154447, 0.266087] | 0 |
| G | T8 | M2 - M0 | 48 | series_rmse_difference | 100 | 0.055978 | [0.033117, 0.078887] | 0 |
| G | T8 | M3 - M0 | 48 | series_rmse_difference | 100 | 0.013438 | [0.000564, 0.025801] | 0.0852 |
| H | T5 | M0 - SeasonalNaive | 48 | series_rmse_difference | 200 | 0.523003 | [0.504119, 0.541749] | 0 |
| H | T5 | M2 - SeasonalNaive | 48 | series_rmse_difference | 200 | -0.419977 | [-0.427146, -0.412760] | 0 |
| H | T5 | M3 - SeasonalNaive | 48 | series_rmse_difference | 200 | -0.440960 | [-0.448050, -0.433739] | 0 |
| A | T0 | M2 - M0 | 96 | relative_series_rmse | 200 | -0.258856 | [-0.267909, -0.249605] | 0 |
| A | T0 | M3 - M0 | 96 | relative_series_rmse | 200 | -0.267755 | [-0.276765, -0.258471] | 0 |
| B | T2 | M1 - M0 | 96 | series_rmse_difference | 100 | 0.129268 | [-0.036120, 0.295595] | 1 |
| B | T2 | DLinear - M0 | 96 | series_rmse_difference | 100 | 0.179726 | [-0.043182, 0.402901] | 1 |
| B | T2 | M2 - M0 | 96 | series_rmse_difference | 100 | 0.022496 | [-0.076190, 0.122283] | 1 |
| B | T2 | M3 - M0 | 96 | series_rmse_difference | 100 | -0.005349 | [-0.069589, 0.059604] | 1 |
| C | T3 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.322660 | [-0.341294, -0.304144] | 0 |
| C | T3 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.297028 | [-0.312754, -0.280506] | 0 |
| C | T4 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.815550 | [-0.845458, -0.786429] | 0 |
| C | T4 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.763813 | [-0.789512, -0.738209] | 0 |
| C | T6 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.381011 | [-0.401276, -0.360349] | 0 |
| C | T6 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.206153 | [-0.221564, -0.190399] | 0 |
| D | T0 | M3 - M3-constant-gate | 96 | series_rmse_difference | 200 | -0.004981 | [-0.006568, -0.003561] | 0 |
| D | T2 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.033729 | [-0.094058, 0.025765] | 1 |
| D | T3 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | 0.000636 | [-0.007092, 0.006983] | 1 |
| D | T4 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.057354 | [-0.068375, -0.046898] | 0 |
| D | T6 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.037095 | [-0.043399, -0.031508] | 0 |
| D | T7 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.025831 | [-0.039370, -0.013684] | 0 |
| D | T8 | M3 - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.035487 | [-0.056099, -0.015534] | 0.0096 |
| D | T0 | M3 - M0 | 96 | series_rmse_difference | 200 | -0.459163 | [-0.479658, -0.438099] | 0 |
| D | T2 | M3 - M0 | 96 | series_rmse_difference | 100 | -0.005349 | [-0.069420, 0.058342] | 1 |
| D | T7 | M3 - M0 | 96 | series_rmse_difference | 100 | -1.336834 | [-1.467023, -1.210601] | 0 |
| D | T8 | M3 - M0 | 96 | series_rmse_difference | 100 | 0.014393 | [-0.003704, 0.031777] | 0.9024 |
| E | T7 | M1 - M0 | 96 | series_rmse_difference | 100 | -0.775514 | [-0.884373, -0.669715] | 0 |
| E | T7 | M2 - M0 | 96 | series_rmse_difference | 100 | -1.286250 | [-1.407530, -1.167550] | 0 |
| E | T7 | M3 - M0 | 96 | series_rmse_difference | 100 | -1.336834 | [-1.465148, -1.214161] | 0 |
| F | T1 | M1 - M0 | 96 | series_rmse_difference | 100 | -0.239151 | [-0.270654, -0.206735] | 0 |
| F | T1 | DLinear - M0 | 96 | series_rmse_difference | 100 | -0.216637 | [-0.249877, -0.183411] | 0 |
| F | T1 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.110376 | [-0.130121, -0.090689] | 0 |
| F | T1 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.132890 | [-0.151359, -0.113740] | 0 |
| F | T4 | M2 - M0 | 96 | series_rmse_difference | 100 | -1.546840 | [-1.590807, -1.502249] | 0 |
| F | T4 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.815550 | [-0.845712, -0.786070] | 0 |
| F | T4 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.763813 | [-0.789273, -0.738963] | 0 |
| F | T6 | M2 - M0 | 96 | series_rmse_difference | 100 | -1.907824 | [-1.945835, -1.869679] | 0 |
| F | T6 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.381011 | [-0.401838, -0.360911] | 0 |
| F | T6 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.206153 | [-0.221193, -0.190591] | 0 |
| G | T8 | M1 - M0 | 96 | series_rmse_difference | 100 | 0.119557 | [0.073458, 0.165589] | 0 |
| G | T8 | DLinear - M0 | 96 | series_rmse_difference | 100 | 0.194197 | [0.129784, 0.257472] | 0 |
| G | T8 | M2 - M0 | 96 | series_rmse_difference | 100 | 0.062168 | [0.029901, 0.095331] | 0 |
| G | T8 | M3 - M0 | 96 | series_rmse_difference | 100 | 0.014393 | [-0.003366, 0.031659] | 0.1114 |
| H | T5 | M0 - SeasonalNaive | 96 | series_rmse_difference | 200 | 0.524176 | [0.507259, 0.541553] | 0 |
| H | T5 | M2 - SeasonalNaive | 96 | series_rmse_difference | 200 | -0.417462 | [-0.422416, -0.412603] | 0 |
| H | T5 | M3 - SeasonalNaive | 96 | series_rmse_difference | 200 | -0.437766 | [-0.442743, -0.432717] | 0 |

## Detector Audit

| Mechanism | true label | origins | detector stable | detector change | change rate |
|---|---|---:|---:|---:|---:|
| continuing_trend | visible_change | 1700 | 1454 | 246 | 0.1447 |
| future_jump | stable | 1600 | 1091 | 509 | 0.3181 |
| future_jump | unseen_change | 100 | 75 | 25 | 0.2500 |
| random_walk | stable | 1700 | 1391 | 309 | 0.1818 |
| seasonal_change | stable | 795 | 687 | 108 | 0.1358 |
| seasonal_change | visible_change | 905 | 757 | 148 | 0.1635 |
| stable | stable | 3400 | 2797 | 603 | 0.1774 |
| stable_season | stable | 3400 | 2849 | 551 | 0.1621 |
| trend_break | stable | 795 | 630 | 165 | 0.2075 |
| trend_break | visible_change | 905 | 774 | 131 | 0.1448 |
| variance_shift | stable | 795 | 623 | 172 | 0.2164 |
| variance_shift | visible_change | 905 | 669 | 236 | 0.2608 |
| visible_level_shift | stable | 795 | 650 | 145 | 0.1824 |
| visible_level_shift | visible_change | 905 | 667 | 238 | 0.2630 |
