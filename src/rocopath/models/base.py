"""
核心数据模型定义

存放整个应用共享的基础数据结构，代表业务领域中的核心概念：
- MapInfo: 地图信息
- Point: 资源点/标记点
- Route: 规划出的路径

使用 Pydantic 便于后续从 JSON 文件加载并验证数据。
"""

from pydantic import BaseModel, Field
from PIL import Image


class MapInfo(BaseModel):
    """地图信息"""

    map_id: str
    """地图ID"""

    name: str
    """地图名称（显示用）"""

    width: int = Field(default=0, description="地图宽度（像素）")
    """地图宽度（像素）"""

    height: int = Field(default=0, description="地图高度（像素）")
    """地图高度（像素）"""

    # PIL 图像不参与序列化/验证，所以 exclude
    image: Image.Image | None = Field(default=None, exclude=True)
    """处理后的地图图像"""

    model_config = {
        "arbitrary_types_allowed": True
    }


class Point(BaseModel):
    """资源点/标记点

    后续会支持：自定义标点、从文件读取批量标点、搜索跳转等功能
    """

    id: str
    """点位唯一ID"""

    name: str
    """点位名称"""

    x: float
    """X坐标（场景坐标系）"""

    y: float
    """Y坐标（场景坐标系）"""

    map_id: str
    """所属地图ID"""

    description: str = Field(default="", description="点位描述")
    """点位描述"""

    point_type: str = Field(default="custom", description="点位类型：custom/npc/resource 等")
    """点位类型：custom/npc/resource 等"""


class Route(BaseModel):
    """规划好的路径"""

    points: list[Point] = Field(default_factory=list, description="路径经过的点位列表")
    """路径经过的点位列表"""

    total_distance: float = Field(default=0.0, description="总距离（用于显示）")
    """总距离（可选，用于显示）"""
