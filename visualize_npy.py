import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from util.data import SEEN_AFF


def parse_args():
    parser = argparse.ArgumentParser(
        description="Visualize stacked affordance masks from .npy files."
    )
    parser.add_argument(
        "--npy_dir",
        required=True,
        help="Directory containing .npy files (recursive).",
    )
    parser.add_argument(
        "--save_dir",
        default="",
        help="Optional output directory to save visualizations. If empty, show interactively.",
    )
    parser.add_argument(
        "--max_files",
        type=int,
        default=0,
        help="Maximum number of .npy files to visualize. 0 means no limit.",
    )
    return parser.parse_args()


def channel_name(index: int) -> str:
    if index < len(SEEN_AFF):
        return SEEN_AFF[index]
    return f"ch_{index}"


def normalize_for_display(img: np.ndarray) -> np.ndarray:
    img = img.astype(np.float32)
    img_min = float(img.min())
    img_max = float(img.max())
    if img_max > img_min:
        img = (img - img_min) / (img_max - img_min)
    return np.clip(img, 0.0, 1.0)


def summarize_channels(array: np.ndarray):
    stats = []
    for i in range(array.shape[0]):
        channel = array[i]
        non_zero_ratio = float(np.count_nonzero(channel)) / float(channel.size)
        stats.append((i, channel_name(i), non_zero_ratio, float(channel.max())))
    return stats


def visualize_channel_first(array: np.ndarray, title: str):
    channels = array.shape[0]
    cols = min(6, channels)
    rows = int(np.ceil(channels / cols))

    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3, rows * 3))
    if not isinstance(axes, np.ndarray):
        axes = np.array([axes])
    axes = axes.flatten()

    fig.suptitle(title, fontsize=12)

    for i in range(channels):
        img = normalize_for_display(array[i])
        aff = channel_name(i)
        axes[i].imshow(img, cmap="gray")
        axes[i].set_title(f"{i}: {aff}", fontsize=8)
        axes[i].axis("off")

    for i in range(channels, len(axes)):
        axes[i].axis("off")

    plt.tight_layout()
    return fig


def process_file(npy_path: Path, save_dir: Path | None, root_dir: Path):
    array = np.load(npy_path)
    rel = npy_path.relative_to(root_dir)
    print(f"\nFile: {rel}")
    print(f"Shape: {array.shape}, dtype: {array.dtype}")
    print(f"Range: [{array.min():.4f}, {array.max():.4f}]")

    if array.ndim == 3:
        stats = summarize_channels(array)
        for idx, aff, ratio, max_val in stats:
            print(f"  ch{idx:02d} {aff:<16} non_zero={ratio:.4%} max={max_val:.4f}")
        fig = visualize_channel_first(array, f"{rel} | shape={array.shape}")
    elif array.ndim == 2:
        fig = plt.figure(figsize=(6, 4))
        plt.imshow(normalize_for_display(array), cmap="gray")
        plt.title(f"{rel} | 2D")
        plt.axis("off")
        plt.tight_layout()
    else:
        print(f"Skip unsupported ndim={array.ndim}")
        return

    if save_dir is None:
        plt.show()
    else:
        out_path = save_dir / rel.with_suffix(".png")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {out_path}")


def main():
    args = parse_args()
    npy_dir = Path(args.npy_dir)
    save_dir = Path(args.save_dir) if args.save_dir else None

    if not npy_dir.exists():
        print(f"Input directory not found: {npy_dir}")
        return

    npy_files = sorted([p for p in npy_dir.rglob("*.npy") if p.is_file()])
    if not npy_files:
        print(f"No .npy files found under: {npy_dir}")
        return

    if args.max_files > 0:
        npy_files = npy_files[: args.max_files]

    print(f"Found {len(npy_files)} .npy file(s)")
    for npy_file in npy_files:
        process_file(npy_file, save_dir, npy_dir)


if __name__ == "__main__":
    main()
