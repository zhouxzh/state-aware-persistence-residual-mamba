from __future__ import annotations

import warnings

import pytest

from utils.sapr_mamba.statistical import _fit_without_numerical_warnings


def test_numerical_warning_is_a_statistical_fit_failure() -> None:
    with pytest.raises(RuntimeError, match="warning"):
        _fit_without_numerical_warnings(
            lambda: (warnings.warn("unstable", RuntimeWarning), object())[1]
        )
