#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量文件重命名工具
支持多种重命名模式：关键词替换、添加前后缀、去除数字等
"""

import os
import re
import argparse
from pathlib import Path
import shutil


def rename_files_with_keyword(directory, old_keyword, new_keyword, dry_run=False):
    """
    将文件名中的关键词替换为新关键词
    
    Args:
        directory: 目标目录
        old_keyword: 要替换的旧关键词
        new_keyword: 新关键词
        dry_run: 是否只预览，不实际执行
    """
    renamed_count = 0
    
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if old_keyword in filename:
                old_path = os.path.join(root, filename)
                new_filename = filename.replace(old_keyword, new_keyword)
                new_path = os.path.join(root, new_filename)
                
                if dry_run:
                    print(f"[预览] {filename} -> {new_filename}")
                else:
                    try:
                        os.rename(old_path, new_path)
                        print(f"✓ {filename} -> {new_filename}")
                        renamed_count += 1
                    except OSError as e:
                        print(f"✗ 重命名失败: {filename} - {e}")
    
    return renamed_count


def add_prefix_suffix(directory, prefix="", suffix="", file_pattern="*", dry_run=False):
    """
    为文件名添加前缀或后缀
    
    Args:
        directory: 目标目录
        prefix: 前缀
        suffix: 后缀（在文件扩展名前）
        file_pattern: 文件匹配模式（如 "*.jpg", "*.json"）
        dry_run: 是否只预览
    """
    renamed_count = 0
    directory_path = Path(directory)
    
    for file_path in directory_path.rglob(file_pattern):
        if file_path.is_file():
            old_name = file_path.name
            name_without_ext = file_path.stem
            extension = file_path.suffix
            
            new_name = f"{prefix}{name_without_ext}{suffix}{extension}"
            new_path = file_path.parent / new_name
            
            if dry_run:
                print(f"[预览] {old_name} -> {new_name}")
            else:
                try:
                    file_path.rename(new_path)
                    print(f"✓ {old_name} -> {new_name}")
                    renamed_count += 1
                except OSError as e:
                    print(f"✗ 重命名失败: {old_name} - {e}")
    
    return renamed_count


def remove_digits_from_names(directory, file_pattern="*", dry_run=False):
    """
    从文件名中去除数字
    
    Args:
        directory: 目标目录
        file_pattern: 文件匹配模式
        dry_run: 是否只预览
    """
    renamed_count = 0
    directory_path = Path(directory)
    
    for file_path in directory_path.rglob(file_pattern):
        if file_path.is_file():
            old_name = file_path.name
            name_without_ext = file_path.stem
            extension = file_path.suffix
            
            # 去除数字
            new_name_without_ext = re.sub(r'\d', '', name_without_ext)
            new_name = f"{new_name_without_ext}{extension}"
            
            # 如果名称有变化才重命名
            if new_name != old_name:
                new_path = file_path.parent / new_name
                
                if dry_run:
                    print(f"[预览] {old_name} -> {new_name}")
                else:
                    try:
                        file_path.rename(new_path)
                        print(f"✓ {old_name} -> {new_name}")
                        renamed_count += 1
                    except OSError as e:
                        print(f"✗ 重命名失败: {old_name} - {e}")
    
    return renamed_count


def rename_with_regex(directory, pattern, replacement, file_pattern="*", dry_run=False):
    """
    使用正则表达式重命名文件
    
    Args:
        directory: 目标目录
        pattern: 正则表达式模式
        replacement: 替换字符串
        file_pattern: 文件匹配模式
        dry_run: 是否只预览
    """
    renamed_count = 0
    directory_path = Path(directory)
    
    for file_path in directory_path.rglob(file_pattern):
        if file_path.is_file():
            old_name = file_path.name
            name_without_ext = file_path.stem
            extension = file_path.suffix
            
            # 应用正则替换
            new_name_without_ext = re.sub(pattern, replacement, name_without_ext)
            new_name = f"{new_name_without_ext}{extension}"
            
            # 如果名称有变化才重命名
            if new_name != old_name:
                new_path = file_path.parent / new_name
                
                if dry_run:
                    print(f"[预览] {old_name} -> {new_name}")
                else:
                    try:
                        file_path.rename(new_path)
                        print(f"✓ {old_name} -> {new_name}")
                        renamed_count += 1
                    except OSError as e:
                        print(f"✗ 重命名失败: {old_name} - {e}")
    
    return renamed_count


def standardize_names(directory, file_pattern="*", dry_run=False):
    """
    标准化文件名：小写、替换空格为下划线、去除特殊字符
    
    Args:
        directory: 目标目录
        file_pattern: 文件匹配模式
        dry_run: 是否只预览
    """
    renamed_count = 0
    directory_path = Path(directory)
    
    for file_path in directory_path.rglob(file_pattern):
        if file_path.is_file():
            old_name = file_path.name
            name_without_ext = file_path.stem
            extension = file_path.suffix
            
            # 标准化处理
            new_name_without_ext = name_without_ext.lower()  # 转小写
            new_name_without_ext = re.sub(r'\s+', '_', new_name_without_ext)  # 空格替换为下划线
            new_name_without_ext = re.sub(r'[^\w\-_]', '', new_name_without_ext)  # 去除特殊字符
            
            new_name = f"{new_name_without_ext}{extension.lower()}"
            
            # 如果名称有变化才重命名
            if new_name != old_name:
                new_path = file_path.parent / new_name
                
                if dry_run:
                    print(f"[预览] {old_name} -> {new_name}")
                else:
                    try:
                        file_path.rename(new_path)
                        print(f"✓ {old_name} -> {new_name}")
                        renamed_count += 1
                    except OSError as e:
                        print(f"✗ 重命名失败: {old_name} - {e}")
    
    return renamed_count


def main():
    parser = argparse.ArgumentParser(description='批量文件重命名工具')
    parser.add_argument('--directory', '-d', default='.', help='目标目录（默认当前目录）')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际执行重命名')
    parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子目录')
    parser.add_argument('--pattern', '-p', default='*', help='文件匹配模式（如 *.jpg）')
    
    # 重命名模式选择
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--replace-keyword', nargs=2, metavar=('OLD', 'NEW'),
                           help='替换关键词：--replace-keyword 旧词 新词')
    mode_group.add_argument('--add-prefix', metavar='PREFIX', help='添加前缀')
    mode_group.add_argument('--add-suffix', metavar='SUFFIX', help='添加后缀（在扩展名前）')
    mode_group.add_argument('--remove-digits', action='store_true', help='去除文件名中的数字')
    mode_group.add_argument('--regex', nargs=2, metavar=('PATTERN', 'REPLACEMENT'),
                           help='正则表达式替换：--regex "模式" "替换"')
    mode_group.add_argument('--standardize', action='store_true', help='标准化文件名')
    
    args = parser.parse_args()
    
    # 检查目录是否存在
    if not os.path.isdir(args.directory):
        print(f"错误：目录 {args.directory} 不存在")
        return
    
    print(f"处理目录: {args.directory}")
    print(f"文件模式: {args.pattern}")
    print(f"递归处理: {'是' if args.recursive else '否'}")
    print(f"预览模式: {'是' if args.dry_run else '否'}")
    print("-" * 50)
    
    renamed_count = 0
    
    # 根据选择的模式执行相应操作
    if args.replace_keyword:
        old_keyword, new_keyword = args.replace_keyword
        print(f"替换关键词: '{old_keyword}' -> '{new_keyword}'")
        renamed_count = rename_files_with_keyword(args.directory, old_keyword, new_keyword, args.dry_run)
    
    elif args.add_prefix:
        print(f"添加前缀: '{args.add_prefix}'")
        renamed_count = add_prefix_suffix(args.directory, prefix=args.add_prefix, 
                                        file_pattern=args.pattern, dry_run=args.dry_run)
    
    elif args.add_suffix:
        print(f"添加后缀: '{args.add_suffix}'")
        renamed_count = add_prefix_suffix(args.directory, suffix=args.add_suffix, 
                                        file_pattern=args.pattern, dry_run=args.dry_run)
    
    elif args.remove_digits:
        print("去除文件名中的数字")
        renamed_count = remove_digits_from_names(args.directory, args.pattern, args.dry_run)
    
    elif args.regex:
        pattern, replacement = args.regex
        print(f"正则表达式替换: '{pattern}' -> '{replacement}'")
        renamed_count = rename_with_regex(args.directory, pattern, replacement, 
                                        args.pattern, args.dry_run)
    
    elif args.standardize:
        print("标准化文件名")
        renamed_count = standardize_names(args.directory, args.pattern, args.dry_run)
    
    print("-" * 50)
    if args.dry_run:
        print(f"预览完成，共找到 {renamed_count} 个需要重命名的文件")
        print("运行时去掉 --dry-run 参数来实际执行重命名")
    else:
        print(f"重命名完成，共处理 {renamed_count} 个文件")


if __name__ == '__main__':
    main()