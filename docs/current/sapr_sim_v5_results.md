# SAPR SIM_V5 Results

This report is generated solely from frozen `sim_v5` task archives. It does not pool V2/V3 or real-data results.

## Decision

- `T0_safety_pass`: `True`
- `T2_leakage_pass`: `True`
- `T8_random_walk_pass`: `True`
- `patch_candidate_groups`: `['T4', 'T6']`
- `patch_claim_pass`: `True`
- `gate_open_evidence`: `False`
- `gate_close_evidence`: `True`
- `state_gate_claim_pass`: `False`
- `gate_attribution_evidence`: `False`

## Coverage

| Mechanism | true stable | true visible | true unseen | detector stable | detector change |
|---|---:|---:|---:|---:|---:|
| stable | 2600 | 0 | 0 | 1763 | 837 |
| visible_level_shift | 395 | 905 | 0 | 783 | 517 |
| future_jump | 1200 | 0 | 100 | 878 | 422 |
| continuing_trend | 0 | 1300 | 0 | 894 | 406 |
| trend_break | 395 | 905 | 0 | 757 | 543 |
| stable_season | 2600 | 0 | 0 | 1764 | 836 |
| seasonal_change | 395 | 905 | 0 | 973 | 327 |
| variance_shift | 395 | 905 | 0 | 880 | 420 |
| random_walk | 1300 | 0 | 0 | 900 | 400 |

## Frozen Comparisons

Negative estimates favor the left model. Bootstrap units are independent test sequences after averaging matched seeds. Holm adjustment is within the frozen A-H family.

| family | group | comparison | H | metric | n | estimate | 95% CI | Holm p |
|---|---|---|---:|---|---:|---:|---|---:|
| A | T0 | M2 - M0 | 12 | relative_series_rmse | 200 | -0.246880 | [-0.258451, -0.235120] | 0 |
| A | T0 | M3-trigger-gate - M0 | 12 | relative_series_rmse | 200 | -0.243848 | [-0.255114, -0.232244] | 0 |
| B | T2 | M1 - M0 | 12 | series_rmse_difference | 100 | 0.172842 | [0.032134, 0.313811] | 0.2624 |
| B | T2 | DLinear - M0 | 12 | series_rmse_difference | 100 | 0.120326 | [-0.032221, 0.275907] | 1 |
| B | T2 | M2 - M0 | 12 | series_rmse_difference | 100 | 0.077949 | [0.010955, 0.145951] | 0.2938 |
| B | T2 | M3-trigger-gate - M0 | 12 | series_rmse_difference | 100 | 0.073605 | [0.011230, 0.134658] | 0.2632 |
| C | T3 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.055045 | [-0.072845, -0.037887] | 0 |
| C | T3 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.067260 | [-0.087491, -0.046800] | 0 |
| C | T4 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.070818 | [-0.092419, -0.049103] | 0 |
| C | T4 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.103835 | [-0.126817, -0.081722] | 0 |
| C | T6 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.146852 | [-0.171854, -0.121080] | 0 |
| C | T6 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.103717 | [-0.127147, -0.080014] | 0 |
| D | T0 | M3-trigger-gate - M3-constant-gate | 12 | series_rmse_difference | 200 | 0.004483 | [0.003186, 0.005778] | 0 |
| D | T2 | M3-trigger-gate - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.034379 | [-0.076161, 0.006815] | 0.9216 |
| D | T3 | M3-trigger-gate - M3-constant-gate | 12 | series_rmse_difference | 100 | -0.008227 | [-0.013293, -0.003187] | 0.0252 |
| D | T4 | M3-trigger-gate - M3-constant-gate | 12 | series_rmse_difference | 100 | 0.007423 | [0.002292, 0.012527] | 0.08 |
| D | T6 | M3-trigger-gate - M3-constant-gate | 12 | series_rmse_difference | 100 | 0.006727 | [-0.000947, 0.013745] | 0.88 |
| D | T7 | M3-trigger-gate - M3-constant-gate | 12 | series_rmse_difference | 100 | 0.010513 | [0.004229, 0.016686] | 0.0114 |
| D | T8 | M3-trigger-gate - M3-constant-gate | 12 | series_rmse_difference | 100 | 0.004176 | [-0.009231, 0.018106] | 1 |
| D | T0 | M3-trigger-gate - M0 | 12 | series_rmse_difference | 200 | -0.403465 | [-0.426128, -0.380461] | 0 |
| D | T2 | M3-trigger-gate - M0 | 12 | series_rmse_difference | 100 | 0.073605 | [0.012566, 0.136578] | 0.333 |
| D | T7 | M3-trigger-gate - M0 | 12 | series_rmse_difference | 100 | -1.128059 | [-1.245871, -1.015190] | 0 |
| D | T8 | M3-trigger-gate - M0 | 12 | series_rmse_difference | 100 | 0.087927 | [0.065304, 0.110502] | 0 |
| E | T7 | M1 - M0 | 12 | series_rmse_difference | 100 | -0.667271 | [-0.759306, -0.575612] | 0 |
| E | T7 | M2 - M0 | 12 | series_rmse_difference | 100 | -1.136954 | [-1.256080, -1.017820] | 0 |
| E | T7 | M3-trigger-gate - M0 | 12 | series_rmse_difference | 100 | -1.128059 | [-1.246493, -1.013754] | 0 |
| F | T1 | M1 - M0 | 12 | series_rmse_difference | 100 | -0.197001 | [-0.230886, -0.162389] | 0 |
| F | T1 | DLinear - M0 | 12 | series_rmse_difference | 100 | -0.209377 | [-0.242625, -0.176418] | 0 |
| F | T1 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.123003 | [-0.145814, -0.101386] | 0 |
| F | T1 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.110626 | [-0.130159, -0.090026] | 0 |
| F | T4 | M2 - M0 | 12 | series_rmse_difference | 100 | -0.260778 | [-0.293612, -0.228814] | 0 |
| F | T4 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.070818 | [-0.092402, -0.049444] | 0 |
| F | T4 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.103835 | [-0.126792, -0.082053] | 0 |
| F | T6 | M2 - M0 | 12 | series_rmse_difference | 100 | -1.050126 | [-1.108744, -0.993535] | 0 |
| F | T6 | M2 - M1 | 12 | series_rmse_difference | 100 | -0.146852 | [-0.171755, -0.121387] | 0 |
| F | T6 | M2 - DLinear | 12 | series_rmse_difference | 100 | -0.103717 | [-0.127592, -0.079790] | 0 |
| G | T8 | M1 - M0 | 12 | series_rmse_difference | 100 | 0.251577 | [0.205289, 0.297306] | 0 |
| G | T8 | DLinear - M0 | 12 | series_rmse_difference | 100 | 0.328782 | [0.277762, 0.378951] | 0 |
| G | T8 | M2 - M0 | 12 | series_rmse_difference | 100 | 0.119293 | [0.092673, 0.146552] | 0 |
| G | T8 | M3-trigger-gate - M0 | 12 | series_rmse_difference | 100 | 0.087927 | [0.065452, 0.110734] | 0 |
| H | T5 | M0 - SeasonalNaive | 12 | series_rmse_difference | 200 | 0.563919 | [0.525562, 0.601555] | 0 |
| H | T5 | M2 - SeasonalNaive | 12 | series_rmse_difference | 200 | -0.450650 | [-0.466160, -0.435430] | 0 |
| H | T5 | M3-trigger-gate - SeasonalNaive | 12 | series_rmse_difference | 200 | -0.437156 | [-0.452975, -0.420848] | 0 |
| I | T4 | M3-trigger-gate - M3-hidden-only | 12 | series_rmse_difference | 100 | 0.025315 | [0.014028, 0.035970] | 0 |
| I | T4 | M3-trigger-gate - M3-no-state-feature | 12 | series_rmse_difference | 100 | 0.038708 | [0.026386, 0.051269] | 0 |
| A | T0 | M2 - M0 | 24 | relative_series_rmse | 200 | -0.256327 | [-0.266973, -0.245380] | 0 |
| A | T0 | M3-trigger-gate - M0 | 24 | relative_series_rmse | 200 | -0.253963 | [-0.264226, -0.243313] | 0 |
| B | T2 | M1 - M0 | 24 | series_rmse_difference | 100 | 0.085150 | [-0.049615, 0.220634] | 1 |
| B | T2 | DLinear - M0 | 24 | series_rmse_difference | 100 | 0.079849 | [-0.072917, 0.229761] | 1 |
| B | T2 | M2 - M0 | 24 | series_rmse_difference | 100 | 0.089201 | [0.015563, 0.167409] | 0.2624 |
| B | T2 | M3-trigger-gate - M0 | 24 | series_rmse_difference | 100 | 0.079669 | [0.004567, 0.152606] | 0.4488 |
| C | T3 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.071357 | [-0.087500, -0.055687] | 0 |
| C | T3 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.088856 | [-0.108221, -0.069747] | 0 |
| C | T4 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.134785 | [-0.154186, -0.115084] | 0 |
| C | T4 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.154852 | [-0.175280, -0.135219] | 0 |
| C | T6 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.215762 | [-0.237105, -0.193999] | 0 |
| C | T6 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.160826 | [-0.182598, -0.139125] | 0 |
| D | T0 | M3-trigger-gate - M3-constant-gate | 24 | series_rmse_difference | 200 | 0.003974 | [0.002954, 0.004968] | 0 |
| D | T2 | M3-trigger-gate - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.021436 | [-0.067482, 0.025619] | 1 |
| D | T3 | M3-trigger-gate - M3-constant-gate | 24 | series_rmse_difference | 100 | -0.009715 | [-0.014498, -0.005004] | 0 |
| D | T4 | M3-trigger-gate - M3-constant-gate | 24 | series_rmse_difference | 100 | 0.007234 | [0.002212, 0.012128] | 0.0782 |
| D | T6 | M3-trigger-gate - M3-constant-gate | 24 | series_rmse_difference | 100 | 0.013273 | [0.007899, 0.017902] | 0 |
| D | T7 | M3-trigger-gate - M3-constant-gate | 24 | series_rmse_difference | 100 | 0.012235 | [0.006661, 0.017668] | 0 |
| D | T8 | M3-trigger-gate - M3-constant-gate | 24 | series_rmse_difference | 100 | 0.009119 | [-0.004817, 0.022480] | 1 |
| D | T0 | M3-trigger-gate - M0 | 24 | series_rmse_difference | 200 | -0.429599 | [-0.452177, -0.406461] | 0 |
| D | T2 | M3-trigger-gate - M0 | 24 | series_rmse_difference | 100 | 0.079669 | [0.002165, 0.150994] | 0.6188 |
| D | T7 | M3-trigger-gate - M0 | 24 | series_rmse_difference | 100 | -1.266674 | [-1.378262, -1.157386] | 0 |
| D | T8 | M3-trigger-gate - M0 | 24 | series_rmse_difference | 100 | 0.076966 | [0.052865, 0.101637] | 0 |
| E | T7 | M1 - M0 | 24 | series_rmse_difference | 100 | -0.756302 | [-0.845450, -0.668476] | 0 |
| E | T7 | M2 - M0 | 24 | series_rmse_difference | 100 | -1.277201 | [-1.390055, -1.165577] | 0 |
| E | T7 | M3-trigger-gate - M0 | 24 | series_rmse_difference | 100 | -1.266674 | [-1.375623, -1.157608] | 0 |
| F | T1 | M1 - M0 | 24 | series_rmse_difference | 100 | -0.233226 | [-0.266037, -0.199660] | 0 |
| F | T1 | DLinear - M0 | 24 | series_rmse_difference | 100 | -0.230187 | [-0.260533, -0.200122] | 0 |
| F | T1 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.126500 | [-0.146602, -0.106704] | 0 |
| F | T1 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.129539 | [-0.148502, -0.110627] | 0 |
| F | T4 | M2 - M0 | 24 | series_rmse_difference | 100 | -0.386019 | [-0.418178, -0.353956] | 0 |
| F | T4 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.134785 | [-0.154405, -0.115409] | 0 |
| F | T4 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.154852 | [-0.175511, -0.135028] | 0 |
| F | T6 | M2 - M0 | 24 | series_rmse_difference | 100 | -0.975751 | [-1.011976, -0.939827] | 0 |
| F | T6 | M2 - M1 | 24 | series_rmse_difference | 100 | -0.215762 | [-0.237823, -0.195066] | 0 |
| F | T6 | M2 - DLinear | 24 | series_rmse_difference | 100 | -0.160826 | [-0.182473, -0.139374] | 0 |
| G | T8 | M1 - M0 | 24 | series_rmse_difference | 100 | 0.204936 | [0.160383, 0.248816] | 0 |
| G | T8 | DLinear - M0 | 24 | series_rmse_difference | 100 | 0.280752 | [0.226532, 0.334333] | 0 |
| G | T8 | M2 - M0 | 24 | series_rmse_difference | 100 | 0.102720 | [0.077105, 0.129299] | 0 |
| G | T8 | M3-trigger-gate - M0 | 24 | series_rmse_difference | 100 | 0.076966 | [0.053181, 0.101975] | 0 |
| H | T5 | M0 - SeasonalNaive | 24 | series_rmse_difference | 200 | 0.641932 | [0.604996, 0.678705] | 0 |
| H | T5 | M2 - SeasonalNaive | 24 | series_rmse_difference | 200 | -0.429529 | [-0.440338, -0.418943] | 0 |
| H | T5 | M3-trigger-gate - SeasonalNaive | 24 | series_rmse_difference | 200 | -0.418945 | [-0.430428, -0.407382] | 0 |
| I | T4 | M3-trigger-gate - M3-hidden-only | 24 | series_rmse_difference | 100 | 0.036359 | [0.025433, 0.047512] | 0 |
| I | T4 | M3-trigger-gate - M3-no-state-feature | 24 | series_rmse_difference | 100 | 0.053973 | [0.041966, 0.066223] | 0 |
| A | T0 | M2 - M0 | 48 | relative_series_rmse | 200 | -0.259253 | [-0.269021, -0.249373] | 0 |
| A | T0 | M3-trigger-gate - M0 | 48 | relative_series_rmse | 200 | -0.257573 | [-0.267098, -0.247582] | 0 |
| B | T2 | M1 - M0 | 48 | series_rmse_difference | 100 | 0.059806 | [-0.076375, 0.196116] | 1 |
| B | T2 | DLinear - M0 | 48 | series_rmse_difference | 100 | 0.081629 | [-0.067297, 0.236729] | 1 |
| B | T2 | M2 - M0 | 48 | series_rmse_difference | 100 | 0.027543 | [-0.080979, 0.138445] | 1 |
| B | T2 | M3-trigger-gate - M0 | 48 | series_rmse_difference | 100 | 0.028004 | [-0.089703, 0.142003] | 1 |
| C | T3 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.130214 | [-0.150085, -0.111019] | 0 |
| C | T3 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.142922 | [-0.163179, -0.122364] | 0 |
| C | T4 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.336777 | [-0.359519, -0.314499] | 0 |
| C | T4 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.358125 | [-0.377712, -0.339214] | 0 |
| C | T6 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.309648 | [-0.332070, -0.286700] | 0 |
| C | T6 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.176835 | [-0.195560, -0.157873] | 0 |
| D | T0 | M3-trigger-gate - M3-constant-gate | 48 | series_rmse_difference | 200 | 0.004323 | [0.003448, 0.005237] | 0 |
| D | T2 | M3-trigger-gate - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.001737 | [-0.048143, 0.043578] | 1 |
| D | T3 | M3-trigger-gate - M3-constant-gate | 48 | series_rmse_difference | 100 | -0.012133 | [-0.016760, -0.007525] | 0 |
| D | T4 | M3-trigger-gate - M3-constant-gate | 48 | series_rmse_difference | 100 | 0.005407 | [-0.000512, 0.011175] | 0.876 |
| D | T6 | M3-trigger-gate - M3-constant-gate | 48 | series_rmse_difference | 100 | 0.020910 | [0.016848, 0.024671] | 0 |
| D | T7 | M3-trigger-gate - M3-constant-gate | 48 | series_rmse_difference | 100 | 0.013943 | [0.009677, 0.018148] | 0 |
| D | T8 | M3-trigger-gate - M3-constant-gate | 48 | series_rmse_difference | 100 | 0.014465 | [-0.000471, 0.029286] | 0.754 |
| D | T0 | M3-trigger-gate - M0 | 48 | series_rmse_difference | 200 | -0.439504 | [-0.461640, -0.418111] | 0 |
| D | T2 | M3-trigger-gate - M0 | 48 | series_rmse_difference | 100 | 0.028004 | [-0.092594, 0.140421] | 1 |
| D | T7 | M3-trigger-gate - M0 | 48 | series_rmse_difference | 100 | -1.312696 | [-1.423325, -1.206472] | 0 |
| D | T8 | M3-trigger-gate - M0 | 48 | series_rmse_difference | 100 | 0.073301 | [0.040840, 0.105911] | 0 |
| E | T7 | M1 - M0 | 48 | series_rmse_difference | 100 | -0.831484 | [-0.926502, -0.739816] | 0 |
| E | T7 | M2 - M0 | 48 | series_rmse_difference | 100 | -1.324751 | [-1.440872, -1.213723] | 0 |
| E | T7 | M3-trigger-gate - M0 | 48 | series_rmse_difference | 100 | -1.312696 | [-1.423439, -1.203046] | 0 |
| F | T1 | M1 - M0 | 48 | series_rmse_difference | 100 | -0.273021 | [-0.306273, -0.241404] | 0 |
| F | T1 | DLinear - M0 | 48 | series_rmse_difference | 100 | -0.260314 | [-0.290155, -0.231279] | 0 |
| F | T1 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.097112 | [-0.111485, -0.083052] | 0 |
| F | T1 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.109819 | [-0.125356, -0.094302] | 0 |
| F | T4 | M2 - M0 | 48 | series_rmse_difference | 100 | -0.696678 | [-0.737555, -0.656251] | 0 |
| F | T4 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.336777 | [-0.359453, -0.314567] | 0 |
| F | T4 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.358125 | [-0.377737, -0.339334] | 0 |
| F | T6 | M2 - M0 | 48 | series_rmse_difference | 100 | -1.929800 | [-1.971545, -1.888687] | 0 |
| F | T6 | M2 - M1 | 48 | series_rmse_difference | 100 | -0.309648 | [-0.332776, -0.286803] | 0 |
| F | T6 | M2 - DLinear | 48 | series_rmse_difference | 100 | -0.176835 | [-0.195682, -0.158271] | 0 |
| G | T8 | M1 - M0 | 48 | series_rmse_difference | 100 | 0.177817 | [0.130246, 0.223521] | 0 |
| G | T8 | DLinear - M0 | 48 | series_rmse_difference | 100 | 0.258480 | [0.199889, 0.316703] | 0 |
| G | T8 | M2 - M0 | 48 | series_rmse_difference | 100 | 0.089427 | [0.059159, 0.119343] | 0 |
| G | T8 | M3-trigger-gate - M0 | 48 | series_rmse_difference | 100 | 0.073301 | [0.041579, 0.105731] | 0 |
| H | T5 | M0 - SeasonalNaive | 48 | series_rmse_difference | 200 | 0.517944 | [0.496277, 0.540016] | 0 |
| H | T5 | M2 - SeasonalNaive | 48 | series_rmse_difference | 200 | -0.415026 | [-0.422862, -0.407119] | 0 |
| H | T5 | M3-trigger-gate - SeasonalNaive | 48 | series_rmse_difference | 200 | -0.406186 | [-0.414505, -0.397937] | 0 |
| I | T4 | M3-trigger-gate - M3-hidden-only | 48 | series_rmse_difference | 100 | 0.076678 | [0.064712, 0.088790] | 0 |
| I | T4 | M3-trigger-gate - M3-no-state-feature | 48 | series_rmse_difference | 100 | 0.105878 | [0.091495, 0.120571] | 0 |
| A | T0 | M2 - M0 | 96 | relative_series_rmse | 200 | -0.260769 | [-0.270106, -0.251335] | 0 |
| A | T0 | M3-trigger-gate - M0 | 96 | relative_series_rmse | 200 | -0.258736 | [-0.267833, -0.249632] | 0 |
| B | T2 | M1 - M0 | 96 | series_rmse_difference | 100 | -0.009094 | [-0.211371, 0.197018] | 1 |
| B | T2 | DLinear - M0 | 96 | series_rmse_difference | 100 | 0.012652 | [-0.214637, 0.242473] | 1 |
| B | T2 | M2 - M0 | 96 | series_rmse_difference | 100 | 0.008850 | [-0.142379, 0.153693] | 1 |
| B | T2 | M3-trigger-gate - M0 | 96 | series_rmse_difference | 100 | 0.002884 | [-0.168854, 0.162461] | 1 |
| C | T3 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.329991 | [-0.353405, -0.307191] | 0 |
| C | T3 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.355294 | [-0.378700, -0.332904] | 0 |
| C | T4 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.701167 | [-0.730879, -0.672090] | 0 |
| C | T4 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.830103 | [-0.855141, -0.805544] | 0 |
| C | T6 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.329965 | [-0.352269, -0.308726] | 0 |
| C | T6 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.170549 | [-0.187279, -0.154677] | 0 |
| D | T0 | M3-trigger-gate - M3-constant-gate | 96 | series_rmse_difference | 200 | 0.005109 | [0.004305, 0.005949] | 0 |
| D | T2 | M3-trigger-gate - M3-constant-gate | 96 | series_rmse_difference | 100 | 0.007934 | [-0.051814, 0.066186] | 1 |
| D | T3 | M3-trigger-gate - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.013038 | [-0.018209, -0.007845] | 0 |
| D | T4 | M3-trigger-gate - M3-constant-gate | 96 | series_rmse_difference | 100 | -0.004188 | [-0.011826, 0.003136] | 1 |
| D | T6 | M3-trigger-gate - M3-constant-gate | 96 | series_rmse_difference | 100 | 0.022899 | [0.018965, 0.026550] | 0 |
| D | T7 | M3-trigger-gate - M3-constant-gate | 96 | series_rmse_difference | 100 | 0.014787 | [0.011071, 0.018547] | 0 |
| D | T8 | M3-trigger-gate - M3-constant-gate | 96 | series_rmse_difference | 100 | 0.015058 | [-0.001666, 0.031294] | 0.88 |
| D | T0 | M3-trigger-gate - M0 | 96 | series_rmse_difference | 200 | -0.442890 | [-0.463935, -0.421964] | 0 |
| D | T2 | M3-trigger-gate - M0 | 96 | series_rmse_difference | 100 | 0.002884 | [-0.158368, 0.159292] | 1 |
| D | T7 | M3-trigger-gate - M0 | 96 | series_rmse_difference | 100 | -1.341458 | [-1.447127, -1.239293] | 0 |
| D | T8 | M3-trigger-gate - M0 | 96 | series_rmse_difference | 100 | 0.074949 | [0.036585, 0.112794] | 0.004 |
| E | T7 | M1 - M0 | 96 | series_rmse_difference | 100 | -0.819956 | [-0.907606, -0.731831] | 0 |
| E | T7 | M2 - M0 | 96 | series_rmse_difference | 100 | -1.353241 | [-1.459498, -1.249560] | 0 |
| E | T7 | M3-trigger-gate - M0 | 96 | series_rmse_difference | 100 | -1.341458 | [-1.445087, -1.237861] | 0 |
| F | T1 | M1 - M0 | 96 | series_rmse_difference | 100 | -0.265156 | [-0.297731, -0.233622] | 0 |
| F | T1 | DLinear - M0 | 96 | series_rmse_difference | 100 | -0.256387 | [-0.286968, -0.226375] | 0 |
| F | T1 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.091793 | [-0.108145, -0.075854] | 0 |
| F | T1 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.100563 | [-0.117382, -0.084217] | 0 |
| F | T4 | M2 - M0 | 96 | series_rmse_difference | 100 | -1.403721 | [-1.451882, -1.354977] | 0 |
| F | T4 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.701167 | [-0.731559, -0.671645] | 0 |
| F | T4 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.830103 | [-0.854687, -0.805333] | 0 |
| F | T6 | M2 - M0 | 96 | series_rmse_difference | 100 | -1.933862 | [-1.971492, -1.896822] | 0 |
| F | T6 | M2 - M1 | 96 | series_rmse_difference | 100 | -0.329965 | [-0.352113, -0.308265] | 0 |
| F | T6 | M2 - DLinear | 96 | series_rmse_difference | 100 | -0.170549 | [-0.186636, -0.154664] | 0 |
| G | T8 | M1 - M0 | 96 | series_rmse_difference | 100 | 0.152793 | [0.097769, 0.206538] | 0 |
| G | T8 | DLinear - M0 | 96 | series_rmse_difference | 100 | 0.232729 | [0.165512, 0.300757] | 0 |
| G | T8 | M2 - M0 | 96 | series_rmse_difference | 100 | 0.087818 | [0.051351, 0.125629] | 0 |
| G | T8 | M3-trigger-gate - M0 | 96 | series_rmse_difference | 100 | 0.074949 | [0.037269, 0.112795] | 0 |
| H | T5 | M0 - SeasonalNaive | 96 | series_rmse_difference | 200 | 0.527966 | [0.507914, 0.548487] | 0 |
| H | T5 | M2 - SeasonalNaive | 96 | series_rmse_difference | 200 | -0.410490 | [-0.416432, -0.404260] | 0 |
| H | T5 | M3-trigger-gate - SeasonalNaive | 96 | series_rmse_difference | 200 | -0.400041 | [-0.406768, -0.393433] | 0 |
| I | T4 | M3-trigger-gate - M3-hidden-only | 96 | series_rmse_difference | 100 | 0.202654 | [0.185512, 0.220582] | 0 |
| I | T4 | M3-trigger-gate - M3-no-state-feature | 96 | series_rmse_difference | 100 | 0.264375 | [0.244314, 0.285259] | 0 |

## Detector Audit

| Mechanism | true label | origins | detector stable | detector change | change rate |
|---|---|---:|---:|---:|---:|
| continuing_trend | visible_change | 1300 | 894 | 406 | 0.3123 |
| future_jump | stable | 1200 | 813 | 387 | 0.3225 |
| future_jump | unseen_change | 100 | 65 | 35 | 0.3500 |
| random_walk | stable | 1300 | 900 | 400 | 0.3077 |
| seasonal_change | stable | 395 | 266 | 129 | 0.3266 |
| seasonal_change | visible_change | 905 | 707 | 198 | 0.2188 |
| stable | stable | 2600 | 1763 | 837 | 0.3219 |
| stable_season | stable | 2600 | 1764 | 836 | 0.3215 |
| trend_break | stable | 395 | 283 | 112 | 0.2835 |
| trend_break | visible_change | 905 | 474 | 431 | 0.4762 |
| variance_shift | stable | 395 | 280 | 115 | 0.2911 |
| variance_shift | visible_change | 905 | 600 | 305 | 0.3370 |
| visible_level_shift | stable | 395 | 289 | 106 | 0.2684 |
| visible_level_shift | visible_change | 905 | 494 | 411 | 0.4541 |
