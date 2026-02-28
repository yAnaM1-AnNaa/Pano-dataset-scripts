#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def overlay_mask(img, mask, colormap="jet", alpha=0.7):
    cmap = plt.get_cmap(colormap)
    overlay = mask.resize(img.size, resample=Image.BICUBIC)
    mask_normalized = np.asarray(overlay) / 255.0
    overlay = (255 * cmap(mask_normalized)[:, :, :3]).astype(np.uint8)
    out = Image.fromarray((alpha * np.asarray(img) + (1 - alpha) * overlay).astype(np.uint8))
    return out


def visualize(rgb_file_path, mask_file_path, output_path, alpha=0.7):
    if os.path.isdir(output_path):
        base_name = os.path.splitext(os.path.basename(rgb_file_path))[0]
        output_path = os.path.join(output_path, f"{base_name}_vis.png")

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    image = Image.open(rgb_file_path).convert("RGB")
    mask = Image.open(mask_file_path).convert("L")
    result = overlay_mask(image, mask, alpha=alpha)
    result.save(output_path)
    print(f"Saved at {output_path}")


def process_dir(rgb_dir, mask_dir, out_dir, BASE_OBJ, SEEN_AFF, alpha):
    rgb_files = []
    for root, _, files in os.walk(rgb_dir):
        for file in files:
            if file.lower().endswith((".jpg", ".jpeg", ".png")):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, rgb_dir)
                rgb_files.append((full_path, rel_path))

    if not rgb_files:
        print(f"No image files found under {rgb_dir}")
        return

    print(f"Found {len(rgb_files)} image files")
    success_count = 0
    fail_count = 0

    for rgb_path, rel_path in sorted(rgb_files):
        rel_no_ext = os.path.splitext(rel_path)[0]
        mask_path = os.path.join(mask_dir, rel_no_ext + ".png")
        output_path = os.path.join(out_dir, rel_no_ext + "_vis.png")
        if os.path.exists(mask_path):
            visualize(rgb_path, mask_path, output_path, alpha)
            success_count += 1
        else:
            print(f"  Skipped: mask not found {mask_path}")
            fail_count += 1

    print(f"\nDone. Success {success_count}, Failed {fail_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize mask overlays on RGB images.")
    parser.add_argument("-i", "--image", default="/root/autodl-tmp/OOAL/data/source/screen/screen5.jpg")
    parser.add_argument("-m", "--mask", default="/root/autodl-tmp/OOAL/data/temps/2/GT/display/screen/screen5.png")
    parser.add_argument("-o", "--output", default="/root/autodl-tmp/OOAL/data/temps/screen5_vis.png")
    parser.add_argument("-a", "--alpha", type=float, default=0.5)
    args = parser.parse_args()

    from data.agd20k_ego import BASE_OBJ, SEEN_AFF

    if not os.path.exists(args.image):
        print(f"Error: input path does not exist {args.image}")
        raise SystemExit(1)
    if not os.path.exists(args.mask):
        print(f"Error: mask path does not exist {args.mask}")
        raise SystemExit(1)

    if os.path.isfile(args.image):
        if not os.path.isfile(args.mask):
            print("Error: in file mode, -m must be a file path")
            raise SystemExit(1)
        visualize(args.image, args.mask, args.output, args.alpha)
    elif os.path.isdir(args.image):
        if not os.path.isdir(args.mask):
            print("Error: in directory mode, -m must be a directory path")
            raise SystemExit(1)
        process_dir(args.image, args.mask, args.output, BASE_OBJ, SEEN_AFF, args.alpha)
    else:
        print(f"Error: cannot determine type of {args.image}")
        raise SystemExit(1)
