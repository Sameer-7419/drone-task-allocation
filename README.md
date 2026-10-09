# Webots QRDPSO Swarm Project

Three-drone Webots simulation for comparing an RDPSO baseline with a QRDPSO-inspired neighborhood extension.

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
- CSV experiment logging

> Important: the supplied project transcript mentions "Eq. 5" and "Eq. 6", but it does not contain the mathematical equations themselves. Therefore this implementation uses a clearly isolated PSO-style neighborhood update as a reconstruction, not as a claim that it exactly reproduces the paper's equations. Replace the marked function in `qrdpso/qrdpso.py` with the paper's exact equations when available.

## Requirements

- Webots R2025b or compatible recent Webots release
- Windows 10/11
- Python 3.10+ configured in Webots
- NumPy

Install NumPy:
```powershell
python -m pip install numpy
```

## Run

1. Open Webots.
2. Open:
   `worlds/qrdpso_swarm.wbt`
3. Press Play.
4. The `swarm_coordinator` Supervisor controller runs the experiment.
5. Results are written to `results/mission_log.csv`.

The coordinator runs both modes sequentially:
- `RDPSO`
- `QRDPSO`

The world intentionally starts with only 3 drones. Once this is stable, increase `NUM_DRONES` and add more robot nodes.

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

1. Add the exact paper equations.
2. Add dynamic task arrival.
3. Add obstacles with path planning.
4. Add drone-failure experiments.
5. Scale to 5, 10, 15 and 20 drones.
6. Run headless repeated trials and aggregate results.


## Webots R2025a troubleshooting

This version does not use external Crazyflie, Floor, background, or lighting PROTOs.
The three drone `Robot` nodes are controlled by the `swarm_coordinator` Supervisor,
so they intentionally do not have individual controllers.

Before running Webots, install NumPy into the same Python interpreter Webots uses:

```powershell
.\install_dependencies.ps1
```

Or manually:

```powershell
"C:\Users\Sameer Gupta\AppData\Local\Programs\Python\Python313\python.exe" -m pip install numpy
```

Then open `worlds/qrdpso_swarm.wbt` in Webots R2025a and press Play.
