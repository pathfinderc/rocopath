#!/usr/bin/env python3
"""
自动从 Qt .ui 文件生成 Python UI 代码
"""

import subprocess
import sys
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent
UI_FILE = ROOT_DIR / "assets" / "ui" / "main.ui"
OUTPUT_FILE = ROOT_DIR / "src" / "rocopath" / "ui" / "ui_main.py"


def build_ui():
    if not UI_FILE.exists():
        print(f"错误: 未找到 UI 文件 {UI_FILE}")
        return 1

    try:
        # 使用 pyside6-uic 编译 .ui 到 Python 代码
        result = subprocess.run(
            ["pyside6-uic", str(UI_FILE)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"编译错误:\n{result.stderr}")
            return 1

        # 写入输出文件
        output_content = result.stdout
        # 确保输出目录存在
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(output_content, encoding="utf-8")

        print(f"成功生成 UI 代码: {OUTPUT_FILE}")
        return 0

    except FileNotFoundError:
        print("错误: 未找到 pyside6-uic，请确保已安装 PySide6")
        print("可以使用以下命令安装: pip install pyside6")
        return 1
    except Exception as e:
        print(f"发生错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(build_ui())
