#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将掩码图与原图叠加可视化
"""

import argparse
import os
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt


def remove_digits(text:str)-> str:
    """使用正则表达式去除数字"""
    import re
    return re.sub(r'\d', '', text)


def overlay_mask(img, mask, colormap="jet", alpha=0.7):
    """参考 utils/util.py 中的 overlay_mask"""
    cmap = plt.get_cmap(colormap)
    # Resize mask and apply colormap
    overlay = mask.resize(img.size, resample=Image.BICUBIC)
    mask_normalized = np.asarray(overlay) / 255.0  # 归一化到 0-1
    overlay = (255 * cmap(mask_normalized)[:, :, :3]).astype(np.uint8)
    # Overlay the image with the mask
    overlayed_img = Image.fromarray((alpha * np.asarray(img) + (1 - alpha) * overlay).astype(np.uint8))
    return overlayed_img


def visualize(rgb_file_path, mask_file_path, output_path, alpha=0.7):
    # 如果输出路径是目录，自动生成文件名
    if os.path.isdir(output_path):
        base_name = os.path.splitext(os.path.basename(rgb_file_path))[0]
        output_path = os.path.join(output_path, f"{base_name}_vis.png")

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 读取原图和掩码
    image = Image.open(rgb_file_path).convert('RGB')
    mask = Image.open(mask_file_path).convert('L')
    result = overlay_mask(image, mask, alpha=alpha)
    result.save(output_path)
    print(f"Saved at {output_path}")


def process_dir(rgb_dir, mask_dir, out_dir, BASE_OBJ, SEEN_AFF, alpha):
    """
    递归处理文件夹中的RGB图像和对应的掩码
    """
    # 递归获取所有图像文件
    rgb_files = []
    for root, dirs, files in os.walk(rgb_dir):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, rgb_dir)
                rgb_files.append((full_path, rel_path))
    
    if not rgb_files:
        print(f"在 {rgb_dir} 中没有找到图像文件")
        return
    
    print(f"找到 {len(rgb_files)} 个图像文件")
    
    success_count = 0
    fail_count = 0

    for rgb_path, rel_path in sorted(rgb_files):
        # 直接在mask_dir根目录下查找同名mask文件（不保持目录结构）
        base_name = os.path.basename(rgb_path)
        mask_filename = os.path.splitext(base_name)[0] + '.png'
        save_name = os.path.splitext(base_name)[0] + '_vis.png'
        
        for root, dirs, files in os.walk(mask_dir):
            if mask_filename in files:
                mask_path = os.path.join(root, mask_filename)
                output_path = os.path.join(out_dir, save_name)
                visualize(rgb_path, mask_path, output_path, alpha)
                success_count += 1
                break
        else:
            print(f"  跳过: 未找到掩码 {mask_filename}")
            fail_count += 1
            continue
    
    print(f"\n完成. 成功 {success_count}, 失败 {fail_count}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='掩码可视化')
    parser.add_argument('-i', '--image', default='/root/autodl-tmp/OOAL/data/source/screen/screen5.jpg', help='原图路径')
    parser.add_argument('-m', '--mask', default='/root/autodl-tmp/OOAL/data/temps/2/GT/display/screen/screen5.png', help='掩码图路径')
    parser.add_argument('-o', '--output', default='/root/autodl-tmp/OOAL/data/temps/screen5_vis.png', help='输出路径')
    parser.add_argument('-a', '--alpha', type=float, default=0.5, help='原图透明度(0-1)')
    args = parser.parse_args()

    import sys
    sys.path.append('/root/autodl-tmp/OOAL')
    from data.agd20k_ego import BASE_OBJ, SEEN_AFF, NOVEL_AFF, UNSEEN_AFF
    
    # 验证输入路径存在
    if not os.path.exists(args.image):
        print(f"错误: 输入路径不存在 {args.image}")
        exit(1)
    
    if not os.path.exists(args.mask):
        print(f"错误: 掩码路径不存在 {args.mask}")
        exit(1)
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    # 根据输入类型选择处理模式
    if os.path.isfile(args.image):
        # 单文件模式
        if not os.path.isfile(args.mask):
            print(f"错误: 单文件模式下 -m 也必须是文件路径")
            exit(1)
        visualize(args.image, args.mask, args.output, args.alpha)
    elif os.path.isdir(args.image):
        # 目录模式
        if not os.path.isdir(args.mask):
            print(f"错误: 目录模式下 -m 也必须是目录路径")
            exit(1)
        process_dir(args.image, args.mask, args.output, BASE_OBJ, SEEN_AFF, args.alpha)
    else:
        print(f"错误: 无法识别 {args.image} 的类型")
        exit(1)
