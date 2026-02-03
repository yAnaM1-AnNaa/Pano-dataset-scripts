import cv2
import os
import random
import torch
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt


def set_seed(seed=0):
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    random.seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def process_gt(args):
    assert args.divide in ["Seen", "Unseen"], "The divide argument should be Seen or Unseen"
    files = os.listdir(args.mask_root)
    dict_1 = {}
    for file in files:
        file_path = os.path.join(args.mask_root, file)
        objs = os.listdir(file_path)
        for obj in objs:
            obj_path = os.path.join(file_path, obj)
            images = os.listdir(obj_path)
            for img in images:
                img_path = os.path.join(obj_path, img)
                mask = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                key = file + "_" + obj + "_" + img
                dict_1[key] = mask

    torch.save(dict_1, args.divide + "_gt.t7")

def process_gt2(args, GT_path):
    """生成GT路径映射文件（txt格式）"""
    files = os.listdir(args.mask_root)
    # gt_file = args.divide + "_gt.txt"
    gt_file = GT_path # = args.divide + args.model_name + "_gt.txt"
    with open(gt_file, 'w') as f:
        for file in files:
            file_path = os.path.join(args.mask_root, file)
            objs = os.listdir(file_path)
            for obj in objs:
                obj_path = os.path.join(file_path, obj)
                images = os.listdir(obj_path)
                for img in images:
                    img_path = os.path.join(obj_path, img)
                    key = file + "_" + obj + "_" + img
                    f.write(f"{key}\t{img_path}\n")


def load_gt_paths(gt_file):
    """加载GT路径映射"""
    gt_masks = {}
    with open(gt_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                key, path = line.split('\t')
                gt_masks[key] = path
    return gt_masks


def load_gt_mask(gt_masks, key):
    """按需加载单张GT mask"""
    if key not in gt_masks:
        return None
    mask_path = gt_masks[key]
    return cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)


def normalize_map(atten_map, resize_size:tuple):
    atten_map = cv2.resize(atten_map, dsize=resize_size)
    min_val = np.min(atten_map)
    max_val = np.max(atten_map)
    atten_norm = (atten_map - min_val) / (max_val - min_val + 1e-10)
    return atten_norm


def get_optimizer(model, args):
    lr = args.lr
    weight_list = []
    for name, value in model.named_parameters():
        if value.requires_grad:
            weight_list.append(value)

    optimizer = torch.optim.SGD([{'params': weight_list,
                                  'lr': lr}],
                                momentum=args.momentum,
                                weight_decay=args.weight_decay,
                                nesterov=True)

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.iters)
    return optimizer, scheduler


def overlay_mask(img: Image.Image, mask: Image.Image, colormap: str = "jet", alpha: float = 0.7) -> Image.Image:
    if not isinstance(img, Image.Image) or not isinstance(mask, Image.Image):
        raise TypeError("img and mask arguments need to be PIL.Image")

    if not isinstance(alpha, float) or alpha < 0 or alpha >= 1:
        raise ValueError("alpha argument is expected to be of type float between 0 and 1")

    cmap = plt.get_cmap(colormap)
    # Resize mask and apply colormap
    overlay = mask.resize(img.size, resample=Image.BICUBIC)
    overlay = (255 * cmap(np.asarray(overlay) ** 2)[:, :, :3]).astype(np.uint8)
    # Overlay the image with the mask
    overlayed_img = Image.fromarray((alpha * np.asarray(img) + (1 - alpha) * overlay).astype(np.uint8))

    return overlayed_img
