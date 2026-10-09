# Reserved for the physics-based Crazyflie controller extension.
# The initial experiment uses a Supervisor to move the simulated drones
# deterministically so that QRDPSO can be tested independently of low-level
# flight-control tuning.
#
# Once the algorithm is validated, this controller can be connected to
# Crazyflie's motor/GPS/IMU devices and receive waypoint commands from the
# coordinator through Webots Emitter/Receiver devices.
