#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


def remove_digits(text: str) -> str:
    return re.sub(r"\d", "", text)


def generate_mask_from_json(json_path, output_path, distance_config: dict, config_key=None):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    image_width = data.get("imageWidth")
    image_height = data.get("imageHeight")
    if image_width is None or image_height is None:
        print(f"  {json_path} lacks image size info; skipped.")
        return False

    mask = np.zeros((image_height, image_width), dtype=np.float32)
    shapes = data.get("shapes", [])
    if config_key is None:
        config_key = os.path.basename(json_path)
    config_key = config_key.replace("\\", "/")

    for idx, shape in enumerate(shapes):
        shape_type = shape.get("shape_type", "")
        label = shape.get("label", "unknown")
        points = shape.get("points", [])
        if shape_type not in ["points", "point"] or len(points) < 1:
            continue

        print(f"Generating mask '{label}': {len(points)} dots")
        shrink_dist = float(distance_config[config_key][idx])
        sigma = max(0.5, shrink_dist * 0.7)
        print(f"Generating '{label}': {len(points)} dots, dist={shrink_dist:.1f}, sigma={sigma:.2f}")

        shape_mask = np.zeros((image_height, image_width), dtype=np.float32)
        for point in points:
            px, py = int(round(point[0])), int(round(point[1]))
            if 0 <= px < image_width and 0 <= py < image_height:
                shape_mask[py, px] = 1.0

        blurred = gaussian_filter(shape_mask, sigma=sigma, mode="constant")
        blurred = np.clip(blurred, 0.0, 1.0)
        mask = np.maximum(mask, blurred)

    if mask.max() > 0:
        mask = (mask / mask.max()) * 255
        mask = np.clip(mask, 0, 255)

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    Image.fromarray(mask.astype(np.uint8), mode="L").save(output_path)
    return True


def process_folder(input_folder, output_folder, BASE_OBJ, SEEN_AFF, NOVEL_OBJ, UNSEEN_AFF, distance_config):
    os.makedirs(output_folder, exist_ok=True)
    json_files = []
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.endswith(".json"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, input_folder)
                json_files.append((full_path, rel_path))

    if not json_files:
        print(f"No JSON files found under {input_folder}")
        return

    print(f"Found {len(json_files)} JSON files (including subdirectories)")
    success_count = 0
    fail_count = 0

    for input_path, rel_path in sorted(json_files):
        output_filename = os.path.splitext(rel_path)[0] + ".png"
        output_path = os.path.join(output_folder, output_filename)
        obj = remove_digits(output_path.replace("\\", "/").split("/")[-1].split(".")[0])

        try:
            aff_index = BASE_OBJ.index(obj)
            aff = SEEN_AFF[aff_index]
            output_path = os.path.join(output_folder, aff, obj, output_filename)
        except ValueError:
            print(f"  Warning: '{obj}' is not in BASE_OBJ; saving directly under output root")
            output_path = os.path.join(output_folder, output_filename)

        try:
            if generate_mask_from_json(input_path, output_path, distance_config, config_key=rel_path):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  Error processing file: '{output_path}'")
            print(f"    Details: {type(e).__name__}: {e}")
            import traceback
            print(f"    Trace: {traceback.format_exc().splitlines()[-2].strip()}")
            fail_count += 1

    print(f"\nFinished. Success {success_count}, Fail {fail_count}")
    print(f"Saved under: {output_folder}")


def process_folder_simple(input_folder, output_folder, distance_config):
    os.makedirs(output_folder, exist_ok=True)
    json_files = []
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.endswith(".json"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, input_folder)
                json_files.append((full_path, rel_path))

    if not json_files:
        print(f"No json files found under {input_folder}")
        return

    print(f"Processing {len(json_files)} json files")
    success_count = 0
    fail_count = 0

    for input_path, rel_path in sorted(json_files):
        output_filename = os.path.splitext(rel_path)[0] + ".png"
        output_path = os.path.join(output_folder, output_filename)
        try:
            if generate_mask_from_json(input_path, output_path, distance_config, config_key=rel_path):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  Error generating mask: {input_path}")
            print(f"    {type(e).__name__}: {e}")
            fail_count += 1

    print(f"\nFinished. Success {success_count}, Fail {fail_count}")
    print(f"Saved under: {output_folder}")


def main():
    parser = argparse.ArgumentParser(description="Generate gaussian mask PNGs from point JSON files.")
    parser.add_argument("--input", "-i", default="/root/autodl-tmp/OOAL/data/source/backrest")
    parser.add_argument("--output", "-o", default="./data/temps/GT")
    parser.add_argument("--config", "-c", default="./data/temps/GT/distance_config.json")
    args = parser.parse_args()

    from data import BASE_OBJ, SEEN_AFF, NOVEL_OBJ, UNSEEN_AFF

    if not os.path.exists(args.output):
        os.makedirs(args.output)
        print(f"Output folder does not exist. Created output folder: {args.output}")

    with open(args.config, "r", encoding="utf-8") as f:
        distance_config = json.load(f)
    process_folder(args.input, args.output, BASE_OBJ, SEEN_AFF, NOVEL_OBJ, UNSEEN_AFF, distance_config)


if __name__ == "__main__":
    main()
