from controller import Supervisor
import sys, os, csv, time, math
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
COMMUNICATION_RANGE = 6.0
WAYPOINT_TOLERANCE = 0.35
MAX_CYCLES_PER_MODE = 900

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

    def set_positions(self, targets, alpha=0.045):
        current = self.positions()
        delta = np.asarray(targets) - current
        next_pos = current + np.clip(delta, -alpha, alpha)
        for d, p in zip(self.drones, next_pos):
            d.getField("translation").setSFVec3f(p.tolist())

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
                    len(comps), NUM_DRONES - len(comps[0]) if len(comps) else NUM_DRONES,
                    total_distance, len(completed), elapsed_ms
                ])
                f.flush()

                if len(completed) == len(self.tasks):
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

coord = Coordinator()
coord.run()
