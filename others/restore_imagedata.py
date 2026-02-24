"""
将labelme JSON文件中的imageData字段解码并保存为RGB图像
"""
import json
import base64
from PIL import Image
import io
import os
import argparse


def restore_image_from_json(json_path, output_path=None):
    """
    从JSON文件中提取imageData并保存为图像
    
    Args:
        json_path: JSON文件路径
        output_path: 输出图像路径（可选），如果不提供则使用JSON中的imagePath
    """
    # 读取JSON文件
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 检查是否有imageData字段
    if 'imageData' not in data or data['imageData'] is None:
        print(f"警告: {json_path} 中没有找到imageData字段")
        return False
    
    # 解码base64数据
    image_data = base64.b64decode(data['imageData'])
    
    # 将字节数据转换为PIL Image对象
    image = Image.open(io.BytesIO(image_data))
    
    # 确保是RGB模式
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # 确定输出路径
    if output_path is None:
        # 使用JSON文件所在目录和imagePath字段
        json_dir = os.path.dirname(json_path)
        image_name = data.get('imagePath', 'restored_image.jpg')
        output_path = os.path.join(json_dir, image_name)
    
    # 保存图像
    image.save(output_path)
    print(f"图像已保存到: {output_path}")
    print(f"图像尺寸: {image.size}")
    print(f"图像模式: {image.mode}")
    
    return True


def batch_restore_images(input_dir, output_dir=None):
    """
    批量处理目录中的所有JSON文件
    
    Args:
        input_dir: 包含JSON文件的目录
        output_dir: 输出目录（可选），如果不提供则保存到JSON文件所在目录
    """
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    json_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    
    if not json_files:
        print(f"在 {input_dir} 中没有找到JSON文件")
        return
    
    print(f"找到 {len(json_files)} 个JSON文件")
    
    success_count = 0
    for json_file in json_files:
        json_path = os.path.join(input_dir, json_file)
        
        if output_dir:
            # 使用JSON文件名生成输出文件名
            base_name = os.path.splitext(json_file)[0]
            output_path = os.path.join(output_dir, f"{base_name}.jpg")
        else:
            output_path = None
        
        print(f"\n处理: {json_file}")
        if restore_image_from_json(json_path, output_path):
            success_count += 1
    
    print(f"\n完成! 成功处理 {success_count}/{len(json_files)} 个文件")


def main():
    parser = argparse.ArgumentParser(
        description='从labelme JSON文件中提取imageData并保存为RGB图像'
    )
    parser.add_argument(
        'input',
        help='JSON文件路径或包含JSON文件的目录'
    )
    parser.add_argument(
        '-o', '--output',
        help='输出图像路径或输出目录（批量处理时）'
    )
    parser.add_argument(
        '-b', '--batch',
        action='store_true',
        help='批量处理目录中的所有JSON文件'
    )
    
    args = parser.parse_args()
    
    if args.batch:
        # 批量处理模式
        batch_restore_images(args.input, args.output)
    else:
        # 单文件处理模式
        if not os.path.isfile(args.input):
            print(f"错误: {args.input} 不是有效的文件")
            return
        
        restore_image_from_json(args.input, args.output)


if __name__ == '__main__':
    main()
