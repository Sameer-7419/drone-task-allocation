import numpy as np

def adjacency_matrix(positions, communication_range):
    positions = np.asarray(positions, dtype=float)
    n = len(positions)
    a = np.zeros((n, n), dtype=int)
    for i in range(n):
        for j in range(i + 1, n):
            if np.linalg.norm(positions[i] - positions[j]) <= communication_range:
                a[i, j] = a[j, i] = 1
    np.fill_diagonal(a, 0)
    return a

def neighbors(adjacency, i):
    return list(np.flatnonzero(adjacency[i]))

def connected_components(adjacency):
    n = len(adjacency)
    seen = set()
    components = []
    for start in range(n):
        if start in seen:
            continue
        stack = [start]
        comp = []
        seen.add(start)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in np.flatnonzero(adjacency[u]):
                if int(v) not in seen:
                    seen.add(int(v))
                    stack.append(int(v))
        components.append(comp)
    return components

def is_connected(adjacency):
    return len(connected_components(adjacency)) <= 1

def mean_link_connectivity(adjacency):
    n = len(adjacency)
    if n < 2:
        return 1.0
    return float(np.sum(adjacency) / (n * (n - 1)))
