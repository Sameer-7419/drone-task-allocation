"""A compact MAPPO trainer with shared actors and a centralized critic.

The actors receive only their individual observations at action time.  The critic
is trained from the complete swarm state, which implements CTDE without leaking
global state into execution.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import numpy as np
import torch
from torch.distributions import Categorical

from .config import MAPPOConfig
from .networks import SharedActor, CentralCritic
from .rollout import RolloutBuffer


class MAPPOTrainer:
    def __init__(self, observation_dim: int, state_dim: int, action_dim: int,
                 config: MAPPOConfig | None = None, seed: int = 0):
        self.config = config or MAPPOConfig()
        self.device = torch.device(self.config.device)
        torch.manual_seed(seed)
        self.actor = SharedActor(observation_dim, action_dim, self.config.hidden_dim).to(self.device)
        self.critic = CentralCritic(state_dim, self.config.hidden_dim).to(self.device)
        self.optimizer = torch.optim.Adam(list(self.actor.parameters()) + list(self.critic.parameters()), lr=self.config.learning_rate)
        self.buffer = RolloutBuffer()

    @torch.no_grad()
    def act(self, observations: np.ndarray, state: np.ndarray, action_mask: np.ndarray, deterministic: bool = False) -> tuple[np.ndarray, np.ndarray, float]:
        obs = torch.as_tensor(observations, dtype=torch.float32, device=self.device)
        mask = torch.as_tensor(action_mask, dtype=torch.bool, device=self.device)
        logits = self.actor(obs, mask)
        distribution = Categorical(logits=logits)
        actions = torch.argmax(logits, dim=-1) if deterministic else distribution.sample()
        log_probs = distribution.log_prob(actions)
        value = self.critic(torch.as_tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0))[0]
        return actions.cpu().numpy(), log_probs.cpu().numpy(), float(value.cpu())

    @torch.no_grad()
    def value(self, state: np.ndarray) -> float:
        tensor = torch.as_tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
        return float(self.critic(tensor)[0].cpu())

    def update(self, last_value: float) -> dict[str, float]:
        data = self.buffer.as_arrays(last_value, self.config.gamma, self.config.gae_lambda)
        advantages = data["advantages"]
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        observations = torch.as_tensor(data["observations"], dtype=torch.float32, device=self.device)
        states = torch.as_tensor(data["states"], dtype=torch.float32, device=self.device)
        masks = torch.as_tensor(data["masks"], dtype=torch.bool, device=self.device)
        actions = torch.as_tensor(data["actions"], dtype=torch.int64, device=self.device)
        old_log_probs = torch.as_tensor(data["old_log_probs"], dtype=torch.float32, device=self.device)
        advantages_t = torch.as_tensor(advantages, dtype=torch.float32, device=self.device)
        returns = torch.as_tensor(data["returns"], dtype=torch.float32, device=self.device)
        metrics: dict[str, float] = {}
        for _ in range(self.config.update_epochs):
            # Shared environmental reward becomes one advantage per agent.
            dist = Categorical(logits=self.actor(observations, masks))
            log_probs = dist.log_prob(actions)
            ratios = torch.exp(log_probs - old_log_probs)
            expanded_advantages = advantages_t[:, None]
            surrogate_a = ratios * expanded_advantages
            surrogate_b = torch.clamp(ratios, 1 - self.config.clip_ratio, 1 + self.config.clip_ratio) * expanded_advantages
            policy_loss = -torch.minimum(surrogate_a, surrogate_b).mean()
            values = self.critic(states)
            value_loss = torch.nn.functional.mse_loss(values, returns)
            entropy = dist.entropy().mean()
            loss = policy_loss + self.config.value_coefficient * value_loss - self.config.entropy_coefficient * entropy
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(list(self.actor.parameters()) + list(self.critic.parameters()), self.config.max_grad_norm)
            self.optimizer.step()
            metrics = {"loss": float(loss.detach().cpu()), "policy_loss": float(policy_loss.detach().cpu()),
                       "value_loss": float(value_loss.detach().cpu()), "entropy": float(entropy.detach().cpu())}
        self.buffer.clear()
        return metrics

    def train(self, env: Any, episodes: int) -> list[dict[str, float]]:
        history: list[dict[str, float]] = []
        for episode in range(episodes):
            observations, state = env.reset()
            episode_reward = 0.0
            done = False
            info: dict[str, Any] = {}
            while not done:
                mask = env.action_mask()
                actions, log_probs, value = self.act(observations, state, mask)
                next_obs, next_state, reward, done, info = env.step(actions)
                self.buffer.add(observations, state, mask, actions, log_probs, value, reward, done)
                observations, state = next_obs, next_state
                episode_reward += reward
                if len(self.buffer) >= self.config.rollout_steps or done:
                    update_metrics = self.update(0.0 if done else self.value(next_state))
            history.append({"episode": episode, "reward": episode_reward, **info, **update_metrics})
        return history

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"actor": self.actor.state_dict(), "critic": self.critic.state_dict(), "config": self.config}, path)
        # Webots uses a portable NumPy-only actor. It therefore does not need
        # PyTorch or a Python installation that matches the training setup.
        actor_state = self.actor.state_dict()
        np.savez_compressed(
            path.with_suffix(".npz"),
            layer1_weight=actor_state["network.0.weight"].detach().cpu().numpy(),
            layer1_bias=actor_state["network.0.bias"].detach().cpu().numpy(),
            layer2_weight=actor_state["network.2.weight"].detach().cpu().numpy(),
            layer2_bias=actor_state["network.2.bias"].detach().cpu().numpy(),
            output_weight=actor_state["network.4.weight"].detach().cpu().numpy(),
            output_bias=actor_state["network.4.bias"].detach().cpu().numpy(),
        )
