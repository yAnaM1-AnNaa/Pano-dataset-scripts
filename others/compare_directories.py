#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import hashlib
import os
from collections import defaultdict
from pathlib import Path


def get_file_hash(file_path, chunk_size=8192):
    h = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def scan_directory(directory, extensions=None, recursive=True):
    directory = Path(directory)
    files_by_type = defaultdict(dict)
    if not directory.exists():
        print(f"Warning: directory does not exist: {directory}")
        return files_by_type

    pattern = "**/*" if recursive else "*"
    file_count = 0
    matched_count = 0

    for file_path in directory.glob(pattern):
        if not file_path.is_file():
            continue
        file_count += 1
        ext = file_path.suffix.lower()
        if extensions and ext not in extensions:
            continue
        matched_count += 1
        files_by_type[ext][file_path.stem] = {
            "path": str(file_path),
            "name": file_path.name,
            "stem": file_path.stem,
            "size": file_path.stat().st_size,
            "relative_path": str(file_path.relative_to(directory)),
        }

    print(f"  Scanned {file_count} file(s), matched {matched_count}")
    if extensions:
        print(f"  Extension filter: {', '.join(extensions)}")
    if files_by_type:
        for ext, files in files_by_type.items():
            print(f"    {ext}: {len(files)} file(s)")
    else:
        print("  No matching files found")
    return files_by_type


def compare_directories(dir1, dir2, extensions=None, recursive=True, compare_mode="name", calculate_hash=False):
    print(f"Scanning dir1: {dir1}")
    files1 = scan_directory(dir1, extensions, recursive)
    print(f"Scanning dir2: {dir2}")
    files2 = scan_directory(dir2, extensions, recursive)

    all_extensions = set(files1.keys()) | set(files2.keys())
    results = {}

    for ext in sorted(all_extensions):
        ext_files1 = files1.get(ext, {})
        ext_files2 = files2.get(ext, {})
        if calculate_hash or compare_mode == "hash":
            for file_dict in [ext_files1, ext_files2]:
                for info in file_dict.values():
                    info["hash"] = get_file_hash(info["path"])

        only_in_dir1 = set(ext_files1) - set(ext_files2)
        only_in_dir2 = set(ext_files2) - set(ext_files1)
        common = set(ext_files1) & set(ext_files2)
        same_files = []
        different_files = []

        for name in common:
            f1 = ext_files1[name]
            f2 = ext_files2[name]
            if compare_mode == "name":
                is_same = True
            elif compare_mode == "size":
                is_same = f1["size"] == f2["size"]
            else:
                is_same = f1.get("hash") and f2.get("hash") and f1["hash"] == f2["hash"]
            if is_same:
                same_files.append(name)
            else:
                different_files.append({"filename": name, "dir1": f1, "dir2": f2})

        results[ext] = {
            "only_in_dir1": [(n, ext_files1[n]) for n in only_in_dir1],
            "only_in_dir2": [(n, ext_files2[n]) for n in only_in_dir2],
            "same_files": [(n, ext_files1[n]) for n in same_files],
            "different_files": different_files,
            "total_dir1": len(ext_files1),
            "total_dir2": len(ext_files2),
        }
    return results


def print_comparison_results(results, dir1, dir2, show_details=False):
    print("\n" + "=" * 80)
    print("Directory comparison results")
    print(f"Directory 1: {dir1}")
    print(f"Directory 2: {dir2}")
    print("=" * 80)

    total_only_dir1 = 0
    total_only_dir2 = 0
    total_same = 0
    total_different = 0
    total_files_dir1 = 0
    total_files_dir2 = 0

    for ext, data in results.items():
        only_dir1_count = len(data["only_in_dir1"])
        only_dir2_count = len(data["only_in_dir2"])
        same_count = len(data["same_files"])
        different_count = len(data["different_files"])
        total_only_dir1 += only_dir1_count
        total_only_dir2 += only_dir2_count
        total_same += same_count
        total_different += different_count
        total_files_dir1 += data["total_dir1"]
        total_files_dir2 += data["total_dir2"]

        print(f"\n{ext} files")
        print(f"  Total: dir1({data['total_dir1']}) vs dir2({data['total_dir2']})")
        print(f"  Same: {same_count}")
        print(f"  Different: {different_count}")
        print(f"  Only in dir1: {only_dir1_count}")
        print(f"  Only in dir2: {only_dir2_count}")

        if show_details:
            if data["only_in_dir1"]:
                print(f"    Only in dir1 ({ext}):")
                for name, _ in data["only_in_dir1"][:10]:
                    print(f"      - {name}")
                if len(data["only_in_dir1"]) > 10:
                    print(f"      ... and {len(data['only_in_dir1']) - 10} more file(s)")
            if data["only_in_dir2"]:
                print(f"    Only in dir2 ({ext}):")
                for name, _ in data["only_in_dir2"][:10]:
                    print(f"      - {name}")
                if len(data["only_in_dir2"]) > 10:
                    print(f"      ... and {len(data['only_in_dir2']) - 10} more file(s)")
            if data["different_files"]:
                print(f"    Different-content files ({ext}):")
                for item in data["different_files"][:5]:
                    print(f"      - {item['filename']} (size: {item['dir1']['size']} vs {item['dir2']['size']})")

    print("\nOverall summary:")
    print(f"  Total files: dir1({total_files_dir1}) vs dir2({total_files_dir2})")
    print(f"  Same files: {total_same}")
    print(f"  Different files: {total_different}")
    print(f"  Only in dir1: {total_only_dir1}")
    print(f"  Only in dir2: {total_only_dir2}")


def save_detailed_report(results, output_file, dir1, dir2):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Directory comparison report\n")
        f.write(f"Directory 1: {dir1}\n")
        f.write(f"Directory 2: {dir2}\n")
        f.write("=" * 80 + "\n\n")
        for ext, data in results.items():
            f.write(f"{ext} files (dir1: {data['total_dir1']}, dir2: {data['total_dir2']})\n")
            f.write("-" * 40 + "\n")
            f.write(f"Only in dir1 ({len(data['only_in_dir1'])}):\n")
            for name, info in data["only_in_dir1"]:
                f.write(f"  {name} ({info['size']} bytes)\n")
            f.write(f"\nOnly in dir2 ({len(data['only_in_dir2'])}):\n")
            for name, info in data["only_in_dir2"]:
                f.write(f"  {name} ({info['size']} bytes)\n")
            if data["different_files"]:
                f.write(f"\nDifferent content ({len(data['different_files'])}):\n")
                for item in data["different_files"]:
                    f.write(f"  {item['filename']}\n")
            f.write("\n" + "=" * 80 + "\n\n")
    print(f"Detailed report saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Compare files between two directories.")
    parser.add_argument("--dir1", help="First directory path")
    parser.add_argument("--dir2", help="Second directory path")
    parser.add_argument("--extensions", "-e", nargs="+", help="File extensions to compare, e.g. .jpg .png")
    parser.add_argument("--recursive", "-r", action="store_true", default=True)
    parser.add_argument("--no-recursive", action="store_true")
    parser.add_argument("--compare-mode", "-m", choices=["name", "size", "hash"], default="name")
    parser.add_argument("--details", "-d", action="store_true")
    parser.add_argument("--list-only", "-l", action="store_true")
    parser.add_argument("--output", "-o", help="Save detailed report to file")
    args = parser.parse_args()

    if not args.list_only:
        if not args.dir1 or not os.path.isdir(args.dir1):
            print(f"Error: directory1 does not exist: '{args.dir1}'")
            return
        if not args.dir2 or not os.path.isdir(args.dir2):
            print(f"Error: directory2 does not exist: '{args.dir2}'")
            return
    else:
        if args.dir1 and not os.path.isdir(args.dir1):
            print(f"Error: directory1 does not exist: '{args.dir1}'")
            return
        if args.dir2 and not os.path.isdir(args.dir2):
            print(f"Error: directory2 does not exist: '{args.dir2}'")
            return

    extensions = None
    if args.extensions:
        extensions = [e if e.startswith(".") else f".{e}" for e in args.extensions]
        print(f"Compare extensions: {', '.join(extensions)}")

    recursive = args.recursive and not args.no_recursive
    print(f"Recursive scan: {'Yes' if recursive else 'No'}")

    if args.list_only:
        print("\nListing directory contents:")
        if args.dir1:
            print(f"\nDirectory 1: {args.dir1}")
            scan_directory(args.dir1, extensions, recursive)
        if args.dir2:
            print(f"\nDirectory 2: {args.dir2}")
            scan_directory(args.dir2, extensions, recursive)
        return

    calculate_hash = args.compare_mode == "hash"
    results = compare_directories(
        args.dir1,
        args.dir2,
        extensions=extensions,
        recursive=recursive,
        compare_mode=args.compare_mode,
        calculate_hash=calculate_hash,
    )
    print_comparison_results(results, args.dir1, args.dir2, args.details)
    if args.output:
        save_detailed_report(results, args.output, args.dir1, args.dir2)


if __name__ == "__main__":
    main()
