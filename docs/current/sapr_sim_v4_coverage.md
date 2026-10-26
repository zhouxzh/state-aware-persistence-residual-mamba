# SAPR Sim V1 Coverage

Passed: `False`

| Mechanism | true stable | true visible | true unseen | detector stable | detector change | passed |
|---|---:|---:|---:|---:|---:|---|
| stable | 3400 | 0 | 0 | 3385 | 15 | False |
| visible_level_shift | 795 | 905 | 0 | 1687 | 13 | False |
| future_jump | 1600 | 0 | 100 | 441 | 1259 | True |
| continuing_trend | 0 | 1700 | 0 | 1691 | 9 | False |
| trend_break | 795 | 905 | 0 | 1693 | 7 | False |
| stable_season | 3400 | 0 | 0 | 3371 | 29 | False |
| seasonal_change | 795 | 905 | 0 | 973 | 727 | True |
| variance_shift | 795 | 905 | 0 | 1662 | 38 | False |
| random_walk | 1700 | 0 | 0 | 439 | 1261 | True |
