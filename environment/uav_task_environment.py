"""A lightweight, reproducible cooperative UAV task-allocation environment.

The environment deliberately models allocation rather than low-level flight.  Each
agent selects a pending task (or an idle action) and moves one bounded step toward
that task.  This makes the MAPPO objective comparable with RDPSO/QRDPSO while
remaining fast enough for repeated seed-based experiments.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np

from qrdpso.connectivity import adjacency_matrix, connected_components, mean_link_connectivity


@dataclass
class ScenarioConfig:
    num_uavs: int = 3
    num_tasks: int = 3
    arena_size: float = 10.0
    communication_range: float = 5.5
    speed: float = 0.35
    task_radius: float = 0.45
    max_steps: int = 80
    energy_budget: float = 40.0
    communication_aware_observation: bool = True
    adaptive_communication_reward: bool = True
    base_communication_penalty: float = 1.5
    adaptive_penalty_gain: float = 4.0


class UAVTaskAllocationEnv:
    """Shared-reward multi-agent environment with fixed-size observations.

    An observation consists of own normalized position/energy, every task's
    relative position and completion flag, then local communication features.
    The critic state is the concatenated global positions, energies, task state,
    and current graph statistics.
    """

    def __init__(self, config: ScenarioConfig | None = None, seed: int | None = None):
        self.config = config or ScenarioConfig()
        self.rng = np.random.default_rng(seed)
        self.positions = np.empty((0, 2))
        self.tasks = np.empty((0, 2))
        self.completed = np.empty(0, dtype=bool)
        self.energy = np.empty(0)
        self.step_count = 0
        self.total_distance = 0.0
        self.connectivity_history: list[float] = []

    @property
    def action_dim(self) -> int:
        return self.config.num_tasks + 1  # final action is idle

    @property
    def observation_dim(self) -> int:
        task_features = self.config.num_tasks * 3  # dx, dy, completion
        communication = 3 if self.config.communication_aware_observation else 0
        return 3 + task_features + communication  # x, y, energy

    @property
    def state_dim(self) -> int:
        return self.config.num_uavs * 3 + self.config.num_tasks * 3 + 2

    def reset(self, seed: int | None = None) -> tuple[np.ndarray, np.ndarray]:
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        size = self.config.arena_size
        self.positions = self.rng.uniform(-size, size, (self.config.num_uavs, 2))
        self.tasks = self.rng.uniform(-size, size, (self.config.num_tasks, 2))
        self.completed = np.zeros(self.config.num_tasks, dtype=bool)
        self.energy = np.full(self.config.num_uavs, self.config.energy_budget, dtype=float)
        self.step_count = 0
        self.total_distance = 0.0
        self.connectivity_history = []
        return self.observations(), self.global_state()

    def connectivity(self) -> tuple[np.ndarray, float, int]:
        adjacency = adjacency_matrix(self._positions_3d(), self.config.communication_range)
        return adjacency, mean_link_connectivity(adjacency), len(connected_components(adjacency))

    def observations(self) -> np.ndarray:
        adjacency, link_ratio, _ = self.connectivity()
        scale = self.config.arena_size
        rows = []
        for agent, position in enumerate(self.positions):
            own = [position[0] / scale, position[1] / scale,
                   self.energy[agent] / self.config.energy_budget]
            task_features: list[float] = []
            for task, done in zip(self.tasks, self.completed):
                delta = (task - position) / scale
                task_features.extend([delta[0], delta[1], float(done)])
            if self.config.communication_aware_observation:
                degree = float(adjacency[agent].sum()) / max(1, self.config.num_uavs - 1)
                component_size = self._component_size(adjacency, agent) / self.config.num_uavs
                own.extend([degree, component_size, link_ratio])
            rows.append(own + task_features)
        return np.asarray(rows, dtype=np.float32)

    def global_state(self) -> np.ndarray:
        _, link_ratio, components = self.connectivity()
        scale = self.config.arena_size
        drones = np.column_stack((self.positions / scale, self.energy[:, None] / self.config.energy_budget))
        task_data = np.column_stack((self.tasks / scale, self.completed.astype(float)))
        return np.concatenate((drones.ravel(), task_data.ravel(), [link_ratio, components / self.config.num_uavs])).astype(np.float32)

    def action_mask(self) -> np.ndarray:
        """Masks completed tasks; idle always remains available."""
        mask = np.ones((self.config.num_uavs, self.action_dim), dtype=bool)
        mask[:, :self.config.num_tasks] = ~self.completed
        return mask

    def step(self, actions: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, bool, dict[str, Any]]:
        actions = np.asarray(actions, dtype=int)
        if actions.shape != (self.config.num_uavs,):
            raise ValueError(f"Expected {self.config.num_uavs} actions, got {actions.shape}")
        previous = self.positions.copy()
        newly_completed = 0
        for agent, action in enumerate(actions):
            if 0 <= action < self.config.num_tasks and not self.completed[action] and self.energy[agent] > 0:
                direction = self.tasks[action] - self.positions[agent]
                distance = float(np.linalg.norm(direction))
                movement = min(self.config.speed, distance, self.energy[agent])
                if distance > 1e-9:
                    self.positions[agent] += direction / distance * movement
                self.energy[agent] -= movement
                if np.linalg.norm(self.tasks[action] - self.positions[agent]) <= self.config.task_radius:
                    self.completed[action] = True
                    newly_completed += 1
        travelled = float(np.linalg.norm(self.positions - previous, axis=1).sum())
        self.total_distance += travelled
        self.step_count += 1
        _, connectivity, components = self.connectivity()
        self.connectivity_history.append(connectivity)
        lambda_comm = self.config.base_communication_penalty
        if self.config.adaptive_communication_reward:
            lambda_comm += self.config.adaptive_penalty_gain * (1.0 - connectivity)
        disconnected = self.config.num_uavs - max(
            (len(component) for component in connected_components(self.connectivity()[0])),
            default=0,
        )
        reward = 12.0 * newly_completed - 0.25 * travelled - lambda_comm * (1.0 - connectivity) - 0.5 * disconnected
        done = bool(self.completed.all() or self.step_count >= self.config.max_steps or np.all(self.energy <= 0))
        info = {
            "completed_tasks": int(self.completed.sum()), "task_completion_rate": float(self.completed.mean()),
            "distance": self.total_distance, "mean_connectivity": connectivity,
            "components": components, "disconnected_uavs": disconnected,
            "communication_penalty": lambda_comm, "newly_completed": newly_completed,
        }
        return self.observations(), self.global_state(), float(reward), done, info

    def _positions_3d(self) -> np.ndarray:
        return np.column_stack((self.positions, np.zeros(self.config.num_uavs)))

    @staticmethod
    def _component_size(adjacency: np.ndarray, source: int) -> int:
        for component in connected_components(adjacency):
            if source in component:
                return len(component)
        return 1
