"""
地图图像处理模块

提供从本地资源目录加载、拼接、处理地图图片及遮罩的功能。
处理后的图像为 RGBA 格式 PIL.Image，可在 UI 层转换为 QPixmap。

函数说明：
- get_map: 快速获取预拼接好的地图图片（直接从 PNG 文件读取）
- load_and_composite_map: 从瓦片拼接并合成遮罩，生成完整地图（用于预处理）
"""

from pathlib import Path
from PIL import Image
import cv2
import numpy as np
from loguru import logger
from rocopath.config import MAPS_PC_DIR, MASKS_PC_DIR, MAP_DATA_DIR


def get_map(map_id: str) -> Image.Image | None:
    """
    获取预拼接好的地图图片。

    直接从 assets/maps/<map_id>.webp 读取已处理好的完整地图图像，
    比 load_and_composite_map 快得多，适用于日常使用。

    Args:
        map_id: 地图唯一标识符

    Returns:
        RGBA 格式 PIL.Image，若文件不存在或加载失败则返回 None
    """
    map_file = MAP_DATA_DIR / f"{map_id}.webp"

    if not map_file.exists():
        logger.warning("地图文件不存在: {}", map_file)
        return None

    try:
        return Image.open(map_file).convert("RGBA")
    except Exception as e:
        logger.error("读取地图文件失败: {} - {}", map_file, e)
        return None


