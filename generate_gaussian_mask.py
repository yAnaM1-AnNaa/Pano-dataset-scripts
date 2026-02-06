#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
根据点阵json文件生成高斯掩码图
对每个控制点应用高斯核，生成多值（非二值）掩码图
"""

import json
import os
import argparse
import numpy as np
from PIL import Image, ImageDraw
import math
from shapely.geometry import Polygon
import re


def remove_digits(text:str)-> str:
    """使用正则表达式去除数字"""
    return re.sub(r'\d', '', text)

def create_gaussian_kernel(size, sigma=None):
    """
    创建高斯核
    Args:
        size: 核大小（会自动转换为奇数）
        sigma: 高斯标准差（如果为None，则根据size自动计算）
    Returns:
        归一化的高斯核
    """
    # 确保size为奇数
    size = int(size)
    if size % 2 == 0:
        size += 1
    if size < 1:
        size = 1

    if sigma is None:
        # 常用公式：sigma = (size - 1) / 6，这样3sigma覆盖核的范围
        sigma = (size - 1) / 6.0
        if sigma <= 0:
            sigma = 0.5

    # 创建坐标网格
    half_size = size // 2
    x = np.arange(-half_size, half_size + 1)
    y = np.arange(-half_size, half_size + 1)
    xx, yy = np.meshgrid(x, y)

    # 计算高斯值
    kernel = np.exp(-(xx**2 + yy**2) / (2 * sigma**2))

    # 归一化使峰值为1
    kernel = kernel / kernel.max()

    return kernel


def apply_gaussian_at_point(mask, x, y, kernel):
    """
    在指定位置应用高斯核

    Args:
        mask: 掩码数组
        x: x坐标
        y: y坐标
        kernel: 高斯核
        label_value: 标签值
    """
    h, w = mask.shape
    kh, kw = kernel.shape
    half_kh, half_kw = kh // 2, kw // 2

    # 计算核在图像上的有效范围
    x, y = int(round(x)), int(round(y))

    # 核的范围
    k_y_start = max(0, half_kh - y)
    k_y_end = min(kh, h - y + half_kh)
    k_x_start = max(0, half_kw - x)
    k_x_end = min(kw, w - x + half_kw)

    # 图像的范围
    img_y_start = max(0, y - half_kh)
    img_y_end = min(h, y + half_kh + 1)
    img_x_start = max(0, x - half_kw)
    img_x_end = min(w, x + half_kw + 1)

    # 检查范围是否有效
    if img_y_start >= img_y_end or img_x_start >= img_x_end:
        return

    # 获取核的对应部分
    kernel_part = kernel[k_y_start:k_y_end, k_x_start:k_x_end]

    # 将高斯值乘以标签值，并与现有值取最大（避免覆盖）
    mask_region = mask[img_y_start:img_y_end, img_x_start:img_x_end]
    new_values = kernel_part
    mask[img_y_start:img_y_end, img_x_start:img_x_end] = np.maximum(mask_region, new_values)


def generate_mask_from_json(json_path, output_path, distance_config:dict):
    """
    从单个json文件生成高斯掩码图
    Args:
        json_path: 输入json文件路径
        output_path: 输出png文件路径
        distance_config: 缩放距离配置字典
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    image_width = data.get('imageWidth')
    image_height = data.get('imageHeight')

    if image_width is None or image_height is None:
        print(f"  {json_path} 缺少图像尺寸信息，跳过处理")
        return False

    # 创建掩码数组（使用float以保存高斯渐变值）
    mask = np.zeros((image_height, image_width), dtype=np.float32)

    # 获取所有shapes
    shapes = data.get('shapes', [])
    for idx, shape in enumerate(shapes):
        shape_type = shape.get('shape_type', '')
        label = shape.get('label', 'unknown')
        points = shape.get('points', [])

        if shape_type == 'points':
            # Shrink_config:{'armset1.json':distance,...}
            # mask_json_path: /root/autodl-tmp/OOAL/data/temps/7/Spotted/armset1.json
            print(f"Generating mask '{label}': {len(points)} dots")
            # 根据缩小的distance确定高斯核大小
            json_name = os.path.basename(json_path)
            shrink_dist = int(distance_config[json_name][idx])
            kernel_size = max(3, int(shrink_dist * 10))  # 核大小=收缩距离*s
            kernel = create_gaussian_kernel(kernel_size)
            for point in points:
                x, y = point[0], point[1]
                apply_gaussian_at_point(mask, x, y, kernel)
        elif shape_type == 'point' and len(points) >= 1:
            print(f"Processing '{label}': {len(points)} dots")
            shrink_dist = int(distance_config[json_name][idx])
            kernel_size = max(3, int(shrink_dist * 20))
            kernel = create_gaussian_kernel(kernel_size)
            for point in points:
                x, y = point[0], point[1]
                apply_gaussian_at_point(mask, x, y, kernel)

    # 归一化到0-255范围
    if mask.max() > 0:
        mask = (mask / mask.max()) * 255
        mask = np.clip(mask, 0, 255)
    mask_uint8 = mask.astype(np.uint8)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

    # 保存为png
    img = Image.fromarray(mask_uint8, mode='L')
    img.save(output_path)

    return True


def process_folder(input_folder, output_folder, BASE_OBJ, SEEN_AFF, NOVEL_AFF, UNSEEN_AFF, distance_config):
    """
    批量处理文件夹中的所有json文件（包括子文件夹）

    Args:
        input_folder: 输入文件夹路径
        output_folder: 输出文件夹路径
        kernel_scale: 高斯核缩放因子
        default_spacing: 默认点间距
        distance_config: 距离配置字典
    """
    # 确保输出文件夹存在
    os.makedirs(output_folder, exist_ok=True)

    # 递归获取所有json文件
    json_files = []
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if file.endswith('.json'):
                # 保存完整路径和相对路径
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, input_folder)
                json_files.append((full_path, rel_path))

    if not json_files:
        print(f"在 {input_folder} 中没有找到json文件")
        return

    print(f"找到 {len(json_files)} 个json文件（包括子文件夹）")

    success_count = 0
    fail_count = 0

    for input_path, rel_path in sorted(json_files):
        # 生成同名的png文件，保持目录结构
        output_filename = os.path.splitext(rel_path)[0] + '.png'
        output_path = os.path.join(output_folder, output_filename)
        obj = remove_digits(output_path.split('/')[-1].split('.')[0])  # lamp
        
        try:
            aff_index = BASE_OBJ.index(obj)
            aff = SEEN_AFF[aff_index]
            output_path = os.path.join(output_folder, aff, obj, output_filename)
        except ValueError:
            # 如果对象不在BASE_OBJ列表中，直接保存到输出文件夹
            print(f"  警告: '{obj}' 不在BASE_OBJ列表中，直接保存到输出目录")
            output_path = os.path.join(output_folder, output_filename)

        try:
            if generate_mask_from_json(input_path, output_path, distance_config):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  ✗ 处理文件出错: '{output_path}'")
            print(f"    错误详情: {type(e).__name__}: {e}")
            import traceback
            print(f"    位置: {traceback.format_exc().splitlines()[-2].strip()}")
            fail_count += 1

    print(f"\nFinished. Success {success_count}, Fail {fail_count}")
    print(f"Saved under: {output_folder}")


def main():
    parser = argparse.ArgumentParser(description='根据点阵json生成高斯掩码图')
    parser.add_argument('--input', '-i', default='/root/autodl-tmp/OOAL/data/source/backrest', help='输入文件夹路径（包含json文件）')
    parser.add_argument('--output', '-o', default='./data/temps/GT', help='输出文件夹路径（保存png文件）')
    parser.add_argument('--config', '-c', default='./data/temps/GT/distance_config.json', help='保存每个文件缩放距离的配置文件路径')
    args = parser.parse_args()

    import sys
    sys.path.append('/root/autodl-tmp/OOAL')
    from data.agd20k_ego import BASE_OBJ, SEEN_AFF, NOVEL_AFF, UNSEEN_AFF

    # 创建输出文件夹
    if not os.path.exists(args.output):
        os.makedirs(args.output)
        print(f"Output folder does not exist. Created output folder: {args.output}")

    with open(args.config, 'r', encoding='utf-8') as f:
        distance_config = json.load(f)

    process_folder(args.input, args.output, BASE_OBJ, SEEN_AFF, NOVEL_AFF, UNSEEN_AFF, distance_config)


if __name__ == '__main__':
    main()
