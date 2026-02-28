#!/usr/bin/env python
"""Pipeline runner for json-shrink -> json-convert -> json to png mask -> viz."""

import argparse
import json
import os
import sys

from util import shrink_polygon as shrink_mod
from util import convert_polygon_to_points as convert_mod
from util import generate_gaussian_mask as mask_mod
from util import visualize_mask as viz_mod


def ensure_dir(path: str) -> None:
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def cmd_json_shrink(args: argparse.Namespace) -> int:
    ensure_dir(args.output)
    if not args.config:
        args.config = os.path.join(args.output, 'Shrink_config.json')
    ensure_dir(os.path.dirname(args.config) if args.config else '')
    shrink_mod.process_directory_recursive(
        args.input,
        args.output,
        args.distance,
        args.config,
        min_area_ratio=args.min_area_ratio,
    )
    return 0


def cmd_json_convert(args: argparse.Namespace) -> int:
    ensure_dir(args.output)
    convert_mod.process_folder(args.input, args.output, args.spacing)
    return 0


def cmd_json_png(args: argparse.Namespace) -> int:
    ensure_dir(args.output)
    if not args.config:
        args.config = os.path.join(os.path.dirname(args.output), 'Shrink_config.json')
    with open(args.config, 'r', encoding='utf-8') as f:
        distance_config = json.load(f)
    mask_mod.process_folder_simple(
        args.input,
        args.output,
        distance_config,
        sigma_scale=args.sigma_scale,
        sigma_min=args.sigma_min,
    )
    return 0


def cmd_mask_viz(args: argparse.Namespace) -> int:
    ensure_dir(args.output)
    if os.path.isfile(args.image):
        if not os.path.isfile(args.mask):
            print(f"Mask file not found: {args.mask}")
            return 1
        viz_mod.visualize(args.image, args.mask, args.output, args.alpha)
        return 0
    if os.path.isdir(args.image):
        if not os.path.isdir(args.mask):
            print(f"Mask directory not found: {args.mask}")
            return 1
        viz_mod.process_dir(args.image, args.mask, args.output, BASE_OBJ=[], SEEN_AFF=[], alpha=args.alpha)
        return 0

    print(f"Image path not found: {args.image}")
    return 1


def cmd_run(args: argparse.Namespace) -> int:
    input_dir = args.input
    output_dir = args.output

    shrink_dir = os.path.join(output_dir, 'Shrinked')
    convert_dir = os.path.join(output_dir, 'Spotted')
    mask_dir = os.path.join(output_dir, 'GT')
    viz_dir = os.path.join(output_dir, 'Vis')
    config_path = os.path.join(output_dir, 'Shrink_config.json')

    ensure_dir(output_dir)
    ensure_dir(shrink_dir)
    ensure_dir(convert_dir)
    ensure_dir(mask_dir)
    ensure_dir(viz_dir)

    print('Step 1/4: json-shrink')
    shrink_mod.process_directory_recursive(
        input_dir,
        shrink_dir,
        args.distance,
        config_path,
        min_area_ratio=args.min_area_ratio,
    )

    print('Step 2/4: json-convert')
    convert_mod.process_folder(shrink_dir, convert_dir, args.spacing)

    print('Step 3/4: json-png')
    with open(config_path, 'r', encoding='utf-8') as f:
        distance_config = json.load(f)
    mask_mod.process_folder_simple(
        convert_dir,
        mask_dir,
        distance_config,
        sigma_scale=args.sigma_scale,
        sigma_min=args.sigma_min,
    )

    print('Step 4/4: mask-viz')
    if os.path.isdir(input_dir):
        viz_mod.process_dir(input_dir, mask_dir, viz_dir, BASE_OBJ=[], SEEN_AFF=[], alpha=args.alpha)
    else:
        print(f"Input image directory not found: {input_dir}")
        return 1

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Dataset pipeline (json-shrink -> json-convert -> json-png -> mask-viz).')
    subparsers = parser.add_subparsers(dest='command', required=True)

    shrink_p = subparsers.add_parser('json-shrink', help='Shrink polygons in Labelme json files.')
    shrink_p.add_argument('--input', '-i', default=r'E:\GithubRepository\code_77329\dataset\pre', help='Input json directory.')
    shrink_p.add_argument('--output', '-o', default=r'E:\GithubRepository\code_77329\dataset\pre_shrink', help='Output json directory.')
    shrink_p.add_argument('--distance', '-d', type=float, default=50, help='Shrink distance.')
    shrink_p.add_argument('--min-area-ratio', type=float, default=0.5, help='Minimum kept area ratio after shrinking (0-1).')
    shrink_p.add_argument('--config', '-c', default='', help='Output distance config json path.')
    shrink_p.set_defaults(func=cmd_json_shrink)

    convert_p = subparsers.add_parser('json-convert', help='Convert polygons to dense points.')
    convert_p.add_argument('--input', '-i', default=r'E:\GithubRepository\code_77329\dataset\pre_shrink', help='Input json directory.')
    convert_p.add_argument('--output', '-o', default=r'E:\GithubRepository\code_77329\dataset\pre_spotted', help='Output json directory.')
    convert_p.add_argument('--spacing', '-s', type=float, default=2.0, help='Point spacing.')
    convert_p.set_defaults(func=cmd_json_convert)

    png_p = subparsers.add_parser('json-png', help='Generate gaussian mask pngs from json.')
    png_p.add_argument('--input', '-i', default=r'E:\GithubRepository\code_77329\dataset\pre_spotted', help='Input json directory.')
    png_p.add_argument('--output', '-o', default=r'E:\GithubRepository\code_77329\dataset\pre_gt', help='Output png directory.')
    png_p.add_argument('--config', '-c', default='', help='Distance config json path.')
    png_p.add_argument('--sigma-scale', type=float, default=0.7, help='Sigma scale factor for shrink distance.')
    png_p.add_argument('--sigma-min', type=float, default=0.5, help='Minimum sigma value.')
    png_p.set_defaults(func=cmd_json_png)

    viz_p = subparsers.add_parser('mask-viz', help='Visualize mask overlays.')
    viz_p.add_argument('--image', '-i', default=r'E:\GithubRepository\code_77329\dataset\pre', help='Input image file or directory.')
    viz_p.add_argument('--mask', '-m', default=r'E:\GithubRepository\code_77329\dataset\pre_gt', help='Mask png file or directory.')
    viz_p.add_argument('--output', '-o', default=r'E:\GithubRepository\code_77329\dataset\pre_vis', help='Output file or directory.')
    viz_p.add_argument('--alpha', '-a', type=float, default=0.5, help='Overlay alpha (0-1).')
    viz_p.set_defaults(func=cmd_mask_viz)

    run_p = subparsers.add_parser('run', help='Run full pipeline.')
    run_p.add_argument('--input', '-i', default=r'E:\GithubRepository\code_77329\dataset\pre', help='Input image/json directory.')
    run_p.add_argument('--output', '-o', default=r'E:\GithubRepository\code_77329\dataset\dataset1', help='Output base directory.')
    run_p.add_argument('--distance', '-d', type=float, default=50, help='Shrink distance.')
    run_p.add_argument('--min-area-ratio', type=float, default=0.5, help='Minimum kept area ratio after shrinking (0-1).')
    run_p.add_argument('--spacing', '-s', type=float, default=2.0, help='Point spacing.')
    run_p.add_argument('--sigma-scale', type=float, default=0.7, help='Sigma scale factor for shrink distance.')
    run_p.add_argument('--sigma-min', type=float, default=0.5, help='Minimum sigma value.')
    run_p.add_argument('--alpha', '-a', type=float, default=0.5, help='Overlay alpha (0-1).')
    run_p.set_defaults(func=cmd_run)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
