"""On-policy rollout storage with generalized advantage estimation."""
from __future__ import annotations
import numpy as np


class RolloutBuffer:
    def __init__(self) -> None:
        self.observations: list[np.ndarray] = []
        self.states: list[np.ndarray] = []
        self.masks: list[np.ndarray] = []
        self.actions: list[np.ndarray] = []
        self.log_probs: list[np.ndarray] = []
        self.values: list[float] = []
        self.rewards: list[float] = []
        self.dones: list[bool] = []

    def add(self, observation: np.ndarray, state: np.ndarray, mask: np.ndarray,
            action: np.ndarray, log_prob: np.ndarray, value: float, reward: float, done: bool) -> None:
        self.observations.append(observation.copy())
        self.states.append(state.copy())
        self.masks.append(mask.copy())
        self.actions.append(action.copy())
        self.log_probs.append(log_prob.copy())
        self.values.append(float(value))
        self.rewards.append(float(reward))
        self.dones.append(bool(done))

    def __len__(self) -> int:
        return len(self.rewards)

    def as_arrays(self, last_value: float, gamma: float, gae_lambda: float) -> dict[str, np.ndarray]:
        if not self.rewards:
            raise RuntimeError("Cannot train from an empty rollout")
        values = np.asarray(self.values + [last_value], dtype=np.float32)
        advantages = np.zeros(len(self), dtype=np.float32)
        gae = 0.0
        for step in reversed(range(len(self))):
            non_terminal = 1.0 - float(self.dones[step])
            delta = self.rewards[step] + gamma * values[step + 1] * non_terminal - values[step]
            gae = delta + gamma * gae_lambda * non_terminal * gae
            advantages[step] = gae
        return {
            "observations": np.asarray(self.observations, dtype=np.float32),
            "states": np.asarray(self.states, dtype=np.float32),
            "masks": np.asarray(self.masks, dtype=bool),
            "actions": np.asarray(self.actions, dtype=np.int64),
            "old_log_probs": np.asarray(self.log_probs, dtype=np.float32),
            "advantages": advantages,
            "returns": advantages + values[:-1],
        }

    def clear(self) -> None:
        self.__init__()
