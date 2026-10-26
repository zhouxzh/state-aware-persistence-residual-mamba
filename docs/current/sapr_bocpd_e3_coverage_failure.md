# BOCPD E3 Coverage Failure

**Status:** immutable pre-training failure record.

E3 used the corrected recent-run BOCPD posterior with seasonal-residual input.
The detector did not meet its frozen paired discrimination gate: T4 had a
visible-minus-stable activation of -0.0161 and T6 had 0.0163, below the 0.10
minimum. No E3 model was trained. Its data, configuration lock, and coverage
audit remain preserved without modification.
