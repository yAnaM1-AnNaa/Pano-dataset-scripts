#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将labelme标注的多边形转换为密集点阵
遍历源文件夹中的所有json文件，处理后保存到目标文件夹
"""

import json
import os
import argparse
import numpy as np
from PIL import Image, ImageDraw


def polygon_to_points(polygon_points, image_width, image_height, point_spacing=1.0):
    """
    将多边形转换为密集点阵

    Args:
        polygon_points: 多边形顶点列表 [[x1,y1], [x2,y2], ...]
        image_width: 图像宽度
        image_height: 图像高度
        point_spacing: 点之间的间距（支持浮点数，默认为1.0）

    Returns:
        点阵列表 [[x1,y1], [x2,y2], ...]
    """
    # 创建一个空白掩码图像
    mask = Image.new('L', (image_width, image_height), 0)
    draw = ImageDraw.Draw(mask)

    # 将多边形顶点转换为元组列表
    polygon_tuples = [(int(p[0]), int(p[1])) for p in polygon_points]

    # 在掩码上绘制填充的多边形
    draw.polygon(polygon_tuples, fill=255)

    # 转换为numpy数组
    mask_array = np.array(mask)

    # 根据间距生成采样网格（支持浮点数间距）
    x_samples = np.arange(0, image_width, point_spacing)
    y_samples = np.arange(0, image_height, point_spacing)

    # 创建网格
    xx, yy = np.meshgrid(x_samples, y_samples)

    # 将浮点坐标转换为整数用于查询掩码
    xx_int = np.clip(np.round(xx).astype(int), 0, image_width - 1)
    yy_int = np.clip(np.round(yy).astype(int), 0, image_height - 1)

    # 检查哪些点在多边形内
    in_polygon = mask_array[yy_int, xx_int] > 0

    # 获取在多边形内的点坐标（保留浮点精度）
    x_coords = xx[in_polygon]
    y_coords = yy[in_polygon]

    # 转换为点列表
    points = [[float(x), float(y)] for x, y in zip(x_coords, y_coords)]

    return points


def process_json_file(input_path, output_path, point_spacing=1):
    """
    处理单个json文件，将多边形转换为点阵

    Args:
        input_path: 输入json文件路径
        output_path: 输出json文件路径
        point_spacing: 点之间的间距
    """
    # 读取json文件
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 获取图像尺寸
    image_width = data.get('imageWidth')
    image_height = data.get('imageHeight')

    if image_width is None or image_height is None:
        print(f"警告: {input_path} 缺少图像尺寸信息，跳过处理")
        return False

    # 处理每个shape
    new_shapes = []
    for shape in data.get('shapes', []):
        shape_type = shape.get('shape_type', '')

        if shape_type == 'polygon':
            # 将多边形转换为点阵
            polygon_points = shape.get('points', [])
            if len(polygon_points) >= 3:
                dense_points = polygon_to_points(
                    polygon_points,
                    image_width,
                    image_height,
                    point_spacing
                )

                # 创建新的shape，类型改为point（多个点）
                new_shape = {
                    'label': shape.get('label', ''),
                    'points': dense_points,
                    'group_id': shape.get('group_id'),
                    'shape_type': 'points',  # 自定义类型，表示点阵
                    'flags': shape.get('flags', {}),
                    'description': shape.get('description', ''),
                    # 保留原始多边形信息以便需要时恢复
                    'original_polygon': polygon_points,
                    'original_shape_type': 'polygon'
                }
                new_shapes.append(new_shape)
                print(f"  转换多边形 '{shape.get('label')}': {len(polygon_points)} 顶点 -> {len(dense_points)} 个点")
            else:
                # 多边形顶点不足，保持原样
                new_shapes.append(shape)
        else:
            # 非多边形类型，保持原样
            new_shapes.append(shape)

    # 更新shapes
    data['shapes'] = new_shapes

    # 保存点间距信息，供后续生成掩码图使用
    data['point_spacing'] = point_spacing

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 保存处理后的json
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return True


def process_folder(input_folder, output_folder, point_spacing=1):
    """
    递归遍历文件夹中的所有json文件并处理

    Args:
        input_folder: 输入文件夹路径
        output_folder: 输出文件夹路径
        point_spacing: 点之间的间距
    """
    # 确保输出文件夹存在
    os.makedirs(output_folder, exist_ok=True)

    # 递归获取所有json文件
    json_files = []
    for root, dirs, files in os.walk(input_folder):
        for f in files:
            if f.endswith('.json'):
                json_files.append(os.path.join(root, f))

    if not json_files:
        print(f"在 {input_folder} 中没有找到json文件")
        return

    print(f"找到 {len(json_files)} 个json文件")

    success_count = 0
    fail_count = 0

    for input_path in sorted(json_files):
        # 只保留文件名，输出到同一目录
        json_file = os.path.basename(input_path)
        obj_name = input_path.split('/')[-2]
        output_path = os.path.join(output_folder, obj_name, json_file)

        print(f"处理: {input_path}")

        try:
            if process_json_file(input_path, output_path, point_spacing):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  错误: {e}")
            fail_count += 1

    print(f"\n处理完成: 成功 {success_count} 个, 失败 {fail_count} 个")
    print(f"输出目录: {output_folder}")


def main():
    parser = argparse.ArgumentParser(description='将labelme多边形标注转换为密集点阵')
    parser.add_argument('--input', '-i', default='/root/autodl-tmp/OOAL/data/source/armset', help='输入文件夹路径')
    parser.add_argument('--output', '-o', default='/root/autodl-tmp/OOAL/data/tobeprocess', help='输出文件夹路径')
    parser.add_argument('--spacing', '-s', type=float, default=0.8,
                        help='点之间的间距，支持浮点数（默认为0.8）')

    args = parser.parse_args()

    if not os.path.isdir(args.input):
        print(f"错误: 输入路径 {args.input} 不是有效的文件夹")
        return

    process_folder(args.input, args.output, args.spacing)


if __name__ == '__main__':
    main()
