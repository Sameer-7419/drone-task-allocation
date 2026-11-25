# Webots QRDPSO Swarm Project

Three-drone Webots simulation plus a reproducible, headless research pipeline for comparing RDPSO, QRDPSO, and communication-aware adaptive MAPPO.

## Scope

The initial experiment contains:
- 3 Crazyflie-style quadrotors in Webots
- Python-based swarm coordinator
- waypoint/task allocation
- position-based adjacency matrix
- neighborhood calculation
- multi-hop connectivity
- simulated communication degradation
- RDPSO baseline vs QRDPSO-inspired Eq. 6 mode
- MAPPO with shared decentralized actors and a centralized critic (CTDE)
- communication-aware observations and adaptive connectivity penalty
- CSV experiment logging

> Important: the supplied project transcript mentions "Eq. 5" and "Eq. 6", but it does not contain the mathematical equations themselves. Therefore this implementation uses a clearly isolated PSO-style neighborhood update as a reconstruction, not as a claim that it exactly reproduces the paper's equations. Replace the marked function in `qrdpso/qrdpso.py` with the paper's exact equations when available.

## Requirements

- Webots R2025b or compatible recent Webots release
- Windows 10/11
- Python 3.10+ configured in Webots
- NumPy and PyTorch

Install NumPy:
```powershell
python -m pip install numpy torch
```

## Run

1. Open Webots.
2. Open:
   `worlds/qrdpso_swarm.wbt`
3. Press Play.
4. The `swarm_coordinator` Supervisor controller runs the experiment.
5. Results are written to `results/mission_log.csv`.

Create a NumPy actor file for Webots after training (or run the comparison again;
new runs create it automatically):

```powershell
python -m mappo.export_webots_policy --checkpoint results/models/ac_mappo_seed_7.pt
```

When `results/models/ac_mappo_seed_7.npz` exists, the supervisor runs
deterministic `AC-MAPPO` inference after the two PSO modes. Webots needs only
NumPy; it does not need PyTorch. Change `MAPPO_POLICY` in
`controllers/swarm_coordinator/swarm_coordinator.py` to visualize another seed.

The coordinator runs the following modes sequentially:
- `RDPSO`
- `QRDPSO`
- `AC-MAPPO` (when its checkpoint is present)

The world intentionally starts with only 3 drones. Once this is stable, increase `NUM_DRONES` and add more robot nodes.

## MAPPO research experiment

The fair three-algorithm experiment is intentionally independent of Webots so
that it can run repeated seed-based trials quickly. Every algorithm receives the
same generated scenario. From the repository root, run:

```powershell
python -m experiments.run_comparison --train-episodes 600 --evaluation-episodes 50 --seeds 7 11 19 23 29
```

It writes `results/comparison_raw.csv`, `results/comparison_summary.csv`, and a
trained checkpoint per seed in `results/models/`. The summary reports mean and
sample standard deviation for task completion, mission steps, distance, mean
connectivity, disconnected UAVs, and decision time. Regenerate these artifacts
with the exact seeds and parameters used in the thesis; do not present a single
run as a research result.

The proposed method is AC-MAPPO. Actors observe their own position/energy, task
state, degree, connected-component size, and link ratio. The central critic sees
the full swarm state only during training. Its adaptive communication penalty is
`lambda_c(t) = lambda_c0 + alpha * (1 - connectivity(t))`.

## Project layout

```text
webots_qrdpso/
├── worlds/
│   └── qrdpso_swarm.wbt
├── controllers/
│   ├── swarm_coordinator/
│   │   └── swarm_coordinator.py
│   └── drone_controller/
│       └── drone_controller.py
├── qrdpso/
│   ├── __init__.py
│   ├── connectivity.py
│   ├── task_allocator.py
│   ├── rd_pso.py
│   └── qrdpso.py
└── results/
    └── .gitkeep
```

## Metrics

The log contains:
- simulation time
- algorithm mode
- mean pairwise connectivity
- number of connected components
- lost/disconnected drones
- total distance travelled
- completed tasks
- allocation computation time

## Communication model

The transcript specifies a direct position-distance model:

A_ij = 1 if ||p_i - p_j|| <= R_c

This project implements exactly that model at the coordinator level. It does not attempt to reproduce a physical Wi-Fi/radio stack.

## Next extensions

1. Substitute the exact paper equations where available.
2. Add dynamic task-arrival and UAV-failure experiment drivers.
3. Scale the common experiment to 5, 10, 15 and 20 UAVs.
4. Run MAPPO ablations by toggling the two `ScenarioConfig` contribution flags.


## Webots R2025a troubleshooting

This version does not use external Crazyflie, Floor, background, or lighting PROTOs.
The three drone `Robot` nodes are controlled by the `swarm_coordinator` Supervisor,
so they intentionally do not have individual controllers.

Before running Webots or the MAPPO experiment, install NumPy and PyTorch into the same Python interpreter:

```powershell
.\install_dependencies.ps1
```

Or manually:

```powershell
<your-python> -m pip install numpy torch
```

Then open `worlds/qrdpso_swarm.wbt` in Webots R2025a and press Play.
