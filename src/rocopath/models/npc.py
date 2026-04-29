"""
NPC点位数据模型

整合从多个JSON文件加载的NPC刷新点信息。
"""

from pydantic import BaseModel, Field


class NpcRefreshRule(BaseModel):
    """NPC刷新规则"""

    id: int
    """规则ID"""

    editor_names: list[str] = Field(default_factory=list)
    """编辑器中显示的名称/说明"""

    @property
    def description(self) -> str:
        """获取规则描述"""
        return " ".join(self.editor_names)


class NpcInfo(BaseModel):
    """NPC基础信息"""

    id: int
    """NPC ID"""

    name: str
    """NPC显示名称"""

    editor_name: str
    """编辑器名称"""


class AreaInfo(BaseModel):
    """区域（刷新点位置）信息"""

    id: int
    """区域ID"""

    map_id: str
    """所属地图ID"""

    world_x: int
    """世界X坐标"""

    world_y: int
    """世界Y坐标"""

    world_z: int
    """世界Z坐标"""


class WorldMapInfo(BaseModel):
    """世界地图信息（用于坐标转换）"""

    scene_res_id: str
    """地图ID"""

    name: str
    """地图名称"""

    center_x: int
    """世界中心X坐标"""

    center_y: int
    """世界中心Y坐标"""

    side_length: int
    """世界边长（游戏单位）"""


class NpcPoint(BaseModel):
    """整合后的NPC刷新点

    包含从所有关联表加载来的完整信息，以及转换后的地图坐标。
    """

    refresh_id: int
    """刷新点ID"""

    npc: NpcInfo
    """NPC信息"""

    area: AreaInfo | None = None
    """区域位置信息（没有refresh_param则为None，过滤掉）"""

    refresh_rule: NpcRefreshRule
    """刷新规则"""

    map_x: float
    """转换后地图上的X坐标（像素）"""

    map_y: float
    """转换后地图上的Y坐标（像素）"""

    @property
    def display_name(self) -> str:
        """显示名称"""
        return self.npc.editor_name or self.npc.name 
