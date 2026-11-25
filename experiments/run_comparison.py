"""Train and compare RDPSO, QRDPSO, and communication-aware adaptive MAPPO.

Run from the repository root::
    python -m experiments.run_comparison --train-episodes 600 --evaluation-episodes 50 --seeds 7 11 19
"""
from __future__ import annotations
import argparse
import csv
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any
import numpy as np

from environment import ScenarioConfig, UAVTaskAllocationEnv
from mappo import MAPPOConfig, MAPPOTrainer
from qrdpso.rd_pso import RDPSO
from qrdpso.qrdpso import QRDPSO
from qrdpso.connectivity import adjacency_matrix

ROOT = Path(__file__).resolve().parents[1]


def _optimizer_actions(env: UAVTaskAllocationEnv, algorithm: str, seed: int) -> np.ndarray:
    """Translate existing waypoint optimizers into task selections."""
    remaining = np.flatnonzero(~env.completed)
    actions = np.full(env.config.num_uavs, env.config.num_tasks, dtype=int)
    if not len(remaining):
        return actions
    targets = np.asarray([env.tasks[remaining[np.argmin(np.linalg.norm(env.tasks[remaining] - p, axis=1))]] for p in env.positions])
    current = env._positions_3d()
    target_3d = np.column_stack((targets, np.zeros(len(targets))))
    if algorithm == "RDPSO":
        candidate = RDPSO(seed=seed + env.step_count).optimize(current, target_3d, iterations=8)[:, :2]
    else:
        adjacency = adjacency_matrix(current, env.config.communication_range)
        candidate = QRDPSO(seed=seed + env.step_count).optimize(current, target_3d, adjacency, iterations=8)[:, :2]
    # Convert continuous optimizer waypoints into a one-to-one task allocation.
    # This prevents a waypoint baseline from gaining/losing performance merely
    # because several UAVs select the same already-served task.
    choices = []
    for drone, waypoint in enumerate(candidate):
        for task in remaining:
            choices.append((float(np.linalg.norm(env.tasks[task] - waypoint)), drone, int(task)))
    assigned_drones, assigned_tasks = set(), set()
    for _, drone, task in sorted(choices):
        if drone not in assigned_drones and task not in assigned_tasks:
            actions[drone] = task
            assigned_drones.add(drone)
            assigned_tasks.add(task)
    return actions


def _record(method: str, seed: int, env: UAVTaskAllocationEnv, info: dict[str, Any], computation_ms: float) -> dict[str, float]:
    return {"method": method, "seed": seed, "task_completion_rate": info["task_completion_rate"],
            "mission_steps": env.step_count, "total_distance": env.total_distance,
            "mean_connectivity": float(np.mean(env.connectivity_history)),
            "disconnected_uavs": info["disconnected_uavs"], "computation_ms": computation_ms}


def evaluate_optimizer(algorithm: str, config: ScenarioConfig, seed: int) -> dict[str, float]:
    env = UAVTaskAllocationEnv(config, seed)
    env.reset(seed)
    done, elapsed, info = False, 0.0, {}
    while not done:
        started = time.perf_counter()
        actions = _optimizer_actions(env, algorithm, seed)
        elapsed += time.perf_counter() - started
        _, _, _, done, info = env.step(actions)
    return _record(algorithm, seed, env, info, elapsed * 1000)


def evaluate_mappo(trainer: MAPPOTrainer, config: ScenarioConfig, seed: int) -> dict[str, float]:
    env = UAVTaskAllocationEnv(config, seed)
    observations, state = env.reset(seed)
    done, elapsed, info = False, 0.0, {}
    while not done:
        started = time.perf_counter()
        actions, _, _ = trainer.act(observations, state, env.action_mask(), deterministic=True)
        elapsed += time.perf_counter() - started
        observations, state, _, done, info = env.step(actions)
    return _record("AC-MAPPO", seed, env, info, elapsed * 1000)


def summarize(records: list[dict[str, float]]) -> list[dict[str, float]]:
    fields = ["task_completion_rate", "mission_steps", "total_distance", "mean_connectivity", "disconnected_uavs", "computation_ms"]
    summary = []
    for method in sorted({str(row["method"]) for row in records}):
        subset = [row for row in records if row["method"] == method]
        row: dict[str, float] = {"method": method, "runs": len(subset)}
        for field in fields:
            values = np.asarray([float(item[field]) for item in subset])
            row[f"{field}_mean"] = float(values.mean())
            row[f"{field}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
        summary.append(row)
    return summary


def write_csv(path: Path, rows: list[dict[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-episodes", type=int, default=400)
    parser.add_argument("--evaluation-episodes", type=int, default=20)
    parser.add_argument("--seeds", type=int, nargs="+", default=[7, 11, 19])
    parser.add_argument("--communication-range", type=float, default=5.5)
    args = parser.parse_args()
    scenario = ScenarioConfig(communication_range=args.communication_range)
    records: list[dict[str, float]] = []
    for seed in args.seeds:
        train_env = UAVTaskAllocationEnv(scenario, seed)
        trainer = MAPPOTrainer(train_env.observation_dim, train_env.state_dim, train_env.action_dim, MAPPOConfig(), seed)
        trainer.train(train_env, args.train_episodes)
        trainer.save(ROOT / "results" / "models" / f"ac_mappo_seed_{seed}.pt")
        for episode in range(args.evaluation_episodes):
            episode_seed = seed * 10_000 + episode
            records.extend([evaluate_optimizer("RDPSO", scenario, episode_seed),
                            evaluate_optimizer("QRDPSO", scenario, episode_seed),
                            evaluate_mappo(trainer, scenario, episode_seed)])
    write_csv(ROOT / "results" / "comparison_raw.csv", records)
    summary = summarize(records)
    write_csv(ROOT / "results" / "comparison_summary.csv", summary)
    print("Experiment configuration:", asdict(scenario))
    for row in summary:
        print(row)


if __name__ == "__main__":
    main()
