#!/usr/bin/env python3
"""
图片批量resize工具 (基于OpenCV)
支持单张图片或文件夹批量处理
使用cv2获得更好的性能和质量
"""

import os
import argparse
import cv2
import numpy as np
from pathlib import Path


def resize_image(input_path, output_path, target_size, keep_aspect_ratio=False, interpolation=cv2.INTER_LANCZOS4):
    """
    调整单张图片大小

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        target_size: 目标尺寸 (width, height)
        keep_aspect_ratio: 是否保持宽高比
        interpolation: 插值方法
    """
    try:
        # 读取图片
        img = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"✗ 无法读取图片: {input_path}")
            return False

        original_size = (img.shape[1], img.shape[0])  # (width, height)

        # 根据参数决定resize方式
        if keep_aspect_ratio:
            # 保持宽高比
            h, w = img.shape[:2]
            target_w, target_h = target_size

            # 计算缩放比例
            scale = min(target_w / w, target_h / h)
            new_w = int(w * scale)
            new_h = int(h * scale)

            resized_img = cv2.resize(img, (new_w, new_h), interpolation=interpolation)
            final_size = (new_w, new_h)
        else:
            # 直接resize到目标尺寸
            resized_img = cv2.resize(img, target_size, interpolation=interpolation)
            final_size = target_size

        # 保存图片
        cv2.imwrite(output_path, resized_img)
        print(f"✓ {os.path.basename(input_path)}: {original_size} -> {final_size}")

        return True
    except Exception as e:
        print(f"✗ 处理失败 {input_path}: {str(e)}")
        return False


def resize_folder(input_folder, output_folder, target_size, keep_aspect_ratio=False, interpolation=cv2.INTER_LANCZOS4):
    """
    批量处理文件夹中的图片

    Args:
        input_folder: 输入文件夹路径
        output_folder: 输出文件夹路径
        target_size: 目标尺寸 (width, height)
        keep_aspect_ratio: 是否保持宽高比
        interpolation: 插值方法
    """
    # 支持的图片格式
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.gif'}

    # 创建输出文件夹
    os.makedirs(output_folder, exist_ok=True)

    # 获取所有图片文件
    input_path = Path(input_folder)
    image_files = [f for f in input_path.iterdir()
                   if f.is_file() and f.suffix.lower() in image_extensions]

    if not image_files:
        print(f"在 {input_folder} 中没有找到图片文件")
        return

    print(f"找到 {len(image_files)} 张图片")
    print(f"目标尺寸: {target_size}")
    print(f"插值方法: {get_interpolation_name(interpolation)}")
    print(f"保持宽高比: {'是' if keep_aspect_ratio else '否'}")
    print("-" * 60)

    # 处理每张图片
    success_count = 0
    for img_file in image_files:
        output_path = os.path.join(output_folder, img_file.name)
        if resize_image(str(img_file), output_path, target_size, keep_aspect_ratio, interpolation):
            success_count += 1

    print("-" * 60)
    print(f"处理完成: {success_count}/{len(image_files)} 张图片成功")


def get_interpolation_name(interpolation):
    """获取插值方法名称"""
    names = {
        cv2.INTER_NEAREST: "NEAREST (最快，质量最低)",
        cv2.INTER_LINEAR: "LINEAR (快速，质量一般)",
        cv2.INTER_CUBIC: "CUBIC (较慢，质量好)",
        cv2.INTER_LANCZOS4: "LANCZOS4 (最慢，质量最好)",
        cv2.INTER_AREA: "AREA (缩小图片时推荐)"
    }
    return names.get(interpolation, "UNKNOWN")


def get_interpolation_method(method_name):
    """根据名称获取插值方法"""
    methods = {
        'nearest': cv2.INTER_NEAREST,
        'linear': cv2.INTER_LINEAR,
        'cubic': cv2.INTER_CUBIC,
        'lanczos': cv2.INTER_LANCZOS4,
        'lanczos4': cv2.INTER_LANCZOS4,
        'area': cv2.INTER_AREA
    }
    return methods.get(method_name.lower(), cv2.INTER_LANCZOS4)


def main():
    parser = argparse.ArgumentParser(
        description='图片批量resize工具 (基于OpenCV，性能优化版)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 单张图片resize (9104x4552 -> 4000x2000)
  python resize.py -i input.jpg -o output.jpg -s 4000 2000

  # 批量处理文件夹
  python resize.py -i ./images -o ./resized -s 4000 2000

  # 保持宽高比
  python resize.py -i ./images -o ./resized -s 4000 2000 --keep-aspect-ratio

  # 指定插值方法
  python resize.py -i ./images -o ./resized -s 4000 2000 --interpolation cubic

插值方法说明:
  - lanczos4 (默认): 质量最好，速度最慢，适合高质量resize
  - cubic: 质量好，速度较快，平衡选择
  - linear: 质量一般，速度快
  - area: 缩小图片时推荐，质量好
  - nearest: 速度最快，质量最低
        """
    )

    parser.add_argument('-i', '--input', required=True,
                        help='输入图片路径或文件夹路径')
    parser.add_argument('-o', '--output', required=True,
                        help='输出图片路径或文件夹路径')
    parser.add_argument('-s', '--size', nargs=2, type=int, required=True,
                        metavar=('WIDTH', 'HEIGHT'),
                        help='目标尺寸，例如: 4000 2000')
    parser.add_argument('--keep-aspect-ratio', action='store_true',
                        help='保持宽高比（会在目标尺寸内缩放）')
    parser.add_argument('--interpolation', type=str, default='lanczos4',
                        choices=['nearest', 'linear', 'cubic', 'lanczos', 'lanczos4', 'area'],
                        help='插值方法 (默认: lanczos4)')

    args = parser.parse_args()

    target_size = tuple(args.size)
    interpolation = get_interpolation_method(args.interpolation)

    # 判断输入是文件还是文件夹
    if os.path.isfile(args.input):
        # 单张图片处理
        os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
        print(f"插值方法: {get_interpolation_name(interpolation)}")
        resize_image(args.input, args.output, target_size, args.keep_aspect_ratio, interpolation)
    elif os.path.isdir(args.input):
        # 批量处理文件夹
        resize_folder(args.input, args.output, target_size, args.keep_aspect_ratio, interpolation)
    else:
        print(f"错误: 输入路径不存在: {args.input}")


if __name__ == '__main__':
    main()
