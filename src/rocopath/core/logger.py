"""
日志配置

使用 loguru 提供简洁的日志输出，整个应用共享同一个 logger 实例。
"""

from loguru import logger
import sys

# 配置日志格式
# 时间 | 级别 | 文件名:行号 | 消息
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)

# 导出 logger 供整个应用使用
__all__ = ["logger"]
