#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import re
import shutil
from pathlib import Path

from util.data import BASE_OBJ, NOVEL_OBJ, SEEN_AFF, UNSEEN_AFF


IMG_EXTS = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Reorganize pipeline outputs into dataset split folders:\n"
            "dataset/Seen|Unseen/testset/{egocentric,GT}/affordance/object/file"
        )
    )
    parser.add_argument(
        "--pipeline_output",
        required=True,
        help="Pipeline output directory that contains GT/ (and optionally other folders).",
    )
    parser.add_argument(
        "--dataset_root",
        required=True,
        help="Target dataset root directory.",
    )
    parser.add_argument(
        "--rgb_dir",
        default="",
        help="Original RGB directory. If provided, images are copied to egocentric as .jpg.",
    )
    parser.add_argument(
        "--gt_subdir",
        default="GT",
        help="Subdirectory under pipeline_output that contains mask PNGs. Default: GT",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Preview operations without copying files.",
    )
    return parser.parse_args()


def normalize_object_name(stem: str) -> str:
    # bathtub83 -> bathtub, chair_001 -> chair
    obj = re.sub(r"\d+", "", stem)
    obj = obj.rstrip("_- ")
    return obj


def build_rgb_index(rgb_dir: Path):
    index = {}
    for ext in IMG_EXTS:
        for p in rgb_dir.rglob(f"*{ext}"):
            if p.is_file():
                index.setdefault(p.stem, p)
    return index


def resolve_split_and_aff(obj: str):
    seen_map = dict(zip(BASE_OBJ, SEEN_AFF))
    unseen_map = dict(zip(NOVEL_OBJ, UNSEEN_AFF))
    if obj in seen_map:
        return "Seen", seen_map[obj]
    if obj in unseen_map:
        return "Unseen", unseen_map[obj]
    return None, None


def copy_file(src: Path, dst: Path, dry_run: bool):
    if dry_run:
        print(f"[DRY] {src} -> {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main():
    args = parse_args()
    pipeline_output = Path(args.pipeline_output)
    dataset_root = Path(args.dataset_root)
    gt_root = pipeline_output / args.gt_subdir
    rgb_dir = Path(args.rgb_dir) if args.rgb_dir else None

    if not gt_root.exists():
        raise FileNotFoundError(f"GT directory not found: {gt_root}")

    rgb_index = {}
    if rgb_dir:
        if not rgb_dir.exists():
            raise FileNotFoundError(f"RGB directory not found: {rgb_dir}")
        rgb_index = build_rgb_index(rgb_dir)
        print(f"Indexed RGB files: {len(rgb_index)}")

    gt_files = sorted([p for p in gt_root.rglob("*.png") if p.is_file()])
    if not gt_files:
        print(f"No PNG masks found under: {gt_root}")
        return

    print(f"Found GT masks: {len(gt_files)}")

    copied_gt = 0
    copied_rgb = 0
    skipped_no_mapping = 0
    missing_rgb = 0

    for gt_path in gt_files:
        stem = gt_path.stem
        obj = normalize_object_name(stem)
        split, aff = resolve_split_and_aff(obj)
        if split is None:
            skipped_no_mapping += 1
            print(f"[SKIP] no obj->aff mapping for '{stem}' (normalized: '{obj}')")
            continue

        gt_dst = (
            dataset_root
            / split
            / "testset"
            / "GT"
            / aff
            / obj
            / f"{stem}.png"
        )
        copy_file(gt_path, gt_dst, args.dry_run)
        copied_gt += 1

        if rgb_dir:
            rgb_src = rgb_index.get(stem)
            if rgb_src is None:
                missing_rgb += 1
                print(f"[WARN] missing RGB for '{stem}' in {rgb_dir}")
                continue

            rgb_dst = (
                dataset_root
                / split
                / "testset"
                / "egocentric"
                / aff
                / obj
                / f"{stem}.jpg"
            )
            copy_file(rgb_src, rgb_dst, args.dry_run)
            copied_rgb += 1

    print("-" * 50)
    print(f"GT copied: {copied_gt}")
    if rgb_dir:
        print(f"RGB copied: {copied_rgb}")
        print(f"Missing RGB: {missing_rgb}")
    print(f"Skipped (no mapping): {skipped_no_mapping}")


if __name__ == "__main__":
    main()
