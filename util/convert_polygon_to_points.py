#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
灏唋abelme鏍囨敞鐨勫杈瑰舰杞崲涓哄瘑闆嗙偣闃?
閬嶅巻婧愭枃浠跺す涓殑鎵€鏈塲son鏂囦欢锛屽鐞嗗悗淇濆瓨鍒扮洰鏍囨枃浠跺す
"""

import json
import os
import argparse
import numpy as np
from PIL import Image, ImageDraw


def polygon_to_points(polygon_points, image_width, image_height, point_spacing=1.0):
    """
    灏嗗杈瑰舰杞崲涓哄瘑闆嗙偣闃?

    Args:
        polygon_points: 澶氳竟褰㈤《鐐瑰垪琛?[[x1,y1], [x2,y2], ...]
        image_width: 鍥惧儚瀹藉害
        image_height: 鍥惧儚楂樺害
        point_spacing: 鐐逛箣闂寸殑闂磋窛锛堟敮鎸佹诞鐐规暟锛岄粯璁や负1.0锛?

    Returns:
        鐐归樀鍒楄〃 [[x1,y1], [x2,y2], ...]
    """
    # 鍒涘缓涓€涓┖鐧芥帺鐮佸浘鍍?
    mask = Image.new('L', (image_width, image_height), 0)
    draw = ImageDraw.Draw(mask)

    # 灏嗗杈瑰舰椤剁偣杞崲涓哄厓缁勫垪琛?
    polygon_tuples = [(int(p[0]), int(p[1])) for p in polygon_points]

    # 鍦ㄦ帺鐮佷笂缁樺埗濉厖鐨勫杈瑰舰
    draw.polygon(polygon_tuples, fill=255)

    # 杞崲涓簄umpy鏁扮粍
    mask_array = np.array(mask)

    # 鏍规嵁闂磋窛鐢熸垚閲囨牱缃戞牸锛堟敮鎸佹诞鐐规暟闂磋窛锛?
    x_samples = np.arange(0, image_width, point_spacing)
    y_samples = np.arange(0, image_height, point_spacing)

    # 鍒涘缓缃戞牸
    xx, yy = np.meshgrid(x_samples, y_samples)

    # 灏嗘诞鐐瑰潗鏍囪浆鎹负鏁存暟鐢ㄤ簬鏌ヨ鎺╃爜
    xx_int = np.clip(np.round(xx).astype(int), 0, image_width - 1)
    yy_int = np.clip(np.round(yy).astype(int), 0, image_height - 1)

    # 妫€鏌ュ摢浜涚偣鍦ㄥ杈瑰舰鍐?
    in_polygon = mask_array[yy_int, xx_int] > 0

    # 鑾峰彇鍦ㄥ杈瑰舰鍐呯殑鐐瑰潗鏍囷紙淇濈暀娴偣绮惧害锛?
    x_coords = xx[in_polygon]
    y_coords = yy[in_polygon]

    # 杞崲涓虹偣鍒楄〃
    points = [[float(x), float(y)] for x, y in zip(x_coords, y_coords)]

    return points


def process_json_file(input_path, output_path, point_spacing=1):
    """
    澶勭悊鍗曚釜json鏂囦欢锛屽皢澶氳竟褰㈣浆鎹负鐐归樀

    Args:
        input_path: 杈撳叆json鏂囦欢璺緞
        output_path: 杈撳嚭json鏂囦欢璺緞
        point_spacing: 鐐逛箣闂寸殑闂磋窛
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    image_width = data.get('imageWidth')
    image_height = data.get('imageHeight')

    if image_width is None or image_height is None:
        print(f"Warning: {input_path} lacks width or height information. Skipping.")
        return False

    # 澶勭悊姣忎釜shape
    new_shapes = []
    for idx, shape in enumerate(data.get('shapes', [])):
        shape_type = shape.get('shape_type', '')
        label = shape.get('label', '')

        if shape_type == 'polygon':
            # 灏嗗杈瑰舰杞崲涓虹偣闃?
            polygon_points = shape.get('points', [])
            if len(polygon_points) >= 3:
                dense_points = polygon_to_points(
                    polygon_points,
                    image_width,
                    image_height,
                    point_spacing
                )

                # 鍒涘缓鏂扮殑shape锛岀被鍨嬫敼涓簆oint锛堝涓偣锛?
                new_shape = {
                    'label': label,
                    'points': dense_points,
                    'group_id': shape.get('group_id'),
                    'shape_type': 'points',  # 鑷畾涔夌被鍨嬶紝琛ㄧず鐐归樀
                    'flags': shape.get('flags', {}),
                    'description': shape.get('description', ''),
                    # 淇濈暀鍘熷澶氳竟褰俊鎭互渚块渶瑕佹椂鎭㈠
                    'original_polygon': polygon_points,
                    'original_shape_type': 'polygon'
                }
                new_shapes.append(new_shape)
                print(f"  [Shape {idx}] Converted polygon '{label}': {len(polygon_points)} vertices -> {len(dense_points)} points")
            else:
                # 澶氳竟褰㈤《鐐逛笉瓒筹紝淇濇寔鍘熸牱
                print(f"  [Shape {idx}] Warning: polygon '{label}' has only {len(polygon_points)} points (< 3), kept original shape")
                new_shapes.append(shape)
        else:
            # 闈炲杈瑰舰绫诲瀷锛屼繚鎸佸師鏍?
            if shape_type:
                print(f"  [Shape {idx}] Keeping non-polygon shape '{shape_type}' ('{label}')")
            new_shapes.append(shape)

    # 鏇存柊shapes
    data['shapes'] = new_shapes

    # 淇濆瓨鐐归棿璺濅俊鎭紝渚涘悗缁敓鎴愭帺鐮佸浘浣跨敤
    data['point_spacing'] = point_spacing

    # 纭繚杈撳嚭鐩綍瀛樺湪
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 淇濆瓨澶勭悊鍚庣殑json
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return True


def process_folder(input_folder, output_folder, point_spacing=1):
    """
    閫掑綊閬嶅巻鏂囦欢澶逛腑鐨勬墍鏈塲son鏂囦欢骞跺鐞?

    Args:
        input_folder: 杈撳叆鏂囦欢澶硅矾寰?
        output_folder: 杈撳嚭鏂囦欢澶硅矾寰?
        point_spacing: 鐐逛箣闂寸殑闂磋窛
    """
    # 纭繚杈撳嚭鏂囦欢澶瑰瓨鍦?
    os.makedirs(output_folder, exist_ok=True)

    # 閫掑綊鑾峰彇鎵€鏈塲son鏂囦欢
    json_files = []
    for root, dirs, files in os.walk(input_folder):
        for f in files:
            if f.endswith('.json'):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, input_folder)
                json_files.append((full_path, rel_path))

    if not json_files:
        print(f"No JSON files found under {input_folder}")
        return

    print(f"Found {len(json_files)} JSON files")

    success_count = 0
    fail_count = 0

    for input_path, rel_path in sorted(json_files):
        # 鍙繚鐣欐枃浠跺悕锛岃緭鍑哄埌鍚屼竴鐩綍
        output_path = os.path.join(output_folder, rel_path)

        print(f"Processing: {input_path}")

        try:
            if process_json_file(input_path, output_path, point_spacing):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  Error: {e}")
            fail_count += 1

    print(f"\nProcessing completed: {success_count} succeeded, {fail_count} failed")
    print(f"Output directory: {output_folder}")


def main():
    parser = argparse.ArgumentParser(description='灏唋abelme澶氳竟褰㈡爣娉ㄨ浆鎹负瀵嗛泦鐐归樀')
    parser.add_argument('--input', '-i', default='./data/temps/Shrinked', help='Input json folder path.')
    parser.add_argument('--output', '-o', default='./data/temps/Spotted', help='Output json folder path.')
    parser.add_argument('--spacing', '-s', type=float, default=0.8,
                        help='Point spacing, default is 0.8.')
    args = parser.parse_args()
    DEFAULT_POINT_SPACING = args.spacing

    # 鍒涘缓杈撳嚭鏂囦欢澶?
    if not os.path.exists(args.output):
        os.makedirs(args.output)
        print(f"Output folder does not exist. Created output folder: {args.output}")

    process_folder(args.input, args.output, DEFAULT_POINT_SPACING)


if __name__ == '__main__':
    main()
