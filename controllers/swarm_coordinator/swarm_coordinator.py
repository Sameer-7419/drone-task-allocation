from controller import Supervisor
import sys, os, csv, time
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from qrdpso.connectivity import adjacency_matrix, connected_components, mean_link_connectivity
from qrdpso.task_allocator import allocate_nearest
from qrdpso.rd_pso import RDPSO
from qrdpso.qrdpso import QRDPSO

TIME_STEP = 50
NUM_DRONES = 3
# Matches the communication range used to train the saved MAPPO checkpoints.
COMMUNICATION_RANGE = 5.5
WAYPOINT_TOLERANCE = 0.35
MAX_CYCLES_PER_MODE = 900
# NumPy-only actor exported from a trained MAPPO checkpoint. It avoids a
# PyTorch dependency inside Webots; create it with mappo.export_webots_policy.
MAPPO_POLICY = os.path.join(ROOT, "results", "models", "ac_mappo_seed_7.npz")
MAPPO_ARENA_SIZE = 10.0
MAPPO_ENERGY_BUDGET = 40.0

class Coordinator(Supervisor):
    def __init__(self):
        super().__init__()
        self.drones = [self.getFromDef(f"DRONE{i}") for i in range(NUM_DRONES)]
        self.initial = [np.array(self.drones[i].getField("translation").getSFVec3f(), dtype=float)
                        for i in range(NUM_DRONES)]
        self.tasks = np.array([[4.0, 0.0, 2.0], [-4.0, 1.5, 2.0], [0.0, -4.0, 2.0]])
        os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
        self.log_path = os.path.join(ROOT, "results", "mission_log.csv")

    def positions(self):
        return np.array([d.getField("translation").getSFVec3f() for d in self.drones], dtype=float)

    def reset(self):
        for d, p in zip(self.drones, self.initial):
            d.getField("translation").setSFVec3f(p.tolist())
        self.step(TIME_STEP)

    def set_positions(self, targets, alpha=0.045, max_distance=None):
        current = self.positions()
        delta = np.asarray(targets) - current
        if max_distance is None:
            # Preserve the original component-wise motion used by PSO modes.
            next_pos = current + np.clip(delta, -alpha, alpha)
        else:
            distances = np.linalg.norm(delta, axis=1, keepdims=True)
            scale = np.minimum(1.0, max_distance / np.maximum(distances, 1e-9))
            next_pos = current + delta * scale
        for d, p in zip(self.drones, next_pos):
            d.getField("translation").setSFVec3f(p.tolist())

    @staticmethod
    def disconnected_count(components):
        return NUM_DRONES - max((len(component) for component in components), default=0)

    def run_mode(self, mode):
        self.reset()
        algo = RDPSO(seed=11) if mode == "RDPSO" else QRDPSO(seed=11)
        completed = set()
        total_distance = 0.0
        previous = self.positions()

        with open(self.log_path, "a", newline="") as f:
            writer = csv.writer(f)
            for cycle in range(MAX_CYCLES_PER_MODE):
                start = time.perf_counter()
                pos = self.positions()
                a = adjacency_matrix(pos, COMMUNICATION_RANGE)
                comps = connected_components(a)

                if mode == "RDPSO":
                    candidate = algo.optimize(pos, self.tasks, iterations=4)
                else:
                    candidate = algo.optimize(pos, self.tasks, a, iterations=4)

                allocation = allocate_nearest(pos, self.tasks)
                targets = np.array([self.tasks[allocation[i]] for i in range(NUM_DRONES)])
                # Keep the algorithm's candidate useful without making the
                # demo unstable: blend optimizer output with assigned task.
                targets = 0.35 * candidate + 0.65 * targets

                self.set_positions(targets)
                self.step(TIME_STEP)

                now = self.positions()
                total_distance += float(np.sum(np.linalg.norm(now - previous, axis=1)))
                previous = now

                for i in range(NUM_DRONES):
                    if np.linalg.norm(now[i] - self.tasks[allocation[i]]) <= WAYPOINT_TOLERANCE:
                        completed.add(allocation[i])

                elapsed_ms = (time.perf_counter() - start) * 1000
                writer.writerow([
                    self.getTime(), mode, cycle, mean_link_connectivity(a),
                    len(comps), self.disconnected_count(comps),
                    total_distance, len(completed), elapsed_ms
                ])
                f.flush()

                if len(completed) == len(self.tasks):
                    break

    def run_mappo_mode(self):
        """Run decentralized MAPPO actor inference in the Webots world."""
        # Keep MAPPO optional at controller startup.  A missing PyTorch package
        # or checkpoint must never stop the RDPSO/QRDPSO visual simulation.
        try:
            from mappo.webots_inference import MAPPOActorPolicy, action_mask, local_observations
            policy = MAPPOActorPolicy(MAPPO_POLICY)
        except Exception as error:
            print("AC-MAPPO was skipped. RDPSO and QRDPSO completed normally.")
            print(f"AC-MAPPO startup error: {type(error).__name__}: {error}")
            print("Create the NumPy actor file with mappo.export_webots_policy and verify MAPPO_POLICY.")
            return
        self.reset()
        completed = np.zeros(len(self.tasks), dtype=bool)
        energy = np.full(NUM_DRONES, MAPPO_ENERGY_BUDGET, dtype=float)
        total_distance = 0.0
        previous = self.positions()

        with open(self.log_path, "a", newline="") as f:
            writer = csv.writer(f)
            for cycle in range(MAX_CYCLES_PER_MODE):
                start = time.perf_counter()
                positions_3d = self.positions()
                adjacency = adjacency_matrix(positions_3d, COMMUNICATION_RANGE)
                components = connected_components(adjacency)
                link_ratio = mean_link_connectivity(adjacency)
                observations = local_observations(
                    positions_3d[:, :2], self.tasks[:, :2], completed, energy, adjacency,
                    link_ratio, MAPPO_ARENA_SIZE, MAPPO_ENERGY_BUDGET,
                )
                actions = policy.select_actions(observations, action_mask(completed, NUM_DRONES))

                # Action 0..N-1 selects a task; N is the trained idle action.
                targets = positions_3d.copy()
                for drone, task in enumerate(actions):
                    if task < len(self.tasks) and not completed[task]:
                        targets[drone] = self.tasks[task]
                # Match the 0.35-distance movement increment used during MAPPO training.
                self.set_positions(targets, max_distance=0.35)
                self.step(TIME_STEP)

                now = self.positions()
                movement = np.linalg.norm(now - previous, axis=1)
                total_distance += float(movement.sum())
                energy = np.maximum(0.0, energy - movement)
                previous = now
                for drone, task in enumerate(actions):
                    if task < len(self.tasks) and np.linalg.norm(now[drone] - self.tasks[task]) <= WAYPOINT_TOLERANCE:
                        completed[task] = True

                elapsed_ms = (time.perf_counter() - start) * 1000
                writer.writerow([
                    self.getTime(), "AC-MAPPO", cycle, link_ratio,
                    len(components), self.disconnected_count(components),
                    total_distance, int(completed.sum()), elapsed_ms,
                ])
                f.flush()
                if completed.all() or np.all(energy <= 0):
                    break

    def run(self):
        # Header
        with open(self.log_path, "w", newline="") as f:
            csv.writer(f).writerow([
                "sim_time", "mode", "cycle", "mean_connectivity",
                "connected_components", "disconnected_estimate",
                "total_distance", "completed_tasks", "allocation_time_ms"
            ])
        self.run_mode("RDPSO")
        self.run_mode("QRDPSO")
        self.run_mappo_mode()

coord = Coordinator()
coord.run()
