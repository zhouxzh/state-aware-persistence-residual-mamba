# BOCPD E2 Coverage Failure

**Status:** immutable pre-training failure record.

E2 used the corrected recent-run BOCPD posterior with first-difference input.
The detector was no longer constant, but its trend-break visible-minus-stable
activation was -0.0215, below the frozen 0.10 requirement. Seasonal change
passed its paired discrimination check (0.1831).

The E2 protocol also requested a pairwise lift for continuing trend, which has
no stable origin stratum by design and is therefore not estimable. E3-E5 retain
T3 in their complete outcome matrices but restrict their pre-training pairwise
detector gate to estimable T4 and T6 mechanisms. No E2 model was trained and no
E2 configuration or data artifact was changed.
