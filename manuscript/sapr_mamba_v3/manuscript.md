# SAPR-Mamba V3: State-Aware Persistence-Residual Forecasting

> Automatically generated evidence-bound draft. It is not submission-ready until all required sections, citations, declarations, and author approvals are present.

## Abstract

[Generated only after V3 analysis and external validation complete.]

## Methods

The V3 study follows the frozen protocol in `configs/sapr_mamba_v3/protocol.lock.json`. V2 is retained as development evidence and is not pooled with V3. [claim:C001] [evidence:E001]

## Results

### Synthetic confirmation

| Comparison | Horizon | Independent sequences | Estimate | 95% CI | Holm p |
|---|---:|---:|---:|---:|---:|
| H1_M2_minus_M1 | 12 | 1500 | -0.0144 | [-0.0171, -0.0118] | 0.0000 |
| H1_M2_minus_M1 | 24 | 1500 | -0.0150 | [-0.0177, -0.0124] | 0.0000 |
| H1_M2_minus_M1 | 48 | 1500 | -0.0158 | [-0.0180, -0.0136] | 0.0000 |
| H1_M2_minus_M1 | 96 | 1500 | -0.0225 | [-0.0247, -0.0203] | 0.0000 |
| H2_M3_minus_M2 | 12 | 1500 | -0.0011 | [-0.0015, -0.0006] | 0.0000 |
| H2_M3_minus_M2 | 24 | 1500 | -0.0015 | [-0.0019, -0.0011] | 0.0000 |
| H2_M3_minus_M2 | 48 | 1500 | -0.0015 | [-0.0018, -0.0012] | 0.0000 |
| H2_M3_minus_M2 | 96 | 1500 | -0.0016 | [-0.0019, -0.0014] | 0.0000 |
| stable_safety_M3_over_M0_minus_1 | 12 | 200 | -0.2449 | [-0.2575, -0.2321] | 0.0000 |
| stable_safety_M3_over_M0_minus_1 | 24 | 200 | -0.2991 | [-0.3129, -0.2853] | 0.0000 |
| stable_safety_M3_over_M0_minus_1 | 48 | 200 | -0.3098 | [-0.3221, -0.2981] | 0.0000 |
| stable_safety_M3_over_M0_minus_1 | 96 | 200 | -0.3093 | [-0.3215, -0.2973] | 0.0000 |

Evidence: `docs/analysis/sapr_mamba_v3/synthetic_primary_comparisons.csv` (SHA-256 `ca61b78c12eff186ec2ced662023ffe697dced0115e21cbd59a0516bc3f259c3`).

### Source-stratified real-panel results

| Source | Comparison | Horizon | n sequences | Estimate | 95% CI | Holm p | Status |
|---|---|---:|---:|---:|---:|---:|---|
| beijing_air_quality | H1_M2_minus_M1 | 3 | 12 | -0.2116 | [-0.6486, 0.2011] | 1.0000 | complete |
| beijing_air_quality | H2_M3_minus_M2 | 3 | 12 | 0.0362 | [-0.2009, 0.2681] | 1.0000 | complete |
| beijing_air_quality | stable_safety_M3_over_M0_minus_1 | 3 | 0 | nan | [nan, nan] | nan | no_eligible_state_units |
| beijing_air_quality | H1_M2_minus_M1 | 6 | 12 | -0.5117 | [-1.0146, -0.0363] | 0.9632 | complete |
| beijing_air_quality | H2_M3_minus_M2 | 6 | 12 | -0.0197 | [-0.3705, 0.2718] | 1.0000 | complete |
| beijing_air_quality | stable_safety_M3_over_M0_minus_1 | 6 | 0 | nan | [nan, nan] | nan | no_eligible_state_units |
| beijing_air_quality | H1_M2_minus_M1 | 12 | 12 | -0.7101 | [-1.9489, 0.5808] | 1.0000 | complete |
| beijing_air_quality | H2_M3_minus_M2 | 12 | 12 | -0.0601 | [-0.5244, 0.2914] | 1.0000 | complete |
| beijing_air_quality | stable_safety_M3_over_M0_minus_1 | 12 | 0 | nan | [nan, nan] | nan | no_eligible_state_units |
| beijing_air_quality | H1_M2_minus_M1 | 24 | 12 | 0.5404 | [-0.9383, 2.0546] | 1.0000 | complete |
| beijing_air_quality | H2_M3_minus_M2 | 24 | 12 | -0.1302 | [-0.6719, 0.3125] | 1.0000 | complete |
| beijing_air_quality | stable_safety_M3_over_M0_minus_1 | 24 | 0 | nan | [nan, nan] | nan | no_eligible_state_units |
| electricity | H1_M2_minus_M1 | 12 | 100 | 4.5202 | [2.4036, 7.0620] | 0.0000 | complete |
| electricity | H2_M3_minus_M2 | 12 | 100 | -0.2604 | [-0.4906, -0.0397] | 0.4756 | complete |
| electricity | stable_safety_M3_over_M0_minus_1 | 12 | 6 | -0.1323 | [-0.3049, 0.1110] | 1.0000 | limited_stable_state_coverage |
| electricity | H1_M2_minus_M1 | 24 | 100 | 9.0525 | [5.1125, 14.0102] | 0.0000 | complete |
| electricity | H2_M3_minus_M2 | 24 | 100 | -0.4296 | [-0.9475, -0.0649] | 0.4320 | complete |
| electricity | stable_safety_M3_over_M0_minus_1 | 24 | 6 | -0.2332 | [-0.4281, 0.0419] | 1.0000 | limited_stable_state_coverage |
| electricity | H1_M2_minus_M1 | 48 | 100 | 9.6057 | [5.2127, 16.3278] | 0.0000 | complete |
| electricity | H2_M3_minus_M2 | 48 | 100 | -0.6855 | [-1.1312, -0.2340] | 0.1584 | complete |
| electricity | stable_safety_M3_over_M0_minus_1 | 48 | 6 | -0.2959 | [-0.5421, -0.0252] | 0.9632 | limited_stable_state_coverage |
| electricity | H1_M2_minus_M1 | 96 | 100 | 7.5253 | [4.0380, 12.3936] | 0.0000 | complete |
| electricity | H2_M3_minus_M2 | 96 | 100 | -0.4227 | [-0.7028, -0.1310] | 0.1400 | complete |
| electricity | stable_safety_M3_over_M0_minus_1 | 96 | 6 | -0.3289 | [-0.5166, -0.1211] | 0.0792 | limited_stable_state_coverage |
| ett | H1_M2_minus_M1 | 3 | 2 | 0.0359 | [0.0284, 0.0434] | 0.0000 | complete |
| ett | H2_M3_minus_M2 | 3 | 2 | 0.0384 | [0.0126, 0.0643] | 0.0000 | complete |
| ett | stable_safety_M3_over_M0_minus_1 | 3 | 0 | nan | [nan, nan] | nan | no_eligible_state_units |
| ett | H1_M2_minus_M1 | 6 | 2 | 0.0936 | [0.0000, 0.1872] | 0.0000 | complete |
| ett | H2_M3_minus_M2 | 6 | 2 | 0.0486 | [0.0077, 0.0895] | 0.0000 | complete |
| ett | stable_safety_M3_over_M0_minus_1 | 6 | 0 | nan | [nan, nan] | nan | no_eligible_state_units |
| ett | H1_M2_minus_M1 | 12 | 4 | 0.1694 | [0.0144, 0.3991] | 1.0000 | complete |
| ett | H2_M3_minus_M2 | 12 | 4 | -0.0010 | [-0.0521, 0.0415] | 1.0000 | complete |
| ett | stable_safety_M3_over_M0_minus_1 | 12 | 1 | -0.0058 | [-0.0058, -0.0058] | 0.0000 | limited_stable_state_coverage |
| ett | H1_M2_minus_M1 | 24 | 4 | 0.3136 | [0.0449, 0.5823] | 0.2418 | complete |
| ett | H2_M3_minus_M2 | 24 | 4 | -0.0150 | [-0.0640, 0.0176] | 1.0000 | complete |
| ett | stable_safety_M3_over_M0_minus_1 | 24 | 1 | -0.6581 | [-0.6581, -0.6581] | 0.0000 | limited_stable_state_coverage |
| ett | H1_M2_minus_M1 | 48 | 2 | 0.3392 | [-0.0031, 0.6815] | 1.0000 | complete |
| ett | H2_M3_minus_M2 | 48 | 2 | -0.0335 | [-0.0586, -0.0084] | 0.0000 | complete |
| ett | stable_safety_M3_over_M0_minus_1 | 48 | 1 | -0.7793 | [-0.7793, -0.7793] | 0.0000 | limited_stable_state_coverage |
| ett | H1_M2_minus_M1 | 96 | 2 | 0.2954 | [-0.0592, 0.6499] | 1.0000 | complete |
| ett | H2_M3_minus_M2 | 96 | 2 | -0.0195 | [-0.0213, -0.0176] | 0.0000 | complete |
| ett | stable_safety_M3_over_M0_minus_1 | 96 | 1 | -0.6117 | [-0.6117, -0.6117] | 0.0000 | limited_stable_state_coverage |
| zenodo_m4 | H1_M2_minus_M1 | 3 | 100 | 26.8212 | [-15.2403, 66.6596] | 1.0000 | complete |
| zenodo_m4 | H2_M3_minus_M2 | 3 | 100 | 9.1548 | [-6.2036, 32.9211] | 1.0000 | complete |
| zenodo_m4 | stable_safety_M3_over_M0_minus_1 | 3 | 39 | 1.6265 | [-0.0795, 4.9084] | 1.0000 | limited_stable_state_coverage |
| zenodo_m4 | H1_M2_minus_M1 | 6 | 100 | 25.1557 | [-5.0758, 55.5994] | 1.0000 | complete |
| zenodo_m4 | H2_M3_minus_M2 | 6 | 100 | 14.4510 | [-2.6766, 38.0856] | 1.0000 | complete |
| zenodo_m4 | stable_safety_M3_over_M0_minus_1 | 6 | 39 | 0.0148 | [-0.0503, 0.0815] | 1.0000 | limited_stable_state_coverage |
| zenodo_m4 | H1_M2_minus_M1 | 12 | 100 | 20.0516 | [-5.1284, 44.4018] | 1.0000 | complete |
| zenodo_m4 | H2_M3_minus_M2 | 12 | 100 | 15.5584 | [-1.9085, 40.4896] | 1.0000 | complete |
| zenodo_m4 | stable_safety_M3_over_M0_minus_1 | 12 | 39 | 0.0175 | [-0.0419, 0.0743] | 1.0000 | limited_stable_state_coverage |
| zenodo_nn5 | H1_M2_minus_M1 | 1 | 100 | -0.4327 | [-0.6054, -0.2614] | 0.0000 | complete |
| zenodo_nn5 | H2_M3_minus_M2 | 1 | 100 | 0.0973 | [0.0596, 0.1354] | 0.0000 | complete |
| zenodo_nn5 | stable_safety_M3_over_M0_minus_1 | 1 | 99 | -0.2816 | [-0.3560, -0.1933] | 0.0000 | limited_stable_state_coverage |
| zenodo_nn5 | H1_M2_minus_M1 | 2 | 100 | -0.5588 | [-0.7248, -0.3962] | 0.0000 | complete |
| zenodo_nn5 | H2_M3_minus_M2 | 2 | 100 | 0.0652 | [0.0285, 0.1039] | 0.0228 | complete |
| zenodo_nn5 | stable_safety_M3_over_M0_minus_1 | 2 | 100 | -0.4483 | [-0.4957, -0.3986] | 0.0000 | complete |
| zenodo_nn5 | H1_M2_minus_M1 | 4 | 100 | -0.2938 | [-0.4293, -0.1591] | 0.0000 | complete |
| zenodo_nn5 | H2_M3_minus_M2 | 4 | 100 | 0.0349 | [0.0099, 0.0610] | 0.1428 | complete |
| zenodo_nn5 | stable_safety_M3_over_M0_minus_1 | 4 | 100 | -0.4131 | [-0.4472, -0.3788] | 0.0000 | complete |
| zenodo_nn5 | H1_M2_minus_M1 | 7 | 100 | -0.1454 | [-0.2324, -0.0610] | 0.0444 | complete |
| zenodo_nn5 | H2_M3_minus_M2 | 7 | 100 | 0.0235 | [0.0062, 0.0417] | 0.1984 | complete |
| zenodo_nn5 | stable_safety_M3_over_M0_minus_1 | 7 | 100 | -0.3503 | [-0.3790, -0.3220] | 0.0000 | complete |
| zenodo_solar | H1_M2_minus_M1 | 18 | 100 | -0.8415 | [-0.9210, -0.7725] | 0.0000 | complete |
| zenodo_solar | H2_M3_minus_M2 | 18 | 100 | -0.0699 | [-0.0808, -0.0600] | 0.0000 | complete |
| zenodo_solar | stable_safety_M3_over_M0_minus_1 | 18 | 0 | nan | [nan, nan] | nan | no_eligible_state_units |
| zenodo_solar | H1_M2_minus_M1 | 36 | 100 | -1.1163 | [-1.2541, -0.9924] | 0.0000 | complete |
| zenodo_solar | H2_M3_minus_M2 | 36 | 100 | -0.2173 | [-0.2428, -0.1928] | 0.0000 | complete |
| zenodo_solar | stable_safety_M3_over_M0_minus_1 | 36 | 0 | nan | [nan, nan] | nan | no_eligible_state_units |
| zenodo_solar | H1_M2_minus_M1 | 72 | 100 | -0.2291 | [-0.2838, -0.1759] | 0.0000 | complete |
| zenodo_solar | H2_M3_minus_M2 | 72 | 100 | -0.0377 | [-0.0490, -0.0270] | 0.0000 | complete |
| zenodo_solar | stable_safety_M3_over_M0_minus_1 | 72 | 0 | nan | [nan, nan] | nan | no_eligible_state_units |
| zenodo_solar | H1_M2_minus_M1 | 144 | 100 | -0.1416 | [-0.1839, -0.0995] | 0.0000 | complete |
| zenodo_solar | H2_M3_minus_M2 | 144 | 100 | -0.0181 | [-0.0276, -0.0091] | 0.0000 | complete |
| zenodo_solar | stable_safety_M3_over_M0_minus_1 | 144 | 0 | nan | [nan, nan] | nan | no_eligible_state_units |
| zenodo_tourism | H1_M2_minus_M1 | 3 | 100 | 866.3137 | [527.9068, 1280.0563] | 0.0000 | complete |
| zenodo_tourism | H2_M3_minus_M2 | 3 | 100 | -12.7389 | [-38.0668, 8.3471] | 1.0000 | complete |
| zenodo_tourism | stable_safety_M3_over_M0_minus_1 | 3 | 53 | -0.2091 | [-0.3054, -0.1059] | 0.0078 | limited_stable_state_coverage |
| zenodo_tourism | H1_M2_minus_M1 | 6 | 100 | 882.6099 | [548.5075, 1293.2631] | 0.0000 | complete |
| zenodo_tourism | H2_M3_minus_M2 | 6 | 100 | 14.5804 | [-40.2910, 83.0402] | 1.0000 | complete |
| zenodo_tourism | stable_safety_M3_over_M0_minus_1 | 6 | 53 | -0.2500 | [-0.3432, -0.1481] | 0.0000 | limited_stable_state_coverage |
| zenodo_tourism | H1_M2_minus_M1 | 12 | 100 | 655.7222 | [383.2621, 976.4688] | 0.0000 | complete |
| zenodo_tourism | H2_M3_minus_M2 | 12 | 100 | 20.6522 | [-30.9377, 97.5329] | 1.0000 | complete |
| zenodo_tourism | stable_safety_M3_over_M0_minus_1 | 12 | 53 | -0.3402 | [-0.4109, -0.2641] | 0.0000 | limited_stable_state_coverage |

Evidence: `docs/analysis/sapr_mamba_v3/real_primary_comparisons.csv` (SHA-256 `14870af005af737c1e7cba8524541ee78fe8bd1ad1d4de02606c20712f34b301`).

### External holdout paired comparisons

The declared external holdout clusters are reported separately from the base source pool; no universal cross-domain claim is inferred. [claim:C_EXT_HOLDOUT] [evidence:E002]

| Source cluster | Comparison | Horizon | n | Estimate | 95% CI | Holm p | Status |
|---|---|---:|---:|---:|---:|---:|---|
| zenodo_solar | H1_M2_minus_M1 | 18 | 100 | -0.8415 | [-0.9210, -0.7725] | 0.0000 | complete |
| zenodo_solar | H2_M3_minus_M2 | 18 | 100 | -0.0699 | [-0.0808, -0.0600] | 0.0000 | complete |
| zenodo_solar | stable_safety_M3_over_M0_minus_1 | 18 | 0 | nan | [nan, nan] | nan | no_eligible_state_units |
| zenodo_solar | H1_M2_minus_M1 | 36 | 100 | -1.1163 | [-1.2541, -0.9924] | 0.0000 | complete |
| zenodo_solar | H2_M3_minus_M2 | 36 | 100 | -0.2173 | [-0.2428, -0.1928] | 0.0000 | complete |
| zenodo_solar | stable_safety_M3_over_M0_minus_1 | 36 | 0 | nan | [nan, nan] | nan | no_eligible_state_units |
| zenodo_solar | H1_M2_minus_M1 | 72 | 100 | -0.2291 | [-0.2838, -0.1759] | 0.0000 | complete |
| zenodo_solar | H2_M3_minus_M2 | 72 | 100 | -0.0377 | [-0.0490, -0.0270] | 0.0000 | complete |
| zenodo_solar | stable_safety_M3_over_M0_minus_1 | 72 | 0 | nan | [nan, nan] | nan | no_eligible_state_units |
| zenodo_solar | H1_M2_minus_M1 | 144 | 100 | -0.1416 | [-0.1839, -0.0995] | 0.0000 | complete |
| zenodo_solar | H2_M3_minus_M2 | 144 | 100 | -0.0181 | [-0.0276, -0.0091] | 0.0000 | complete |
| zenodo_solar | stable_safety_M3_over_M0_minus_1 | 144 | 0 | nan | [nan, nan] | nan | no_eligible_state_units |
| zenodo_tourism | H1_M2_minus_M1 | 3 | 100 | 866.3137 | [527.9068, 1280.0563] | 0.0000 | complete |
| zenodo_tourism | H2_M3_minus_M2 | 3 | 100 | -12.7389 | [-38.0668, 8.3471] | 1.0000 | complete |
| zenodo_tourism | stable_safety_M3_over_M0_minus_1 | 3 | 53 | -0.2091 | [-0.3054, -0.1059] | 0.0078 | limited_stable_state_coverage |
| zenodo_tourism | H1_M2_minus_M1 | 6 | 100 | 882.6099 | [548.5075, 1293.2631] | 0.0000 | complete |
| zenodo_tourism | H2_M3_minus_M2 | 6 | 100 | 14.5804 | [-40.2910, 83.0402] | 1.0000 | complete |
| zenodo_tourism | stable_safety_M3_over_M0_minus_1 | 6 | 53 | -0.2500 | [-0.3432, -0.1481] | 0.0000 | limited_stable_state_coverage |
| zenodo_tourism | H1_M2_minus_M1 | 12 | 100 | 655.7222 | [383.2621, 976.4688] | 0.0000 | complete |
| zenodo_tourism | H2_M3_minus_M2 | 12 | 100 | 20.6522 | [-30.9377, 97.5329] | 1.0000 | complete |
| zenodo_tourism | stable_safety_M3_over_M0_minus_1 | 12 | 53 | -0.3402 | [-0.4109, -0.2641] | 0.0000 | limited_stable_state_coverage |

Evidence: `docs/analysis/sapr_mamba_v3/external_holdout_primary_comparisons.csv` (SHA-256 `a78bb14d4e6737f906aafa59078f041fbbf2f1331e87e39d16777f6df05cfe38`).

### External source and state coverage

| Panel | Source cluster | Series | Stable test series | Change test series | External holdout | Stable endpoint |
|---|---|---:|---:|---:|---|---|
| solar_10min | zenodo_solar | 100 | 6 | 100 | true | false |
| tourism_monthly | zenodo_tourism | 100 | 99 | 31 | true | true |
| nn5_daily | zenodo_nn5 | 100 | 100 | 38 | false | true |
| m4_monthly | zenodo_m4 | 100 | 84 | 46 | false | true |

Evidence: `data/sapr_mamba_v3/real/source_extensions/v3.1/prepared_manifest.json` (SHA-256 `efbe478eaa090c9c2e2a92f283f4760583b2f4b01bd906992601b8cb3b39b7ed`).

### Independent recomputation

Real-task metric recomputation status: **verified** (950 tasks; 0 failures).
Evidence: `docs/analysis/sapr_mamba_v3/real_verification_manifest.json`.

## Limitations

- Stable-state safety was not fully estimable for 25 of 28 source-horizon rows (10 with no eligible stable-state units and 15 with incomplete stable-state coverage). [claim:C_LIMIT_STABLE] [evidence:E005]
- Statistical baseline candidate fitting recorded 484 retained failure rows; their fallback behavior must be considered when comparing contextual baselines. [claim:C_LIMIT_STAT] [evidence:E006]
- V2 is a development baseline and is not pooled into V3 confirmation estimates.
- State coverage, independent source-cluster count, and external-holdout status must be reported from V3 manifests.

## Declarations (unresolved placeholders)

Authorship, funding, conflicts, ethics/data-use declarations, and AI-use disclosure are not inferred by automation and must not be fabricated. [claim:C002] [evidence:E001]

## Software and Procedural Guidance

Evidence binding, limitation disclosure, and manuscript audit structure were informed by Scientific Agent Skills: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents* (arXiv:2609.00065v2; doi:10.48550/arXiv.2609.00065).
