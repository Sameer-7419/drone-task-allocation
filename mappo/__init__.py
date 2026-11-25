"""Centralized-training, decentralized-execution MAPPO implementation.

Imports are deliberately lazy: Webots uses a NumPy-only inference helper and
must not require PyTorch simply to import a submodule of this package.
"""

__all__ = ["MAPPOConfig", "MAPPOTrainer"]


def __getattr__(name):
    if name == "MAPPOConfig":
        from .config import MAPPOConfig
        return MAPPOConfig
    if name == "MAPPOTrainer":
        from .trainer import MAPPOTrainer
        return MAPPOTrainer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
