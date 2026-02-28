import argparse
import re
from pathlib import Path

import cv2
import numpy as np

from util.data import BASE_OBJ, SEEN_AFF


def normalize_object_name(stem: str) -> str:
    # bathtub83 -> bathtub, chair_001 -> chair
    obj = re.sub(r"\d+", "", stem)
    obj = obj.rstrip("_- ")
    return obj


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert per-object PNG masks into stacked NPY affordance masks."
    )
    parser.add_argument(
        "--png_folder",
        required=True,
        help="Folder containing per-object PNG masks (recursive).",
    )
    parser.add_argument(
        "--output_npy_dir",
        required=True,
        help="Output folder for generated .npy files.",
    )
    parser.add_argument(
        "--mask_size",
        nargs=2,
        type=int,
        default=[1024, 2048],
        metavar=("H", "W"),
        help="Mask size as H W. Default: 1024 2048.",
    )
    return parser.parse_args()


def load_png_as_mask(png_path: Path, target_shape):
    img = cv2.imread(str(png_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Failed to read image: {png_path}")
    if img.shape != target_shape:
        img = cv2.resize(img, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_NEAREST)
    return img.astype(np.float32)


def main():
    args = parse_args()
    png_folder = Path(args.png_folder)
    output_npy_dir = Path(args.output_npy_dir)
    mask_size = (args.mask_size[0], args.mask_size[1])

    affordance_list = SEEN_AFF
    affordance_by_obj = dict(zip(BASE_OBJ, SEEN_AFF))
    aff_to_index = {aff: i for i, aff in enumerate(affordance_list)}

    mask_files = sorted([f for f in png_folder.rglob("*.png") if f.is_file()])
    if not mask_files:
        print(f"No PNG files found in {png_folder}")
        return

    for mask_path in mask_files:
        rel_path = mask_path.relative_to(png_folder)
        stem = mask_path.stem
        obj_name = normalize_object_name(stem)
        aff = affordance_by_obj.get(obj_name)

        if aff not in aff_to_index:
            print(
                f"No affordance mapping for {mask_path.name} "
                f"(normalized object: {obj_name}); skipping."
            )
            continue

        # Pure in-memory assembly: initialize all channels to zero and fill one mapped channel.
        affordance_masks = np.zeros((len(affordance_list), mask_size[0], mask_size[1]), dtype=np.float32)
        channel_idx = aff_to_index[aff]
        affordance_masks[channel_idx] = load_png_as_mask(mask_path, target_shape=mask_size)

        npy_rel_path = rel_path.with_name(f"{obj_name}.npy")
        npy_save_path = output_npy_dir / npy_rel_path
        npy_save_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(npy_save_path, affordance_masks)
        print(
            f"Saved {npy_save_path} shape={affordance_masks.shape} "
            f"dtype={affordance_masks.dtype} aff={aff}"
        )


if __name__ == "__main__":
    main()
