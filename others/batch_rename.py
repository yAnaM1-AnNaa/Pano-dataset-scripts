#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import re
from pathlib import Path


def rename_files_with_keyword(directory, old_keyword, new_keyword, dry_run=False):
    renamed_count = 0
    for root, _, files in os.walk(directory):
        for filename in files:
            if old_keyword not in filename:
                continue
            old_path = os.path.join(root, filename)
            new_filename = filename.replace(old_keyword, new_keyword)
            new_path = os.path.join(root, new_filename)
            if dry_run:
                print(f"[DRY RUN] {filename} -> {new_filename}")
            else:
                try:
                    os.rename(old_path, new_path)
                    print(f"[OK] {filename} -> {new_filename}")
                    renamed_count += 1
                except OSError as e:
                    print(f"[ERROR] rename failed: {filename} - {e}")
    return renamed_count


def add_prefix_suffix(directory, prefix="", suffix="", file_pattern="*", dry_run=False):
    renamed_count = 0
    for file_path in Path(directory).rglob(file_pattern):
        if not file_path.is_file():
            continue
        old_name = file_path.name
        new_name = f"{prefix}{file_path.stem}{suffix}{file_path.suffix}"
        new_path = file_path.parent / new_name
        if dry_run:
            print(f"[DRY RUN] {old_name} -> {new_name}")
        else:
            try:
                file_path.rename(new_path)
                print(f"[OK] {old_name} -> {new_name}")
                renamed_count += 1
            except OSError as e:
                print(f"[ERROR] rename failed: {old_name} - {e}")
    return renamed_count


def remove_digits_from_names(directory, file_pattern="*", dry_run=False):
    renamed_count = 0
    for file_path in Path(directory).rglob(file_pattern):
        if not file_path.is_file():
            continue
        old_name = file_path.name
        new_name = f"{re.sub(r'\\d', '', file_path.stem)}{file_path.suffix}"
        if new_name == old_name:
            continue
        new_path = file_path.parent / new_name
        if dry_run:
            print(f"[DRY RUN] {old_name} -> {new_name}")
        else:
            try:
                file_path.rename(new_path)
                print(f"[OK] {old_name} -> {new_name}")
                renamed_count += 1
            except OSError as e:
                print(f"[ERROR] rename failed: {old_name} - {e}")
    return renamed_count


def rename_with_regex(directory, pattern, replacement, file_pattern="*", dry_run=False):
    renamed_count = 0
    for file_path in Path(directory).rglob(file_pattern):
        if not file_path.is_file():
            continue
        old_name = file_path.name
        new_name = f"{re.sub(pattern, replacement, file_path.stem)}{file_path.suffix}"
        if new_name == old_name:
            continue
        new_path = file_path.parent / new_name
        if dry_run:
            print(f"[DRY RUN] {old_name} -> {new_name}")
        else:
            try:
                file_path.rename(new_path)
                print(f"[OK] {old_name} -> {new_name}")
                renamed_count += 1
            except OSError as e:
                print(f"[ERROR] rename failed: {old_name} - {e}")
    return renamed_count


def standardize_names(directory, file_pattern="*", dry_run=False):
    renamed_count = 0
    for file_path in Path(directory).rglob(file_pattern):
        if not file_path.is_file():
            continue
        old_name = file_path.name
        base = file_path.stem.lower()
        base = re.sub(r"\s+", "_", base)
        base = re.sub(r"[^\w\-_]", "", base)
        new_name = f"{base}{file_path.suffix.lower()}"
        if new_name == old_name:
            continue
        new_path = file_path.parent / new_name
        if dry_run:
            print(f"[DRY RUN] {old_name} -> {new_name}")
        else:
            try:
                file_path.rename(new_path)
                print(f"[OK] {old_name} -> {new_name}")
                renamed_count += 1
            except OSError as e:
                print(f"[ERROR] rename failed: {old_name} - {e}")
    return renamed_count


def main():
    parser = argparse.ArgumentParser(description="Batch file rename tool.")
    parser.add_argument("--directory", "-d", default=".", help="Target directory.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not apply changes.")
    parser.add_argument("--recursive", "-r", action="store_true", help="Reserved for compatibility.")
    parser.add_argument("--pattern", "-p", default="*", help="File glob pattern, e.g. *.jpg")

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--replace-keyword", nargs=2, metavar=("OLD", "NEW"))
    mode_group.add_argument("--add-prefix", metavar="PREFIX")
    mode_group.add_argument("--add-suffix", metavar="SUFFIX")
    mode_group.add_argument("--remove-digits", action="store_true")
    mode_group.add_argument("--regex", nargs=2, metavar=("PATTERN", "REPLACEMENT"))
    mode_group.add_argument("--standardize", action="store_true")
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Error: directory does not exist: {args.directory}")
        return

    print(f"Target directory: {args.directory}")
    print(f"File pattern: {args.pattern}")
    print(f"Recursive: {'Yes' if args.recursive else 'No'}")
    print(f"Dry run: {'Yes' if args.dry_run else 'No'}")
    print("-" * 50)

    renamed_count = 0
    if args.replace_keyword:
        old_keyword, new_keyword = args.replace_keyword
        print(f"Replace keyword: '{old_keyword}' -> '{new_keyword}'")
        renamed_count = rename_files_with_keyword(args.directory, old_keyword, new_keyword, args.dry_run)
    elif args.add_prefix:
        print(f"Add prefix: '{args.add_prefix}'")
        renamed_count = add_prefix_suffix(args.directory, prefix=args.add_prefix, file_pattern=args.pattern, dry_run=args.dry_run)
    elif args.add_suffix:
        print(f"Add suffix: '{args.add_suffix}'")
        renamed_count = add_prefix_suffix(args.directory, suffix=args.add_suffix, file_pattern=args.pattern, dry_run=args.dry_run)
    elif args.remove_digits:
        print("Remove digits from file names")
        renamed_count = remove_digits_from_names(args.directory, args.pattern, args.dry_run)
    elif args.regex:
        pattern, replacement = args.regex
        print(f"Regex replace: '{pattern}' -> '{replacement}'")
        renamed_count = rename_with_regex(args.directory, pattern, replacement, args.pattern, args.dry_run)
    elif args.standardize:
        print("Standardize file names")
        renamed_count = standardize_names(args.directory, args.pattern, args.dry_run)

    print("-" * 50)
    if args.dry_run:
        print(f"Dry run complete, found {renamed_count} file(s) to rename")
        print("Run again without --dry-run to apply changes")
    else:
        print(f"Rename complete, processed {renamed_count} file(s)")


if __name__ == "__main__":
    main()
