"""
导出导入面板组件

封装所有导出/导入的UI交互逻辑，保持主窗口代码简洁。
"""

import os
from collections.abc import Callable
from PySide6.QtWidgets import (
    QMainWindow, QMessageBox, QDialog, QPushButton,
    QFileDialog, QFormLayout, QLineEdit
)
from loguru import logger


DEFAULT_NOTES = "本路线从洛寻导出，可能与实际游戏资源点存在差异。"


class ExportImportPanel:
    """导出导入面板组件"""

    def __init__(
        self,
        parent: QMainWindow,
        get_map_scene: Callable,
        get_map_controller: Callable,
        get_current_map_id: Callable[[], str],
        show_status: Callable[[str], None],
    ):
        self._parent = parent
        self._get_map_scene = get_map_scene
        self._get_map_controller = get_map_controller
        self._get_current_map_id = get_current_map_id
        self._show_status = show_status

        # 延迟导入 JSON 生成/解析函数
        from rocopath.exporters.compatible import generate_compatible_json
        from rocopath.exporters.compatible_new import generate_new_compatible_json
        from rocopath.exporters.npc_imp_exp import (
            generate_npc_export_json,
            generate_route_export_json,
            parse_npc_import_json,
            rebuild_npc_points,
        )

        self._generate_compatible_json = generate_compatible_json
        self._generate_new_compatible_json = generate_new_compatible_json
        self._generate_npc_export_json = generate_npc_export_json
        self._generate_route_export_json = generate_route_export_json
        self._parse_npc_import_json = parse_npc_import_json
        self._rebuild_npc_points = rebuild_npc_points

    # ===== 公共方法（供 MainWindow 调用）=====

    def export_new_compatible(self) -> None:
        """导出新版兼容格式路径"""
        self._export_single_or_batch_routes(
            generate_func=self._generate_new_compatible_json,
            dialog_title_single="导出兼容格式路径",
            dialog_title_batch="批量导出兼容格式路径",
        )

    def export_compatible(self) -> None:
        """导出旧版兼容格式路径"""
        self._export_single_or_batch_routes(
            generate_func=self._generate_compatible_json,
            dialog_title_single="导出兼容格式路径",
            dialog_title_batch="批量导出兼容格式路径",
        )

    def export_npc_points(self) -> None:
        """导出全部NPC点位"""
        map_id = self._get_current_map_id()
        if not self._check_map_loaded(map_id, "导出"):
            return

        world_map = self._get_map_controller().get_world_map(map_id)
        if not world_map:
            self._show_warning("无法导出", "当前地图信息未加载，无法导出")
            return

        npc_points = self._get_map_controller().get_all_points(map_id)
        if not npc_points:
            self._show_warning("无法导出", "当前地图没有可导出的NPC点位")
            return

        map_name = world_map.name
        default_filename = f"{map_name}_npc_points.json"
        file_path = self._get_save_file_path("导出NPC点位", default_filename)
        if not file_path:
            return

        json_str = self._generate_npc_export_json(map_id, map_name, world_map, npc_points)

        if self._save_json_file(file_path, json_str):
            msg = f"已成功导出 {len(npc_points)} 个NPC点位到:\n{file_path}"
            self._show_info("导出成功", msg)
            self._show_status(f"导出完成: {file_path}")
            logger.info("NPC点位导出成功: {}", file_path)

    def import_npc_points(self, rebuild_callback: Callable) -> None:
        """导入NPC点位

        Args:
            rebuild_callback: 导入成功后刷新UI的回调
        """
        map_id = self._get_current_map_id()
        if not self._check_map_loaded(map_id, "导入"):
            return

        file_path = self._get_open_file_path("导入NPC点位")
        if not file_path:
            return

        # 读取并解析文件
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json_content = f.read()
        except Exception as e:
            logger.error("读取导入文件失败: {}", str(e))
            self._show_error("读取失败", f"读取文件时出错:\n{str(e)}")
            return

        # 解析JSON
        try:
            _, points_data = self._parse_npc_import_json(json_content)
        except ValueError as e:
            logger.error("解析导入JSON失败: {}", str(e))
            self._show_error("格式错误", f"文件格式不正确:\n{str(e)}")
            return

        if not points_data:
            self._show_warning("没有点位", "文件中没有可导入的NPC点位")
            return

        # 获取刷新规则字典
        refresh_rules = self._get_map_controller().get_refresh_rules_dict()

        # 重建 NpcPoint 对象
        npc_points = self._rebuild_npc_points(points_data, map_id, refresh_rules)

        # 弹出确认对话框
        reply = QMessageBox.question(
            self._parent,
            "确认导入",
            f"检测到 {len(npc_points)} 个点位\n"
            f"导入会与当前地图现有点位合并，已存在的 refresh_id 会被覆盖。\n\n"
            f"是否继续导入？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 添加到地图
        added = self._get_map_controller().add_points(map_id, npc_points)
        total = len(npc_points)
        updated = total - added

        logger.info("NPC点位导入完成: 新增={}, 更新={}", added, updated)

        # 刷新UI
        rebuild_callback()

        # 显示结果
        QMessageBox.information(
            self._parent,
            "导入完成",
            f"导入完成:\n新增 {added} 个点位\n更新 {updated} 个已存在点位\n\n"
            f"当前地图共 {len(self._get_map_controller().get_all_points(map_id))} 个点位",
            QMessageBox.StandardButton.Ok,
        )
        self._show_status(f"导入完成: 新增 {added}, 更新 {updated}")

    def export_current_points(self) -> None:
        """导出当前显示的点位"""
        map_id = self._get_current_map_id()
        if not self._check_map_loaded(map_id, "导出"):
            return

        points = self._get_map_scene().get_all_current_points()
        if not points:
            self._show_warning("无法导出", "当前地图没有显示任何点位，请先搜索或筛选出要导出的点位")
            return

        world_map = self._get_map_controller().get_world_map(map_id)
        if not world_map:
            self._show_warning("无法导出", "当前地图信息未加载，无法导出")
            return

        map_name = world_map.name
        default_filename = f"{map_name}_visible_points.json"
        file_path = self._get_save_file_path("导出当前显示点位", default_filename)
        if not file_path:
            return

        json_str = self._generate_npc_export_json(map_id, map_name, world_map, points)

        if self._save_json_file(file_path, json_str):
            msg = f"已成功导出 {len(points)} 个当前显示点位到:\n{file_path}"
            self._show_info("导出成功", msg)
            self._show_status(f"导出完成: {file_path}")
            logger.info("导出当前显示点位成功: {}", file_path)

    def export_routes(self) -> None:
        """导出所有规划路径"""
        map_id = self._get_current_map_id()
        if not self._check_map_loaded(map_id, "导出"):
            return

        routes = self._get_map_scene().get_planned_routes()
        if not routes:
            self._show_warning("无法导出", "当前地图没有规划任何路径，请先规划路径")
            return

        world_map = self._get_map_controller().get_world_map(map_id)
        if not world_map:
            self._show_warning("无法导出", "当前地图信息未加载，无法导出")
            return

        map_name = world_map.name
        default_filename = f"{map_name}_routes.json"
        file_path = self._get_save_file_path("导出所有已规划路径", default_filename)
        if not file_path:
            return

        json_str = self._generate_route_export_json(map_id, map_name, world_map, routes)

        if self._save_json_file(file_path, json_str):
            msg = f"已成功导出 {len(routes)} 条规划路径到:\n{file_path}"
            self._show_info("导出成功", msg)
            self._show_status(f"导出完成: {file_path}")
            logger.info("导出所有规划路径成功: {}", file_path)

    # ===== 内部辅助函数 =====

    def _check_map_loaded(self, map_id: str, action: str) -> bool:
        """检查是否已加载地图，未加载则显示警告"""
        if not map_id:
            self._show_warning(f"无法{action}", f"当前未加载任何地图，请先加载地图")
            return False
        return True

    def _get_save_file_path(self, caption: str, default_filename: str) -> str:
        """获取保存文件路径"""
        file_path, _ = QFileDialog.getSaveFileName(
            self._parent,
            caption,
            default_filename,
            "JSON 文件 (*.json);;所有文件 (*)",
        )
        return file_path

    def _get_open_file_path(self, caption: str) -> str:
        """获取打开文件路径"""
        file_path, _ = QFileDialog.getOpenFileName(
            self._parent,
            caption,
            "",
            "JSON 文件 (*.json);;所有文件 (*)",
        )
        return file_path

    def _get_directory_path(self, caption: str) -> str:
        """获取目录路径"""
        directory = QFileDialog.getExistingDirectory(
            self._parent,
            caption,
            "",
            QFileDialog.Option.ShowDirsOnly,
        )
        return directory

    def _show_info(self, title: str, message: str) -> None:
        """显示信息消息框"""
        QMessageBox.information(self._parent, title, message, QMessageBox.StandardButton.Ok)

    def _show_warning(self, title: str, message: str) -> None:
        """显示警告消息框"""
        QMessageBox.warning(self._parent, title, message, QMessageBox.StandardButton.Ok)

    def _show_error(self, title: str, message: str) -> None:
        """显示错误消息框"""
        QMessageBox.critical(self._parent, title, message, QMessageBox.StandardButton.Ok)

    def _save_json_file(self, file_path: str, json_str: str) -> bool:
        """保存 JSON 文件，统一处理异常。成功返回 True，失败返回 False"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_str)
            return True
        except Exception as e:
            logger.error("保存文件失败: {}", str(e))
            self._show_error("导出失败", f"保存文件时出错:\n{str(e)}")
            return False

    def _export_single_or_batch_routes(
        self,
        generate_func: Callable,
        dialog_title_single: str,
        dialog_title_batch: str,
    ) -> None:
        """兼容格式导出的通用逻辑（单条/多条路径）

        Args:
            generate_func: 生成 JSON 的函数
            dialog_title_single: 单条路径的对话框标题
            dialog_title_batch: 多条路径的对话框标题
        """
        routes = self._get_map_scene().get_planned_routes()

        if not routes:
            self._show_warning("无法导出", "当前没有已规划好的路径，请先规划至少一条路径")
            return

        # 单条路径：保持原有对话框交互
        if len(routes) == 1:
            # 弹出输入对话框让用户输入 name 和 notes
            dialog = QDialog(self._parent)
            dialog.setWindowTitle(dialog_title_single)
            dialog.setFixedSize(400, 180)
            layout = QFormLayout(dialog)

            name_edit = QLineEdit()
            name_edit.setPlaceholderText("例如：向阳花路线")
            layout.addRow("路径名称:", name_edit)

            notes_edit = QLineEdit()
            notes_edit.setText(DEFAULT_NOTES)
            notes_edit.setDisabled(True)
            layout.addRow("路径说明:", notes_edit)

            ok_button = QPushButton("下一步...")
            ok_button.clicked.connect(dialog.accept)
            cancel_button = QPushButton("取消")
            cancel_button.clicked.connect(dialog.reject)

            button_layout = QFormLayout()
            button_layout.addRow(ok_button)
            button_layout.addRow(cancel_button)
            layout.addRow("", button_layout)

            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            name = name_edit.text().strip()
            notes = notes_edit.text().strip()

            if not name:
                self._show_warning("输入错误", "路径名称不能为空")
                return

            route = routes[0]
            points = [(p.map_x, p.map_y) for p in route.points]

            json_str = generate_func(name, notes, points, loop=False)

            file_path = self._get_save_file_path("保存路径文件", f"{name}.json")
            if not file_path:
                return

            if self._save_json_file(file_path, json_str):
                self._show_info("导出成功", f"路径已成功导出到:\n{file_path}")
                self._show_status(f"导出完成: {file_path}")
                logger.info("兼容格式导出成功: {}", file_path)
            return

        # 多条路径：批量导出
        # 弹出输入对话框让用户输入文件名前缀
        dialog = QDialog(self._parent)
        dialog.setWindowTitle(dialog_title_batch)
        dialog.setFixedSize(420, 160)
        layout = QFormLayout(dialog)

        prefix_edit = QLineEdit()
        prefix_edit.setText("route")
        prefix_edit.setPlaceholderText("文件名前缀，例如 route")
        layout.addRow("文件名前缀:", prefix_edit)

        notes_edit = QLineEdit()
        notes_edit.setText(DEFAULT_NOTES)
        notes_edit.setDisabled(True)
        layout.addRow("路径说明:", notes_edit)

        ok_button = QPushButton("选择导出目录...")
        ok_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.reject)

        button_layout = QFormLayout()
        button_layout.addRow(ok_button)
        button_layout.addRow(cancel_button)
        layout.addRow("", button_layout)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        prefix = prefix_edit.text().strip() or "route"
        notes = notes_edit.text().strip()

        directory = self._get_directory_path("选择导出目录")
        if not directory:
            return

        success_count = 0
        errors: list[str] = []

        for i, route in enumerate(routes, 1):
            filename = f"{prefix}_{i}.json"
            file_path = os.path.join(directory, filename)

            points = [(p.map_x, p.map_y) for p in route.points]
            route_name = f"{prefix}_{i}" if len(routes) > 1 else prefix

            json_str = generate_func(route_name, notes, points, loop=False)

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(json_str)
                success_count += 1
                logger.info("批量导出成功: {}", file_path)
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")
                logger.error("批量导出失败 {}: {}", filename, str(e))

        # 显示结果
        if not errors:
            self._show_info("批量导出成功", f"成功导出 {success_count} 条路径到目录:\n{directory}")
            self._show_status(f"批量导出完成: {success_count} 条路径")
        else:
            if success_count > 0:
                self._show_warning(
                    "部分导出失败",
                    f"成功: {success_count} 条\n失败: {len(errors)} 条\n\n" + "\n".join(errors),
                )
                self._show_status(f"导出完成: {success_count} 成功, {len(errors)} 失败")
            else:
                self._show_error("全部导出失败", "\n".join(errors))
                self._show_status("导出失败")
