"""
Decode imageData from Labelme JSON and save as RGB image.
"""

import argparse
import base64
import io
import json
import os

from PIL import Image


def restore_image_from_json(json_path, output_path=None):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "imageData" not in data or data["imageData"] is None:
        print(f"Warning: imageData field not found in {json_path}")
        return False

    image_data = base64.b64decode(data["imageData"])
    image = Image.open(io.BytesIO(image_data))
    if image.mode != "RGB":
        image = image.convert("RGB")

    if output_path is None:
        json_dir = os.path.dirname(json_path)
        image_name = data.get("imagePath", "restored_image.jpg")
        output_path = os.path.join(json_dir, image_name)

    image.save(output_path)
    print(f"Image saved to: {output_path}")
    print(f"Image size: {image.size}")
    print(f"Image mode: {image.mode}")
    return True


def batch_restore_images(input_dir, output_dir=None):
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    json_files = [f for f in os.listdir(input_dir) if f.endswith(".json")]
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return

    print(f"Found {len(json_files)} JSON file(s)")
    success_count = 0
    for json_file in json_files:
        json_path = os.path.join(input_dir, json_file)
        output_path = None
        if output_dir:
            output_path = os.path.join(output_dir, f"{os.path.splitext(json_file)[0]}.jpg")
        print(f"\nProcessing: {json_file}")
        if restore_image_from_json(json_path, output_path):
            success_count += 1

    print(f"\nDone! Successfully processed {success_count}/{len(json_files)} file(s)")


def main():
    parser = argparse.ArgumentParser(description="Extract imageData from Labelme JSON as RGB images.")
    parser.add_argument("input", help="JSON file path or directory containing JSON files.")
    parser.add_argument("-o", "--output", help="Output image path or output directory for batch mode.")
    parser.add_argument("-b", "--batch", action="store_true", help="Batch process all JSON files in a directory.")
    args = parser.parse_args()

    if args.batch:
        batch_restore_images(args.input, args.output)
    else:
        if not os.path.isfile(args.input):
            print(f"Error: {args.input} is not a valid file")
            return
        restore_image_from_json(args.input, args.output)


if __name__ == "__main__":
    main()
