"""
路径点模型

用户自定义路径点，不同于内置 NPC 点位。
无 NPC 元数据，仅包含坐标和标签。
"""

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class PathPoint:
    """用户自定义路径点，非NPC点位"""

    point_id: str = field(default_factory=lambda: f"path_{uuid4().hex[:8]}")
    map_x: float = 0.0
    map_y: float = 0.0
    label: str = ""

    @property
    def display_name(self) -> str:
        return self.label or f"路径点 {self.point_id[-6:]}"

    @property
    def area(self) -> None:
        return None  # 路径点无区域信息，距离计算回退到2D
