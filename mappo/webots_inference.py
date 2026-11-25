"""NumPy-only MAPPO actor inference for the Webots supervisor.

Use ``mappo.export_webots_policy`` once to convert a PyTorch checkpoint to the
``.npz`` actor file expected here. No PyTorch import occurs in this module.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np

from qrdpso.connectivity import connected_components


class MAPPOActorPolicy:
    """Execute the shared two-hidden-layer MAPPO actor with NumPy only."""

    def __init__(self, policy_path: str | Path):
        path = Path(policy_path)
        if not path.is_file():
            raise FileNotFoundError(
                f"MAPPO Webots policy was not found: {path}. "
                "Create it with: python -m mappo.export_webots_policy --checkpoint results/models/ac_mappo_seed_7.pt"
            )
        with np.load(path) as policy:
            expected = {"layer1_weight", "layer1_bias", "layer2_weight", "layer2_bias", "output_weight", "output_bias"}
            missing = expected.difference(policy.files)
            if missing:
                raise ValueError(f"Invalid MAPPO policy file; missing {sorted(missing)}")
            self.layer1_weight = policy["layer1_weight"]
            self.layer1_bias = policy["layer1_bias"]
            self.layer2_weight = policy["layer2_weight"]
            self.layer2_bias = policy["layer2_bias"]
            self.output_weight = policy["output_weight"]
            self.output_bias = policy["output_bias"]
        self.observation_dim = int(self.layer1_weight.shape[1])
        self.action_dim = int(self.output_weight.shape[0])
        self.path = path

    def select_actions(self, observations: np.ndarray, action_mask: np.ndarray) -> np.ndarray:
        observations = np.asarray(observations, dtype=np.float32)
        action_mask = np.asarray(action_mask, dtype=bool)
        if observations.ndim != 2 or observations.shape[1] != self.observation_dim:
            raise ValueError(f"Policy expects observations shaped (UAVs, {self.observation_dim}), got {observations.shape}")
        if action_mask.shape != (len(observations), self.action_dim):
            raise ValueError(f"Policy expects an action mask shaped ({len(observations)}, {self.action_dim}), got {action_mask.shape}")
        hidden = np.tanh(observations @ self.layer1_weight.T + self.layer1_bias)
        hidden = np.tanh(hidden @ self.layer2_weight.T + self.layer2_bias)
        logits = hidden @ self.output_weight.T + self.output_bias
        logits = np.where(action_mask, logits, -np.inf)
        return np.argmax(logits, axis=1).astype(int)


def local_observations(positions: np.ndarray, tasks: np.ndarray, completed: np.ndarray,
                       energy: np.ndarray, adjacency: np.ndarray, link_ratio: float,
                       arena_size: float, energy_budget: float) -> np.ndarray:
    """Build the local observation in the exact training-time feature order."""
    positions = np.asarray(positions, dtype=float)
    tasks = np.asarray(tasks, dtype=float)
    rows: list[list[float]] = []
    for agent, position in enumerate(positions):
        component_size = _component_size(adjacency, agent) / len(positions)
        own = [position[0] / arena_size, position[1] / arena_size,
               energy[agent] / energy_budget,
               float(adjacency[agent].sum()) / max(1, len(positions) - 1),
               component_size, link_ratio]
        task_features: list[float] = []
        for task, done in zip(tasks, completed):
            relative = (task - position) / arena_size
            task_features.extend([relative[0], relative[1], float(done)])
        rows.append(own + task_features)
    return np.asarray(rows, dtype=np.float32)


def action_mask(completed: np.ndarray, num_agents: int) -> np.ndarray:
    """Completed tasks are masked; the final action is always idle."""
    completed = np.asarray(completed, dtype=bool)
    task_mask = np.broadcast_to(~completed, (num_agents, len(completed)))
    return np.column_stack((task_mask, np.ones((num_agents, 1), dtype=bool)))


def _component_size(adjacency: np.ndarray, agent: int) -> int:
    for component in connected_components(adjacency):
        if agent in component:
            return len(component)
    return 1
