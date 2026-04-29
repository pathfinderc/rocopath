import sys
from pathlib import Path

# ========== 项目路径配置 ==========

# 项目根目录
# PyInstaller 打包后使用 sys._MEIPASS，开发环境使用相对路径
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # PyInstaller 打包环境
    PROJECT_DIR = Path(sys._MEIPASS)
else:
    # 开发环境（src/rocopath 的上两级）
    PROJECT_DIR = Path(__file__).parent.parent.parent

# 资源路径
ASSETS_DIR = PROJECT_DIR / "assets"
MAP_DATA_DIR = ASSETS_DIR / "maps"
MAPS_PC_DIR = MAP_DATA_DIR / "Maps_PC"
MASKS_PC_DIR = MAP_DATA_DIR / "Masks_PC"
DATA_DIR = ASSETS_DIR / "data"


# ========== 地图基础配置 ==========

# 卡洛西亚大陆（整个世界地图）
BIGWORLD_MAP_ID = "10003"
BIGWORLD_NAME = "卡洛西亚大陆"
BIGWORLD_EN_NAME = "bigworld"

# 魔法学院（主城地图）
MAGIC_ACADEMY_MAP_ID = "10018"
MAGIC_ACADEMY_NAME = "魔法学院"
MAGIC_ACADEMY_EN_NAME = "magic_academy"
