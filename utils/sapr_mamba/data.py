"""Leakage-safe windows and chronological panel preparation for SAPR-Mamba."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from .features import FEATURE_NAMES, causal_features, state_label


@dataclass(frozen=True)
class SeriesInfo:
    series_id: str
    period: int
    train_end: int
    valid_end: int
    source: str
    mechanism: str = "real"
    strength: float = float("nan")
    change_point: int = -1


def split_points(length: int, fractions: tuple[float, float, float] = (0.6, 0.2, 0.2)) -> tuple[int, int]:
    if len(fractions) != 3 or not np.isclose(sum(fractions), 1.0):
        raise ValueError("split fractions must sum to one")
    train_end = int(length * fractions[0])
    valid_end = train_end + int(length * fractions[1])
    if train_end < 2 or valid_end >= length:
        raise ValueError("series is too short for chronological split")
    return train_end, valid_end


def causal_forward_fill(values: np.ndarray, maximum_gap: int) -> tuple[np.ndarray, np.ndarray]:
    """Forward-fill only short gaps and return an eligibility mask for all positions."""
    output = np.asarray(values, dtype=np.float64).copy()
    eligible = np.isfinite(output)
    index = 0
    while index < len(output):
        if np.isfinite(output[index]):
            index += 1
            continue
        start = index
        while index < len(output) and not np.isfinite(output[index]):
            index += 1
        end = index
        gap = end - start
        if start > 0 and gap <= maximum_gap and np.isfinite(output[start - 1]):
            output[start:end] = output[start - 1]
            eligible[start:end] = True
    return output.astype(np.float32), eligible


def _window_is_eligible(eligible: np.ndarray, start: int, end: int) -> bool:
    return start >= 0 and end <= eligible.size and bool(eligible[start:end].all())


class WindowDataset:
    """Lazy origin windows. Target bounds are enforced when origins are constructed."""

    def __init__(
        self,
        sequences: np.ndarray,
        infos: list[SeriesInfo],
        origins: np.ndarray,
        input_length: int,
        horizon: int,
        epsilon: float,
        change_threshold: float,
        eligibility: np.ndarray | None = None,
        feature_permutation_seed: int | None = None,
        cached_features: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None,
    ) -> None:
        if sequences.ndim != 2 or len(sequences) != len(infos):
            raise ValueError("sequences must be [series, time] aligned with series info")
        self.sequences = np.asarray(sequences, dtype=np.float32)
        self.infos = infos
        self.origins = np.asarray(origins, dtype=np.int64)
        self.input_length = int(input_length)
        self.horizon = int(horizon)
        self.epsilon = float(epsilon)
        self.change_threshold = float(change_threshold)
        self.eligibility = np.ones_like(self.sequences, dtype=bool) if eligibility is None else eligibility.astype(bool)
        if self.origins.ndim != 2 or self.origins.shape[1] != 2:
            raise ValueError("origins must have [series_index, origin] rows")
        # Features, labels, and audit scores are deterministic functions of each
        # already-valid causal origin. Cache them once so repeated sampling does
        # not recompute robust statistics or change the model input.
        if cached_features is None:
            self.audit_phi = np.empty((len(self.origins), len(FEATURE_NAMES)), dtype=np.float32)
            self.audit_state = np.empty(len(self.origins), dtype=np.int8)
            self.audit_change_score = np.empty(len(self.origins), dtype=np.float32)
            for row_index in range(len(self.origins)):
                phi, label, score = self._compute_feature(row_index)
                self.audit_phi[row_index] = phi
                self.audit_state[row_index] = 1 if label == "change" else 0
                self.audit_change_score[row_index] = score
        else:
            self.audit_phi, self.audit_state, self.audit_change_score = cached_features
            if (
                self.audit_phi.shape != (len(self.origins), len(FEATURE_NAMES))
                or self.audit_state.shape != (len(self.origins),)
                or self.audit_change_score.shape != (len(self.origins),)
            ):
                raise ValueError("Cached SAPR origin features do not match the current origin matrix")
        self.feature_permutation = None
        if feature_permutation_seed is not None:
            rng = np.random.default_rng(int(feature_permutation_seed))
            self.feature_permutation = rng.permutation(len(self.origins))

    def __len__(self) -> int:
        return len(self.origins)

    def cached_features(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.audit_phi, self.audit_state, self.audit_change_score

    def _compute_feature(self, row_index: int) -> tuple[np.ndarray, str, float]:
        series_index, origin = self.origins[row_index]
        info = self.infos[int(series_index)]
        history = self.sequences[series_index, origin - self.input_length:origin]
        phi = causal_features(history, info.period, self.epsilon)
        label, score = state_label(phi, self.change_threshold)
        return phi, label, score

    def __getitem__(self, row_index: int) -> dict:
        series_index, origin = self.origins[row_index]
        start = int(origin) - self.input_length
        end = int(origin) + self.horizon
        if not _window_is_eligible(self.eligibility[int(series_index)], start, end):
            raise RuntimeError("ineligible window reached dataset; origin construction is invalid")
        x = self.sequences[series_index, start:origin]
        y = self.sequences[series_index, origin:end]
        phi = self.audit_phi[row_index]
        state = self.audit_state[row_index]
        score = self.audit_change_score[row_index]
        if self.feature_permutation is not None:
            phi = self.audit_phi[int(self.feature_permutation[row_index])]
        return {
            "x": x.astype(np.float32),
            "y": y.astype(np.float32),
            "phi": phi.astype(np.float32),
            "state": np.int8(state),
            "change_score": np.float32(score),
            "series_index": np.int64(series_index),
            "origin": np.int64(origin),
        }


def make_origins(
    sequences: np.ndarray,
    infos: list[SeriesInfo],
    input_length: int,
    horizon: int,
    split: str,
    stride: int,
    eligibility: np.ndarray | None = None,
) -> np.ndarray:
    """Construct only origins whose whole target is inside the requested range."""
    if split not in {"train", "validation", "test", "all"}:
        raise ValueError(f"Unknown split: {split}")
    rows = []
    valid_mask = np.ones_like(sequences, dtype=bool) if eligibility is None else eligibility
    for series_index, info in enumerate(infos):
        length = sequences.shape[1]
        if split == "train":
            lower, upper = input_length, info.train_end
        elif split == "validation":
            lower, upper = max(input_length, info.train_end), info.valid_end
        elif split == "test":
            lower, upper = max(input_length, info.valid_end), length
        else:
            lower, upper = input_length, length
        for origin in range(lower, upper - horizon + 1, max(1, stride)):
            if _window_is_eligible(valid_mask[series_index], origin - input_length, origin + horizon):
                rows.append((series_index, origin))
    if not rows:
        raise ValueError(f"No eligible {split} origins for L={input_length}, H={horizon}")
    return np.asarray(rows, dtype=np.int64)


def cap_origins_per_series(origins: np.ndarray, maximum_per_series: int) -> np.ndarray:
    """Evenly retain a frozen maximum number of already valid origins per series."""
    if maximum_per_series < 1:
        raise ValueError("maximum_per_series must be positive")
    rows = []
    for series_index in np.unique(origins[:, 0]):
        selected = origins[origins[:, 0] == series_index]
        if len(selected) > maximum_per_series:
            indices = np.linspace(0, len(selected) - 1, maximum_per_series, dtype=int)
            selected = selected[indices]
        rows.append(selected)
    return np.concatenate(rows, axis=0)


def synthetic_series_info(roster: list[dict], sequence_length: int, period: int) -> list[SeriesInfo]:
    train_end, valid_end = split_points(sequence_length)
    return [
        SeriesInfo(
            series_id=str(item["series_id"]),
            period=int(period),
            train_end=train_end,
            valid_end=valid_end,
            source="synthetic",
            mechanism=str(item["mechanism"]),
            strength=float(item["strength"]),
            change_point=int(item["change_point"]),
        )
        for item in roster
    ]


def stable_series_key(identifier: str) -> str:
    return hashlib.sha256(identifier.encode("utf-8")).hexdigest()
