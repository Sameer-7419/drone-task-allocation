import numpy as np

class QRDPSO:
    """Neighborhood-aware extension of the baseline PSO.

    IMPORTANT:
    The original transcript references an Eq. 5 baseline and Eq. 6
    neighborhood extension, but the actual paper equations were not
    present in the supplied text. This implementation therefore isolates
    the neighborhood term so the exact equation can be substituted later.
    """
    def __init__(self, seed=7, inertia=0.55, cognitive=1.2, social=1.4, neighborhood=0.8):
        self.rng = np.random.default_rng(seed)
        self.w = inertia
        self.c1 = cognitive
        self.c2 = social
        self.c3 = neighborhood

    def optimize(self, current_positions, targets, adjacency, iterations=8):
        x = np.asarray(current_positions, dtype=float)
        g = np.asarray(targets, dtype=float)
        a = np.asarray(adjacency)
        n = len(x)

        particles = x[:, None, :] + self.rng.normal(0, 0.4, (n, n, 3))
        velocity = np.zeros_like(particles)
        pbest = particles.copy()
        pbest_cost = np.linalg.norm(particles - g[None, :, :], axis=2)

        for _ in range(iterations):
            r1 = self.rng.random(particles.shape)
            r2 = self.rng.random(particles.shape)
            for i in range(n):
                local = np.flatnonzero(a[i])
                if len(local):
                    neighborhood_best = np.mean(pbest[local], axis=(0,1))
                else:
                    neighborhood_best = np.mean(pbest[i], axis=0)

                velocity[i] = (
                    self.w * velocity[i]
                    + self.c1 * r1[i] * (pbest[i] - particles[i])
                    + self.c2 * r2[i] * (g - particles[i])
                    + self.c3 * (neighborhood_best - particles[i])
                )

            particles += velocity
            cost = np.linalg.norm(particles - g[None, :, :], axis=2)
            mask = cost < pbest_cost
            pbest[mask] = particles[mask]
            pbest_cost[mask] = cost[mask]

        return np.array([pbest[i, np.argmin(pbest_cost[i])] for i in range(n)])
