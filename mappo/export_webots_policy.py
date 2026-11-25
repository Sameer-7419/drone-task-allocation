"""Convert a trained PyTorch MAPPO checkpoint into a Webots NumPy actor file.

Example:
    python -m mappo.export_webots_policy --checkpoint results/models/ac_mappo_seed_7.pt
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import torch


def export_actor(checkpoint_path: Path, output_path: Path) -> None:
    try:
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    except TypeError:
        checkpoint = torch.load(checkpoint_path, map_location="cpu")
    state = checkpoint["actor"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        layer1_weight=state["network.0.weight"].detach().cpu().numpy(),
        layer1_bias=state["network.0.bias"].detach().cpu().numpy(),
        layer2_weight=state["network.2.weight"].detach().cpu().numpy(),
        layer2_bias=state["network.2.bias"].detach().cpu().numpy(),
        output_weight=state["network.4.weight"].detach().cpu().numpy(),
        output_bias=state["network.4.bias"].detach().cpu().numpy(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.checkpoint.with_suffix(".npz")
    export_actor(args.checkpoint, output)
    print(f"Created NumPy-only Webots MAPPO policy: {output}")


if __name__ == "__main__":
    main()
