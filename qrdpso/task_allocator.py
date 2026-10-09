import numpy as np

def allocate_nearest(drones, tasks):
    """Greedy one-to-one nearest-task allocation.

    drones: list/array of [x,y,z]
    tasks: list/array of [x,y,z]
    returns: dict {drone_index: task_index}
    """
    drones = np.asarray(drones, dtype=float)
    tasks = np.asarray(tasks, dtype=float)
    remaining = set(range(len(tasks)))
    allocation = {}

    for i, p in enumerate(drones):
        if not remaining:
            break
        j = min(remaining, key=lambda k: np.linalg.norm(p - tasks[k]))
        allocation[i] = j
        remaining.remove(j)
    return allocation
