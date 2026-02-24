#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件夹差异比较工具
比较两个文件夹中同类文件的差异，支持按文件类型分析
"""

import os
import argparse
from pathlib import Path
from collections import defaultdict
import hashlib


def get_file_hash(file_path, chunk_size=8192):
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return None


def scan_directory(directory, extensions=None, recursive=True):
    """
    扫描目录，按文件类型分组
    
    Args:
        directory: 目录路径
        extensions: 要包含的文件扩展名列表，None表示所有文件
        recursive: 是否递归扫描子目录
        
    Returns:
        dict: {extension: {filename: file_info}} 的嵌套字典
    """
    directory = Path(directory)
    files_by_type = defaultdict(dict)
    
    if not directory.exists():
        print(f"⚠️  警告: 目录 {directory} 不存在")
        return files_by_type
    
    # 选择扫描模式
    if recursive:
        file_pattern = '**/*'
    else:
        file_pattern = '*'
    
    file_count = 0
    matched_count = 0
    
    for file_path in directory.glob(file_pattern):
        if file_path.is_file():
            file_count += 1
            ext = file_path.suffix.lower()
            
            # 过滤文件扩展名
            if extensions and ext not in extensions:
                continue
                
            matched_count += 1
            
            # 文件信息
            file_info = {
                'path': str(file_path),
                'name': file_path.name,
                'stem': file_path.stem,  # 不含扩展名的文件名
                'size': file_path.stat().st_size,
                'relative_path': str(file_path.relative_to(directory))
            }
            
            # 使用文件名（不含扩展名）作为键
            files_by_type[ext][file_path.stem] = file_info
    
    print(f"  📁 扫描到 {file_count} 个文件，匹配 {matched_count} 个")
    if extensions:
        print(f"  🔍 过滤扩展名: {', '.join(extensions)}")
    
    # 显示各类型文件数量
    if files_by_type:
        for ext, files in files_by_type.items():
            print(f"    {ext}: {len(files)} 个文件")
    else:
        print("  ❌ 没有找到匹配的文件")
        if file_count > 0 and extensions:
            print(f"  💡 提示: 找到了文件但扩展名不匹配，尝试不使用 -e 参数看所有文件")
    
    return files_by_type


def compare_directories(dir1, dir2, extensions=None, recursive=True, 
                       compare_mode='name', calculate_hash=False):
    """
    比较两个目录的文件差异
    
    Args:
        dir1, dir2: 要比较的两个目录
        extensions: 要比较的文件扩展名列表
        recursive: 是否递归扫描
        compare_mode: 比较模式 ('name', 'size', 'hash')
        calculate_hash: 是否计算文件哈希值
        
    Returns:
        dict: 比较结果
    """
    print(f"扫描目录1: {dir1}")
    files1 = scan_directory(dir1, extensions, recursive)
    
    print(f"扫描目录2: {dir2}")
    files2 = scan_directory(dir2, extensions, recursive)
    
    # 获取所有文件类型
    all_extensions = set(files1.keys()) | set(files2.keys())
    
    results = {}
    
    for ext in sorted(all_extensions):
        ext_files1 = files1.get(ext, {})
        ext_files2 = files2.get(ext, {})
        
        # 如果需要计算哈希值
        if calculate_hash or compare_mode == 'hash':
            for file_dict in [ext_files1, ext_files2]:
                for file_info in file_dict.values():
                    file_info['hash'] = get_file_hash(file_info['path'])
        
        # 比较文件
        only_in_dir1 = set(ext_files1.keys()) - set(ext_files2.keys())
        only_in_dir2 = set(ext_files2.keys()) - set(ext_files1.keys())
        common_files = set(ext_files1.keys()) & set(ext_files2.keys())
        
        # 分析共同文件的差异
        same_files = []
        different_files = []
        
        for filename in common_files:
            file1_info = ext_files1[filename]
            file2_info = ext_files2[filename]
            
            is_same = False
            
            if compare_mode == 'name':
                is_same = True  # 文件名相同就认为相同
            elif compare_mode == 'size':
                is_same = file1_info['size'] == file2_info['size']
            elif compare_mode == 'hash':
                is_same = (file1_info.get('hash') and file2_info.get('hash') and 
                          file1_info['hash'] == file2_info['hash'])
            
            if is_same:
                same_files.append(filename)
            else:
                different_files.append({
                    'filename': filename,
                    'dir1': file1_info,
                    'dir2': file2_info
                })
        
        results[ext] = {
            'only_in_dir1': [(f, ext_files1[f]) for f in only_in_dir1],
            'only_in_dir2': [(f, ext_files2[f]) for f in only_in_dir2],
            'same_files': [(f, ext_files1[f]) for f in same_files],
            'different_files': different_files,
            'total_dir1': len(ext_files1),
            'total_dir2': len(ext_files2)
        }
    
    return results


def print_comparison_results(results, dir1, dir2, show_details=False):
    """打印比较结果"""
    print("\n" + "="*80)
    print(f"文件夹比较结果")
    print(f"目录1: {dir1}")
    print(f"目录2: {dir2}")
    print("="*80)
    
    total_only_dir1 = 0
    total_only_dir2 = 0
    total_same = 0
    total_different = 0
    total_files_dir1 = 0
    total_files_dir2 = 0
    
    for ext, data in results.items():
        only_dir1_count = len(data['only_in_dir1'])
        only_dir2_count = len(data['only_in_dir2'])
        same_count = len(data['same_files'])
        different_count = len(data['different_files'])
        
        total_only_dir1 += only_dir1_count
        total_only_dir2 += only_dir2_count
        total_same += same_count
        total_different += different_count
        total_files_dir1 += data['total_dir1']
        total_files_dir2 += data['total_dir2']
        
        print(f"\n📁 {ext} 文件")
        print(f"  📊 总数: 目录1({data['total_dir1']}) vs 目录2({data['total_dir2']})")
        print(f"  ✅ 相同: {same_count}")
        print(f"  ⚠️  差异: {different_count}")
        print(f"  ➕ 仅在目录1: {only_dir1_count}")
        print(f"  ➖ 仅在目录2: {only_dir2_count}")
        
        if show_details:
            if data['only_in_dir1']:
                print(f"    仅在目录1的{ext}文件:")
                for filename, file_info in data['only_in_dir1'][:10]:  # 最多显示10个
                    print(f"      - {filename}")
                if len(data['only_in_dir1']) > 10:
                    print(f"      ... 还有 {len(data['only_in_dir1'])-10} 个文件")
            
            if data['only_in_dir2']:
                print(f"    仅在目录2的{ext}文件:")
                for filename, file_info in data['only_in_dir2'][:10]:
                    print(f"      - {filename}")
                if len(data['only_in_dir2']) > 10:
                    print(f"      ... 还有 {len(data['only_in_dir2'])-10} 个文件")
            
            if data['different_files']:
                print(f"    内容不同的{ext}文件:")
                for diff_info in data['different_files'][:5]:
                    filename = diff_info['filename']
                    size1 = diff_info['dir1']['size']
                    size2 = diff_info['dir2']['size']
                    print(f"      - {filename} (大小: {size1} vs {size2})")
    
    print(f"\n📊 总计统计:")
    print(f"  📁 总文件数: 目录1({total_files_dir1}) vs 目录2({total_files_dir2})")
    print(f"  ✅ 相同文件: {total_same}")
    print(f"  ⚠️  差异文件: {total_different}")
    print(f"  ➕ 仅在目录1: {total_only_dir1}")
    print(f"  ➖ 仅在目录2: {total_only_dir2}")


def save_detailed_report(results, output_file, dir1, dir2):
    """保存详细的比较报告到文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"文件夹差异比较报告\n")
        f.write(f"生成时间: {__import__('datetime').datetime.now()}\n")
        f.write(f"目录1: {dir1}\n")
        f.write(f"目录2: {dir2}\n")
        f.write("="*80 + "\n\n")
        
        for ext, data in results.items():
            f.write(f"{ext} 文件类型 (目录1: {data['total_dir1']}个, 目录2: {data['total_dir2']}个)\n")
            f.write("-" * 40 + "\n")
            
            f.write(f"仅在目录1存在的文件 ({len(data['only_in_dir1'])} 个):\n")
            for filename, file_info in data['only_in_dir1']:
                f.write(f"  {filename} ({file_info['size']} 字节)\n")
            
            f.write(f"\n仅在目录2存在的文件 ({len(data['only_in_dir2'])} 个):\n")
            for filename, file_info in data['only_in_dir2']:
                f.write(f"  {filename} ({file_info['size']} 字节)\n")
            
            if data['different_files']:
                f.write(f"\n内容不同的文件 ({len(data['different_files'])} 个):\n")
                for diff_info in data['different_files']:
                    f.write(f"  {diff_info['filename']}\n")
                    f.write(f"    目录1: {diff_info['dir1']['size']} 字节\n")
                    f.write(f"    目录2: {diff_info['dir2']['size']} 字节\n")
            
            f.write("\n" + "="*80 + "\n\n")
    
    print(f"详细报告已保存到: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='比较两个文件夹中同类文件的差异')
    parser.add_argument('--dir1', help='第一个目录路径')
    parser.add_argument('--dir2', help='第二个目录路径') 
    parser.add_argument('--extensions', '-e', nargs='+', 
                       help='要比较的文件扩展名（如 .jpg .png），不指定则比较所有文件')
    parser.add_argument('--recursive', '-r', action='store_true', default=True,
                       help='递归扫描子目录（默认开启）')
    parser.add_argument('--no-recursive', action='store_true', 
                       help='不递归扫描，只扫描顶层目录')
    parser.add_argument('--compare-mode', '-m', choices=['name', 'size', 'hash'], 
                       default='name', help='比较模式：name(文件名), size(大小), hash(内容)')
    parser.add_argument('--details', '-d', action='store_true', 
                       help='显示详细信息')
    parser.add_argument('--list-only', '-l', action='store_true',
                       help='仅列出目录内容，不进行比较')
    parser.add_argument('--output', '-o', help='保存详细报告到文件')
    
    args = parser.parse_args()
    
    # 检查目录是否存在
    if not args.list_only:
        if not args.dir1 or not os.path.isdir(args.dir1):
            print(f"错误: 目录1 '{args.dir1}' 不存在")
            return
        if not args.dir2 or not os.path.isdir(args.dir2):
            print(f"错误: 目录2 '{args.dir2}' 不存在")
            return
    else:
        if args.dir1 and not os.path.isdir(args.dir1):
            print(f"错误: 目录1 '{args.dir1}' 不存在")
            return
        if args.dir2 and not os.path.isdir(args.dir2):
            print(f"错误: 目录2 '{args.dir2}' 不存在")
            return
    
    # 处理扩展名
    extensions = None
    if args.extensions:
        extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in args.extensions]
        print(f"比较文件类型: {', '.join(extensions)}")
    
    # 处理递归选项
    recursive = args.recursive and not args.no_recursive
    print(f"递归扫描: {'是' if recursive else '否'}")
    
    # 如果只是列出内容
    if args.list_only:
        print(f"\n📂 列出目录内容:")
        if args.dir1:
            print(f"\n目录1: {args.dir1}")
            scan_directory(args.dir1, extensions, recursive)
        if args.dir2:
            print(f"\n目录2: {args.dir2}")
            scan_directory(args.dir2, extensions, recursive)
        return
    
    # 执行比较
    calculate_hash = args.compare_mode == 'hash'
    results = compare_directories(
        args.dir1, args.dir2, 
        extensions=extensions,
        recursive=recursive,
        compare_mode=args.compare_mode,
        calculate_hash=calculate_hash
    )
    
    # 显示结果
    print_comparison_results(results, args.dir1, args.dir2, args.details)
    
    # 保存报告
    if args.output:
        save_detailed_report(results, args.output, args.dir1, args.dir2)


if __name__ == '__main__':
    main()