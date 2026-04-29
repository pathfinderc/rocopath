from pathlib import Path
from rocopath.utils.map import stitch_images


def test_stitch_images_with_valid_images():
    """测试使用有效图片进行拼接"""
    # 使用提供的测试资源路径
    project_root_path = Path(__file__).parent.parent.parent
    image_path = project_root_path / "assets" / "map" / "Maps_PC" / "10003"
    image_dir = str(image_path)
    # 调用函数
    result = stitch_images(image_dir)

    # 验证结果不是空的
    assert result is not None

