"""SAPR-Mamba models isolated from the historical financial model namespace."""

from __future__ import annotations

import torch
from torch import nn


def _normalize_history(x: torch.Tensor, epsilon: float = 1e-6) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    baseline = x[:, -1:]
    scale = x.std(dim=1, keepdim=True, unbiased=False).clamp_min(epsilon)
    return (x - baseline) / scale, baseline, scale


class PersistenceModel(nn.Module):
    def __init__(self, horizon: int) -> None:
        super().__init__()
        self.horizon = int(horizon)

    def forward(self, x: torch.Tensor, phi: torch.Tensor) -> dict[str, torch.Tensor]:
        baseline = x[:, -1:].expand(-1, self.horizon)
        zeros = torch.zeros_like(baseline)
        return {"forecast": baseline, "residual": zeros, "gate": zeros + 1.0, "embedding": zeros[:, :1]}


class LinearResidualModel(nn.Module):
    def __init__(self, horizon: int, phi_dim: int, history_projection: int = 96) -> None:
        super().__init__()
        self.horizon = int(horizon)
        self.history_projection = int(history_projection)
        self.network = nn.Linear(self.history_projection + int(phi_dim), self.horizon)

    def forward(self, x: torch.Tensor, phi: torch.Tensor) -> dict[str, torch.Tensor]:
        normalized, baseline, scale = _normalize_history(x)
        differences = normalized[:, 1:] - normalized[:, :-1]
        if differences.size(1) < self.history_projection:
            differences = nn.functional.pad(differences, (self.history_projection - differences.size(1), 0))
        else:
            differences = differences[:, -self.history_projection:]
        residual = self.network(torch.cat((differences, phi), dim=1)) * scale
        forecast = baseline + residual
        return {"forecast": forecast, "residual": residual, "gate": torch.ones_like(residual), "embedding": phi}


class SeasonalNaiveModel(nn.Module):
    """Causal seasonal-naive path, included only as a contextual baseline."""

    def __init__(self, horizon: int, period: int) -> None:
        super().__init__()
        self.horizon = int(horizon)
        self.period = int(period)

    def forward(self, x: torch.Tensor, phi: torch.Tensor) -> dict[str, torch.Tensor]:
        if x.size(1) < self.period:
            raise ValueError("seasonal-naive requires an input at least one period long")
        indices = torch.arange(self.horizon, device=x.device) % self.period
        forecast = x[:, -self.period:].index_select(1, indices)
        baseline = x[:, -1:].expand_as(forecast)
        return {"forecast": forecast, "residual": forecast - baseline, "gate": torch.ones_like(forecast), "embedding": phi}


class DriftModel(nn.Module):
    """Causal drift forecast, anchored at the most recent value."""

    def __init__(self, horizon: int) -> None:
        super().__init__()
        self.horizon = int(horizon)

    def forward(self, x: torch.Tensor, phi: torch.Tensor) -> dict[str, torch.Tensor]:
        steps = torch.arange(1, self.horizon + 1, device=x.device, dtype=x.dtype).unsqueeze(0)
        slope = (x[:, -1:] - x[:, :1]) / max(x.size(1) - 1, 1)
        forecast = x[:, -1:] + slope * steps
        return {"forecast": forecast, "residual": forecast - x[:, -1:], "gate": torch.ones_like(forecast), "embedding": phi}


class DLinearResidualModel(nn.Module):
    """Last-value-anchored DLinear contextual baseline with fixed moving-average decomposition."""

    def __init__(self, input_length: int, horizon: int, kernel_size: int) -> None:
        super().__init__()
        self.input_length = int(input_length)
        self.horizon = int(horizon)
        self.kernel_size = int(kernel_size)
        self.trend_head = nn.Linear(self.input_length, self.horizon)
        self.seasonal_head = nn.Linear(self.input_length, self.horizon)

    def forward(self, x: torch.Tensor, phi: torch.Tensor) -> dict[str, torch.Tensor]:
        normalized, baseline, scale = _normalize_history(x)
        padding = (self.kernel_size - 1) // 2
        padded = nn.functional.pad(normalized.unsqueeze(1), (padding, padding), mode="replicate")
        trend = nn.functional.avg_pool1d(padded, self.kernel_size, stride=1).squeeze(1)
        seasonal = normalized - trend
        residual = (self.trend_head(trend) + self.seasonal_head(seasonal)) * scale
        forecast = baseline + residual
        return {"forecast": forecast, "residual": residual, "gate": torch.ones_like(residual), "embedding": phi}


class MambaResidualModel(nn.Module):
    def __init__(
        self,
        horizon: int,
        phi_dim: int,
        d_model: int,
        d_state: int,
        d_conv: int,
        expand: int,
        layers: int,
        dropout: float,
        gated: bool,
    ) -> None:
        super().__init__()
        try:
            from mamba_ssm import Mamba
        except ImportError as exc:
            raise RuntimeError("mamba-ssm is required for M2/M3; install it in the mamba Conda environment") from exc
        self.horizon = int(horizon)
        self.gated = bool(gated)
        self.input_projection = nn.Linear(1 + int(phi_dim), int(d_model))
        self.blocks = nn.ModuleList(
            [Mamba(d_model=int(d_model), d_state=int(d_state), d_conv=int(d_conv), expand=int(expand)) for _ in range(int(layers))]
        )
        self.norms = nn.ModuleList([nn.LayerNorm(int(d_model)) for _ in range(int(layers))])
        self.dropout = nn.Dropout(float(dropout))
        self.residual_head = nn.Linear(int(d_model), self.horizon)
        self.gate_phi = nn.Linear(int(phi_dim), 1)
        self.gate_hidden = nn.Linear(int(d_model), 1)

    def forward(self, x: torch.Tensor, phi: torch.Tensor) -> dict[str, torch.Tensor]:
        normalized, baseline, scale = _normalize_history(x)
        feature_tokens = phi.unsqueeze(1).expand(-1, normalized.size(1), -1)
        encoded = self.input_projection(torch.cat((normalized.unsqueeze(-1), feature_tokens), dim=-1))
        for block, norm in zip(self.blocks, self.norms):
            encoded = norm(encoded + self.dropout(block(encoded)))
        embedding = encoded[:, -1]
        residual = self.residual_head(embedding) * scale
        if self.gated:
            gate_scalar = torch.sigmoid(self.gate_phi(phi) + self.gate_hidden(embedding))
            gate = gate_scalar.expand(-1, self.horizon)
        else:
            gate = torch.ones_like(residual)
        forecast = baseline + gate * residual
        return {"forecast": forecast, "residual": residual, "gate": gate, "embedding": embedding}


def build_model(model_id: str, horizon: int, phi_dim: int, specification: dict, input_length: int | None = None, period: int | None = None) -> nn.Module:
    if model_id == "M0":
        return PersistenceModel(horizon)
    if model_id == "M1":
        linear = specification["linear_residual"]
        return LinearResidualModel(horizon, phi_dim, linear["history_projection"])
    if model_id == "SeasonalNaive":
        if period is None:
            raise ValueError("SeasonalNaive requires a configured period")
        return SeasonalNaiveModel(horizon, period)
    if model_id == "Drift":
        return DriftModel(horizon)
    if model_id == "DLinear":
        if input_length is None:
            raise ValueError("DLinear requires input_length")
        return DLinearResidualModel(input_length, horizon, specification["dlinear"]["moving_average_kernel"])
    if model_id not in {"M2", "M3", "M3-shuffle"}:
        raise ValueError(f"Unknown SAPR model: {model_id}")
    mamba = specification["mamba"]
    return MambaResidualModel(
        horizon=horizon,
        phi_dim=phi_dim,
        d_model=mamba["d_model"],
        d_state=mamba["d_state"],
        d_conv=mamba["d_conv"],
        expand=mamba["expand"],
        layers=mamba["layers"],
        dropout=mamba["dropout"],
        gated=model_id in {"M3", "M3-shuffle"},
    )
