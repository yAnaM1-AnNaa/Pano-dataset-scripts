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


def visualize(image_path, mask_path, output_path, alpha=0.7):
    # 如果输出路径是目录，自动生成文件名
    if os.path.isdir(output_path):
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        output_path = os.path.join(output_path, f"{base_name}_vis.png")

    # 读取原图和掩码
    image = Image.open(image_path).convert('RGB')
    mask = Image.open(mask_path).convert('L')
    # img = Image.fromarray(np.array(image_path))

    # 叠加
    # ego_pred = overlay_mask(img, ego_pred, alpha=0.5)
    result = overlay_mask(image, mask, alpha=alpha)
    result.save(output_path)
    print(f"已保存: {output_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='掩码可视化')
    parser.add_argument('-i', '--image', required=True, help='原图路径')
    parser.add_argument('-m', '--mask', required=True, help='掩码图路径')
    parser.add_argument('-o', '--output', required=True, help='输出路径')
    parser.add_argument('-a', '--alpha', type=float, default=0.5, help='原图透明度(0-1)')

    args = parser.parse_args()
    visualize(args.image, args.mask, args.output, args.alpha)
