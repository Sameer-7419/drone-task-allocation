"""Neural modules for MAPPO: a shared decentralized actor and central critic."""
import torch
from torch import nn


def _mlp(input_dim: int, hidden_dim: int, output_dim: int) -> nn.Sequential:
    return nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.Tanh(), nn.Linear(hidden_dim, hidden_dim), nn.Tanh(), nn.Linear(hidden_dim, output_dim))


class SharedActor(nn.Module):
    def __init__(self, observation_dim: int, action_dim: int, hidden_dim: int):
        super().__init__()
        self.network = _mlp(observation_dim, hidden_dim, action_dim)

    def forward(self, observations: torch.Tensor, action_mask: torch.Tensor | None = None) -> torch.Tensor:
        logits = self.network(observations)
        if action_mask is not None:
            logits = logits.masked_fill(~action_mask.bool(), torch.finfo(logits.dtype).min)
        return logits


class CentralCritic(nn.Module):
    def __init__(self, state_dim: int, hidden_dim: int):
        super().__init__()
        self.network = _mlp(state_dim, hidden_dim, 1)

    def forward(self, states: torch.Tensor) -> torch.Tensor:
        return self.network(states).squeeze(-1)
