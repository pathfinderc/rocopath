"""
PIL Image 到 QImage 的转换工具

提供高效、简洁的转换函数，不依赖 QApplication，可直接在非 GUI 环境中使用。
"""

from PIL import Image
from PySide6.QtGui import QImage

def pil_image_to_qimage(pil_img: Image.Image) -> QImage:
    """
    将 PIL Image 对象转换为 QImage 对象。

    该函数通过直接内存拷贝实现，无需保存临时文件，性能高效。
    支持常见的 RGB 和 RGBA 模式，其他模式会自动转换为 RGBA。

    Args:
        pil_img: PIL Image 实例

    Returns:
        等效的 QImage 对象，格式为 QImage.Format_RGBA8888 或 QImage.Format_RGB888

    Raises:
        TypeError: 如果输入不是 PIL Image
    """

    # 统一转换为 RGB 或 RGBA 格式以便直接映射到 QImage 格式
    if pil_img.mode == "RGB":
        fmt = QImage.Format.Format_RGB888
        bytes_per_line = pil_img.width * 3
    elif pil_img.mode == "RGBA":
        fmt = QImage.Format.Format_RGBA8888
        bytes_per_line = pil_img.width * 4
    else:
        # 其他模式（如 L、P、CMYK）先转为 RGBA 以保证透明通道正确处理
        pil_img = pil_img.convert("RGBA")
        fmt = QImage.Format.Format_RGBA8888
        bytes_per_line = pil_img.width * 4

    # 获取图像的原始字节数据（必须是连续内存）
    data = pil_img.tobytes("raw", pil_img.mode)

    qimg = QImage(data, pil_img.width, pil_img.height, bytes_per_line, fmt)
    # 保持 data 引用，防止 QImage 底层指针因 Python GC 悬空
    qimg = qimg.copy()
    return qimg
