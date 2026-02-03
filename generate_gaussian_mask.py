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


def apply_gaussian_at_point(mask, x, y, kernel, label_value):
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
    new_values = kernel_part * label_value
    mask[img_y_start:img_y_end, img_x_start:img_x_end] = np.maximum(mask_region, new_values)


def generate_mask_from_json(json_path, output_path, kernel_scale=1.0, default_spacing=1):
    """
    从json文件生成高斯掩码图

    Args:
        json_path: 输入json文件路径
        output_path: 输出png文件路径
        kernel_scale: 高斯核缩放因子 k（kernel_size = k * spacing）
        default_spacing: 默认点间距（如果json中没有记录）

    Returns:
        是否成功
    """
    # 读取json文件
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 获取图像尺寸
    image_width = data.get('imageWidth')
    image_height = data.get('imageHeight')

    if image_width is None or image_height is None:
        print(f"警告: {json_path} 缺少图像尺寸信息，跳过处理")
        return False

    # 获取点间距（从第一个功能保存的信息）
    point_spacing = data.get('point_spacing', default_spacing)

    # 计算高斯核大小
    kernel_size = max(1, int(kernel_scale * point_spacing))
    kernel = create_gaussian_kernel(kernel_size)

    print(f"  点间距: {point_spacing}, 核缩放: {kernel_scale}, 核大小: {kernel.shape[0]}")

    # 创建掩码数组（使用float以保存高斯渐变值）
    mask = np.zeros((image_height, image_width), dtype=np.float32)

    # 获取所有shapes的标签，为每个标签分配一个值
    shapes = data.get('shapes', [])
    label_set = set()
    for shape in shapes:
        label_set.add(shape.get('label', 'unknown'))

    # 为每个标签分配一个值（1, 2, 3, ...），0保留给背景
    label_to_value = {label: idx + 1 for idx, label in enumerate(sorted(label_set))}

    if label_to_value:
        print(f"  标签映射: {label_to_value}")

    # 从json中读取原始多边形（如果有）
    original_polygons = data.get('original_polygons', [])
    if original_polygons:
        print(f"  找到 {len(original_polygons)} 个原始多边形用于裁剪")

    # 处理每个shape
    for shape in shapes:
        shape_type = shape.get('shape_type', '')
        label = shape.get('label', 'unknown')
        points = shape.get('points', [])
        label_value = label_to_value.get(label, 1)

        # 处理点阵类型（由第一个脚本生成）
        if shape_type == 'points':
            print(f"  处理点阵 '{label}': {len(points)} 个点, 值={label_value}")
            for point in points:
                x, y = point[0], point[1]
                apply_gaussian_at_point(mask, x, y, kernel, label_value)

        # 也支持直接处理多边形（如果json未经第一个脚本处理）
        elif shape_type == 'polygon' and len(points) >= 3:
            print(f"  警告: 发现未转换的多边形 '{label}'，建议先用convert_polygon_to_points.py处理")
            # 简单地在多边形顶点位置应用高斯
            for point in points:
                x, y = point[0], point[1]
                apply_gaussian_at_point(mask, x, y, kernel, label_value)

        # 支持单点类型
        elif shape_type == 'point' and len(points) >= 1:
            for point in points:
                x, y = point[0], point[1]
                apply_gaussian_at_point(mask, x, y, kernel, label_value)

    # 归一化到0-255范围
    if mask.max() > 0:
        # 保持多值特性：不同标签值会有不同的最大灰度
        # 将最大值映射到255
        max_label_value = max(label_to_value.values()) if label_to_value else 1
        mask = (mask / max_label_value) * 255
        mask = np.clip(mask, 0, 255)

    # 转换为uint8
    mask_uint8 = mask.astype(np.uint8)

    # 使用原始多边形裁剪掩码（避免超出边界）
    if original_polygons:
        print(f"  应用多边形裁剪")
        # 创建多边形掩码
        polygon_mask = Image.new('L', (image_width, image_height), 0)
        draw = ImageDraw.Draw(polygon_mask)
        
        for poly_points in original_polygons:
            # 将点转换为PIL需要的格式
            flat_points = [(int(p[0]), int(p[1])) for p in poly_points]
            draw.polygon(flat_points, fill=255)
        
        # 将多边形掩码转换为numpy数组
        polygon_mask_np = np.array(polygon_mask)
        
        # 裁剪：多边形外的区域设为0
        mask_uint8 = np.where(polygon_mask_np > 0, mask_uint8, 0).astype(np.uint8)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

    # 保存为png
    img = Image.fromarray(mask_uint8, mode='L')
    img.save(output_path)

    return True


def process_folder(input_folder, output_folder, kernel_scale=1.0, default_spacing=1):
    """
    批量处理文件夹中的所有json文件（包括子文件夹）

    Args:
        input_folder: 输入文件夹路径
        output_folder: 输出文件夹路径
        kernel_scale: 高斯核缩放因子
        default_spacing: 默认点间距
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

        print(f"处理: {rel_path} -> {output_filename}")

        try:
            if generate_mask_from_json(input_path, output_path, kernel_scale, default_spacing):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  错误: {e}")
            fail_count += 1

    print(f"\n处理完成: 成功 {success_count} 个, 失败 {fail_count} 个")
    print(f"输出目录: {output_folder}")


def main():
    parser = argparse.ArgumentParser(description='根据点阵json生成高斯掩码图')
    parser.add_argument('--input', '-i', required=True, help='输入文件夹路径（包含json文件）')
    parser.add_argument('--output', '-o', required=True, help='输出文件夹路径（保存png文件）')
    parser.add_argument('--kernel-scale', '-k', type=float, default=1.0,
                        help='高斯核缩放因子k，核大小=k*点间距（默认为1.0）')
    parser.add_argument('--default-spacing', '-s', type=int, default=1,
                        help='默认点间距，当json中没有记录时使用（默认为1）')

    args = parser.parse_args()

    if not os.path.isdir(args.input):
        print(f"错误: 输入路径 {args.input} 不是有效的文件夹")
        return

    process_folder(args.input, args.output, args.kernel_scale, args.default_spacing)


if __name__ == '__main__':
    main()
