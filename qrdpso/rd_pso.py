import numpy as np

class RDPSO:
    """Compact PSO-style waypoint optimizer used as the baseline.

    This is an engineering baseline for the simulation. It is not a claim
    to reproduce a paper's exact RDPSO implementation unless its equations
    are supplied.
    """
    def __init__(self, seed=7, inertia=0.55, cognitive=1.2, social=1.4):
        self.rng = np.random.default_rng(seed)
        self.w = inertia
        self.c1 = cognitive
        self.c2 = social

    def optimize(self, current_positions, targets, iterations=8):
        x = np.asarray(current_positions, dtype=float)
        g = np.asarray(targets, dtype=float)
        n = len(x)
        particles = x[:, None, :] + self.rng.normal(0, 0.4, (n, n, 3))
        velocity = np.zeros_like(particles)
        pbest = particles.copy()
        pbest_cost = np.linalg.norm(particles - g[None, :, :], axis=2)
        best_idx = np.argmin(pbest_cost, axis=1)
        gbest = np.array([pbest[i, best_idx[i]] for i in range(n)])

        for _ in range(iterations):
            r1 = self.rng.random(particles.shape)
            r2 = self.rng.random(particles.shape)
            velocity = self.w*velocity + self.c1*r1*(pbest-particles) + self.c2*r2*(gbest[:,None,:]-particles)
            particles += velocity
            cost = np.linalg.norm(particles - g[None, :, :], axis=2)
            mask = cost < pbest_cost
            pbest[mask] = particles[mask]
            pbest_cost[mask] = cost[mask]
            for i in range(n):
                k = int(np.argmin(pbest_cost[i]))
                gbest[i] = pbest[i, k]
        return gbest
