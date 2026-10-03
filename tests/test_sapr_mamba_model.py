from __future__ import annotations

import torch

from model.StateAwarePersistenceResidualMamba import DLinearResidualModel, DriftModel, LinearResidualModel, PersistenceModel, SeasonalNaiveModel


def test_persistence_is_exact_last_observation_repeat() -> None:
    x = torch.tensor([[1.0, 2.0, 5.0], [-2.0, 4.0, 7.0]])
    output = PersistenceModel(4)(x, torch.zeros(2, 9))
    assert torch.equal(output["forecast"], x[:, -1:].expand(-1, 4))
    assert torch.equal(output["gate"], torch.ones(2, 4))


def test_linear_residual_model_uses_numeric_projection_and_backpropagates() -> None:
    model = LinearResidualModel(horizon=4, phi_dim=9, history_projection=6)
    x = torch.randn(3, 12, requires_grad=True)
    output = model(x, torch.randn(3, 9))
    assert output["forecast"].shape == (3, 4)
    output["forecast"].square().mean().backward()
    assert torch.isfinite(x.grad).all()


def test_contextual_naive_models_are_causal_paths() -> None:
    x = torch.tensor([[1.0, 2.0, 3.0, 4.0]])
    phi = torch.zeros(1, 9)
    assert torch.equal(SeasonalNaiveModel(3, 2)(x, phi)["forecast"], torch.tensor([[3.0, 4.0, 3.0]]))
    assert torch.allclose(DriftModel(2)(x, phi)["forecast"], torch.tensor([[5.0, 6.0]]))
    output = DLinearResidualModel(4, 2, 3)(x, phi)
    assert output["forecast"].shape == (1, 2)
