import argparse
import json
import os

import numpy as np
from shapely.geometry import Polygon


def scale_polygon(points: list, scale_factor: float):
    pts = np.array(points)
    center = np.mean(pts, axis=0)
    scaled_pts = center + scale_factor * (pts - center)
    return scaled_pts.tolist()


def shrink_polygon(points, distance, auto_fix=True):
    poly = Polygon(points)
    if not poly.is_valid:
        return points, len(points)

    shrunk_poly = poly.buffer(-distance, join_style=2)
    if shrunk_poly.is_empty:
        return points, 0
    if shrunk_poly.geom_type == "MultiPolygon":
        shrunk_poly = max(shrunk_poly.geoms, key=lambda p: p.area)
    if shrunk_poly.geom_type != "Polygon":
        return points, 0

    x, y = shrunk_poly.exterior.xy
    coords = []
    for i in range(len(x)):
        coords.append([x[i], y[i]])
    new_points = coords[:-1]
    shrunk_len = len(new_points)
    return new_points, shrunk_len


def process_json_file(
    input_path,
    output_path,
    initial_distance,
    distance_dict,
    config_key=None,
    min_area_ratio=0.5,
):
    if config_key is None:
        config_key = os.path.basename(input_path)
    config_key = config_key.replace("\\", "/")

    try:
        distance_dict[config_key] = []
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for i in range(len(data["shapes"])):
            points = data["shapes"][i]["points"]
            res_len = len(points)
            if res_len < 3:
                print(f"  Warning: shape {i} has only {res_len} points (< 3); skipped.")
                continue

            poly = Polygon(points)
            if not poly.is_valid:
                print(f"  Fixing shape {i}.")
                poly = poly.buffer(0)
                if poly.geom_type == "MultiPolygon":
                    poly = max(poly.geoms, key=lambda p: p.area)
                if poly.is_valid and poly.geom_type == "Polygon":
                    x, y = poly.exterior.xy
                    points = [[x[j], y[j]] for j in range(len(x) - 1)]
                else:
                    print(f"  Shape {i}: auto-fix failed, keeping original points.")

            original_area = Polygon(points).area
            current_distance = initial_distance
            new_points = points
            shrunk_len = len(points)

            for _ in range(50):
                new_points, shrunk_len = shrink_polygon(points, current_distance, auto_fix=False)
                if shrunk_len == 0 or current_distance < 0.5:
                    current_distance *= 0.95
                    continue
                shrunk_area = Polygon(new_points).area if shrunk_len > 2 else 0
                if shrunk_area >= original_area * min_area_ratio:
                    break
                current_distance *= 0.95

            data["shapes"][i]["points"] = new_points if shrunk_len > 0 else points
            distance_dict[config_key].append(current_distance)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error processing {input_path}: {str(e)}")
        return False


def process_directory_recursive(input_dir, output_dir, distance, config_path, min_area_ratio=0.5):
    success_count = 0
    error_count = 0
    all_distance_configs = {}

    for root, _, files in os.walk(input_dir):
        for file in files:
            if not file.endswith(".json"):
                continue
            input_file_path = os.path.join(root, file)
            rel_path = os.path.relpath(input_file_path, input_dir)
            output_file_path = os.path.join(output_dir, rel_path)
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
            print(f"Processing {input_file_path}")
            ok = process_json_file(
                input_file_path,
                output_file_path,
                distance,
                all_distance_configs,
                config_key=rel_path,
                min_area_ratio=min_area_ratio,
            )
            if ok:
                print(f"{file} finished")
                success_count += 1
            else:
                error_count += 1

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(all_distance_configs, f, indent=2, ensure_ascii=False)
    print(f"Distance config saved to: {config_path}")
    return success_count, error_count


def main():
    parser = argparse.ArgumentParser(description="Recursively shrink polygons in Labelme JSON files.")
    parser.add_argument(
        "--input",
        "-i",
        default="/root/autodl-tmp/OOAL/data/temps/6/111",
        help="Input directory containing JSON files.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="/root/autodl-tmp/OOAL/data/temps/6/111result",
        help="Output directory for processed JSON files.",
    )
    parser.add_argument("--distance", "-d", type=float, default=50, help="Shrink distance.")
    parser.add_argument(
        "--min-area-ratio",
        type=float,
        default=0.5,
        help="Minimum kept area ratio after shrinking (0-1).",
    )
    parser.add_argument(
        "--config",
        "-c",
        default="/root/autodl-tmp/OOAL/data/temps/6/shrink_config.json",
        help="Output path for shrink distance config JSON.",
    )
    args = parser.parse_args()

    if not os.path.exists(args.output):
        os.makedirs(args.output)
        print(f"Output folder does not exist. Created output folder: {args.output}")

    print(f"Start processing {args.input}")
    print(f"Shrink distance: {args.distance}")
    print(f"Output to: {args.output}")
    success_count, error_count = process_directory_recursive(
        args.input,
        args.output,
        args.distance,
        args.config,
        min_area_ratio=args.min_area_ratio,
    )
    print("-" * 50)
    print(f"Succeeded {success_count}, Failed {error_count}")


if __name__ == "__main__":
    main()
