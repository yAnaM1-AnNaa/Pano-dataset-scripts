import argparse
import os
import re
import shutil
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
        help="Folder containing per-object PNG masks.",
    )
    parser.add_argument(
        "--output_npy_dir",
        required=True,
        help="Output folder for generated .npy files.",
    )
    parser.add_argument(
        "--temp_folder",
        required=True,
        help="Temporary folder for intermediate PNGs.",
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


def clear_folder_contents(folder_path):
    folder_path = Path(folder_path)
    if not folder_path.exists():
        folder_path.mkdir(parents=True, exist_ok=True)
        return
    for entry in folder_path.iterdir():
        if entry.is_file() or entry.is_symlink():
            entry.unlink()
        elif entry.is_dir():
            shutil.rmtree(entry)


def load_png_as_mask(png_path, target_shape=None):
    img = cv2.imread(str(png_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Failed to read image: {png_path}")
    if target_shape is not None and img.shape != target_shape:
        img = cv2.resize(img, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_NEAREST)
    return img.astype(np.uint8)


def write_black_pngs(temp_folder, count, mask_size):
    os.makedirs(temp_folder, exist_ok=True)
    for idx in range(count):
        black_img = np.zeros(mask_size, dtype=np.uint8)
        out_path = os.path.join(temp_folder, f"{idx}.png")
        cv2.imwrite(out_path, black_img)


def main():
    args = parse_args()
    png_folder = Path(args.png_folder)
    output_npy_dir = Path(args.output_npy_dir)
    temp_folder = Path(args.temp_folder)
    mask_size = (args.mask_size[0], args.mask_size[1])

    affordance_list = SEEN_AFF
    affordance_by_obj = dict(zip(BASE_OBJ, SEEN_AFF))

    mask_files = sorted([f for f in png_folder.rglob("*.png") if f.is_file()])
    if not mask_files:
        print(f"No PNG files found in {png_folder}")
        return

    for mask_path in mask_files:
        clear_folder_contents(temp_folder)

        write_black_pngs(temp_folder, len(affordance_list), mask_size)

        rel_path = mask_path.relative_to(png_folder)
        stem = mask_path.stem
        obj_name = normalize_object_name(stem)
        aff = affordance_by_obj.get(obj_name)
        temp_mask_path = temp_folder / mask_path.name
        shutil.copy2(mask_path, temp_mask_path)

        if aff in affordance_list:
            idx = affordance_list.index(aff)
            target_black = temp_folder / f"{idx}.png"
            if target_black.exists():
                target_black.unlink()
            shutil.move(str(temp_mask_path), str(target_black))
            print(f"Replaced {mask_path.name} -> {idx}.png (affordance: {aff})")
        else:
            print(
                f"No affordance mapping for {mask_path.name} "
                f"(normalized object: {obj_name}); skipping."
            )
            if temp_mask_path.exists():
                temp_mask_path.unlink()
            continue

        output_npy_dir.mkdir(parents=True, exist_ok=True)
        masks = []
        for idx in range(len(affordance_list)):
            mask_file = temp_folder / f"{idx}.png"
            if not mask_file.exists():
                mask = np.zeros(mask_size, dtype=np.uint8)
            else:
                mask = load_png_as_mask(mask_file, target_shape=mask_size)
            masks.append(mask)
        affordance_masks = np.stack(masks, axis=0).astype(np.float32)
        npy_rel_path = rel_path.with_name(f"{obj_name}.npy")
        npy_save_path = output_npy_dir / npy_rel_path
        npy_save_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(npy_save_path, affordance_masks)
        print(
            f"Saved {npy_save_path} shape={affordance_masks.shape} "
            f"dtype={affordance_masks.dtype}"
        )


if __name__ == "__main__":
    main()
