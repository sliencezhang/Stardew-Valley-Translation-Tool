import time
from typing import Any
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QProgressBar, QPushButton, QGroupBox,
                               QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QApplication, QWidget)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor

from core.config import config
from core.signal_bus import signal_bus
from ui.styles import get_progress_dialog_style, apply_table_header_style
from ui.widgets import BackgroundWidget, load_background_image


class TranslationProgressDialog(QDialog):
    operationStopped = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.success_rate_label = None
        self.translated_items_label = None
        self.total_items_label = None
        self.setWindowTitle("翻译进度跟踪")
        self.setModal(False)
        self.setMinimumSize(1000, 700)
        
        # 设置无边框窗口和透明背景以实现圆角
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setStyleSheet(get_progress_dialog_style(config.theme))
        
        # 加载背景图片
        self.background_pixmap = load_background_image(config.theme)

        self.current_operation = ""
        self.start_time = None
        self.elapsed_timer = QTimer()
        self.elapsed_timer.timeout.connect(self.update_elapsed_time)
        self.elapsed_seconds = 0

        # 使用更简单的数据结构
        self.file_items = {}  # filename -> 文件信息
        self.translation_items = {}  # (filename, key) -> 翻译项信息
        
        # 智能淘汰策略相关
        self.max_detail_rows = 2000  # 最大显示行数
        self.removable_items = []  # 可淘汰的条目列表 [(时间戳, item_id), ...]
        self.ai_translation_count = 0  # AI翻译计数
        self.cache_hit_count = 0  # 缓存命中计数
        self.incremental_count = 0  # 增量翻译计数
        self.failed_count = 0  # 失败计数

        self.init_ui()

    def init_ui(self):
        # 创建主布局（透明）
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建带背景图片的容器
        self.container_widget = BackgroundWidget(self.background_pixmap, config.theme)
        self.container_widget.setObjectName("dialogContainer")
        container_layout = QVBoxLayout(self.container_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        main_layout.addWidget(self.container_widget)
        
        # 添加自定义标题栏
        from ui.custom_title_bar import CustomTitleBar
        self.title_bar = CustomTitleBar(self)
        container_layout.addWidget(self.title_bar)
        
        # 内容区域
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        container_layout.addWidget(content_widget)

        # 操作信息区域
        layout.addWidget(self._create_info_group())

        # 总体进度区域
        layout.addWidget(self._create_overall_group())

        # 分割器区域
        splitter = self._create_splitter()
        layout.addWidget(splitter)

        # 按钮区域
        layout.addLayout(self._create_button_layout())

        self.setLayout(main_layout)

    def _create_info_group(self):
        """创建操作信息组"""
        info_group = QGroupBox("操作信息")
        info_layout = QVBoxLayout(info_group)

        self.operation_label = QLabel("操作: 无")
        self.operation_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        info_layout.addWidget(self.operation_label)

        # 时间信息和统计信息（一行显示）
        time_stats_layout = QHBoxLayout()
        
        # 左侧：时间信息
        time_stats_layout.addWidget(QLabel("开始时间:"))
        self.start_time_label = QLabel("--:--:--")
        time_stats_layout.addWidget(self.start_time_label)

        time_stats_layout.addWidget(QLabel("已用时间:"))
        self.elapsed_time_label = QLabel("00:00:00")
        time_stats_layout.addWidget(self.elapsed_time_label)

        time_stats_layout.addStretch()

        # 中间：详细统计信息
        detail_stats_labels = ["AI翻译:", "缓存命中:", "增量翻译:", "显示条目:", "失败:"]
        detail_stats_widgets = ["ai_translation_label", "cache_hit_label", "incremental_label", "display_count_label", "failed_label"]
        
        for label_text, widget_name in zip(detail_stats_labels, detail_stats_widgets):
            time_stats_layout.addWidget(QLabel(label_text))
            widget = QLabel("0")
            setattr(self, widget_name, widget)
            time_stats_layout.addWidget(widget)

        time_stats_layout.addStretch()

        # 右侧：统计信息
        stats_labels = ["总键值对:", "未翻译:", "成功率:"]
        stats_widgets = ["total_items_label", "translated_items_label", "success_rate_label"]

        for label_text, widget_name in zip(stats_labels, stats_widgets):
            time_stats_layout.addWidget(QLabel(label_text))
            widget = QLabel("0")
            if widget_name == "success_rate_label":
                widget.setText("0%")
            setattr(self, widget_name, widget)
            time_stats_layout.addWidget(widget)

        info_layout.addLayout(time_stats_layout)
        return info_group

    def _create_overall_group(self):
        """创建总体进度组"""
        overall_group = QGroupBox("总体进度")
        overall_layout = QVBoxLayout(overall_group)

        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        overall_layout.addWidget(self.overall_progress)

        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("进度:"))
        self.progress_percent = QLabel("0%")
        self.progress_percent.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        progress_layout.addWidget(self.progress_percent)

        progress_layout.addWidget(QLabel("状态:"))
        self.status_label = QLabel("等待开始...")
        progress_layout.addWidget(self.status_label)
        progress_layout.addStretch()

        overall_layout.addLayout(progress_layout)
        return overall_group

    def _create_splitter(self):
        """创建分割器"""
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 文件进度表格
        splitter.addWidget(self._create_files_table_widget())

        # 详细翻译表格
        splitter.addWidget(self._create_details_table_widget())

        splitter.setSizes([300, 400])
        return splitter

    def _create_files_table_widget(self):
        """创建文件表格部件"""
        group = QGroupBox("文件进度")
        layout = QVBoxLayout(group)

        self.files_table = QTableWidget()
        self.files_table.setColumnCount(4)
        self.files_table.setHorizontalHeaderLabels(["文件", "状态", "进度", "时间"])
        self.files_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # 设置列宽策略
        header = self.files_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 4):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        
        # 应用表头样式
        apply_table_header_style(self.files_table, config.theme)

        layout.addWidget(self.files_table)
        return group

    def _create_details_table_widget(self):
        """创建详细表格部件"""
        group = QGroupBox("详细翻译进度")
        layout = QVBoxLayout(group)

        self.details_table = QTableWidget()
        self.details_table.setColumnCount(5)
        self.details_table.setHorizontalHeaderLabels(["键", "原文", "译文", "状态", "时间"])
        self.details_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # 设置列宽策略
        header = self.details_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        # 设置最小宽度
        self.details_table.setColumnWidth(0, 200)
        self.details_table.setColumnWidth(3, 80)
        self.details_table.setColumnWidth(4, 80)
        
        # 应用表头样式
        apply_table_header_style(self.details_table, config.theme)

        layout.addWidget(self.details_table)
        return group

    def _create_button_layout(self):
        """创建按钮布局"""
        button_layout = QHBoxLayout()

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)

        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)

        return button_layout

    # ==================== 核心功能方法 ====================

    def start_operation(self, operation_name):
        """开始新操作"""
        self.current_operation = operation_name
        self.operation_label.setText(f"操作: {operation_name}")

        self.start_time = time.time()
        self.elapsed_seconds = 0
        self.start_time_label.setText(time.strftime("%H:%M:%S", time.localtime(self.start_time)))

        self.overall_progress.setValue(0)
        self.progress_percent.setText("0%")
        self.status_label.setText("翻译中...")

        self.files_table.setRowCount(0)
        self.details_table.setRowCount(0)

        self.file_items.clear()
        self.translation_items.clear()
        self.removable_items.clear()
        
        # 重置所有计数
        self.ai_translation_count = 0
        self.cache_hit_count = 0
        self.incremental_count = 0
        self.failed_count = 0

        # 更新所有标签显示
        self.total_items_label.setText("0")
        self.translated_items_label.setText("0")
        self.success_rate_label.setText("0%")
        self.ai_translation_label.setText("0")
        self.cache_hit_label.setText("0")
        self.incremental_label.setText("0")
        self.display_count_label.setText("0")
        self.failed_label.setText("0")

        self.elapsed_timer.start(1000)

        signal_bus.log_message.emit("INFO", f"🚀 开始操作: {operation_name}", {})

    def stop_operation(self):
        """停止当前操作"""
        self.elapsed_timer.stop()
        self.status_label.setText("已停止")
        signal_bus.log_message.emit("INFO", "操作已停止", {})
        self.operationStopped.emit()

    def add_file_progress(self, filename: str, total_items: int = 0):
        """添加文件进度（简化版）"""
        if filename in self.file_items:
            # 文件已存在，更新总数并返回
            self.file_items[filename]['总数'] = total_items
            self._update_statistics()
            return

        row = self.files_table.rowCount()
        self.files_table.insertRow(row)

        # 存储文件信息
        self.file_items[filename] = {
            '行号': row,
            '总数': total_items,
            '译文': 0,
            '状态': '等待',
            '进度': 0
        }

        # 设置表格项
        self._set_table_item(self.files_table, row, 0, filename)
        self._set_table_item(self.files_table, row, 1, "等待", color=self._get_status_color("等待"))
        self._set_table_item(self.files_table, row, 2, "0%")
        self._set_table_item(self.files_table, row, 3, time.strftime("%H:%M:%S"))

        # 更新统计
        self._update_statistics()
        self.files_table.scrollToBottom()

    def update_file_progress(self, filename: str, status: str = None,
                             progress: int = None, translated_count: int = None):
        """更新文件进度（简化版）"""
        if filename not in self.file_items:
            return

        file_info = self.file_items[filename]
        row = file_info['行号']
        
        # 检查行是否仍然有效
        if row < 0 or row >= self.files_table.rowCount():
            # 重新查找行
            row = -1
            for i in range(self.files_table.rowCount()):
                item = self.files_table.item(i, 0)
                if item and item.text() == filename:
                    row = i
                    file_info['行号'] = row
                    break
            
            # 如果找不到有效行，返回
            if row < 0:
                return

        if status is not None:
            file_info['状态'] = status
            color = self._get_status_color(status)
            self._set_table_item(self.files_table, row, 1, status, color=color)

        if progress is not None:
            file_info['进度'] = progress
            self._set_table_item(self.files_table, row, 2, f"{progress}%")

        if translated_count is not None:
            file_info['译文'] = translated_count

        # 更新时间
        self._set_table_item(self.files_table, row, 3, time.strftime("%H:%M:%S"))

        # 更新统计
        self._update_statistics()

    def add_translation_detail(self, filename: str, key: str, original_text: str):
        """添加翻译详情（支持缓存命中）"""
        item_id = (filename, key)

        # 如果已存在，跳过
        if item_id in self.translation_items:
            return

        # 创建新项
        self.translation_items[item_id] = {
            '原文': original_text,
            '译文': '',
            '状态': '等待翻译',  # 默认状态
            '时间': time.time(),
            '行号': None
        }

        # 获取当前行号
        row = self.details_table.rowCount()
        self.translation_items[item_id]['行号'] = row

        # 添加到表格
        self.details_table.insertRow(row)

        self._set_table_item(self.details_table, row, 0, self._shorten_text(key, 80), tooltip=key)
        self._set_table_item(self.details_table, row, 1, self._shorten_text(original_text, 100), tooltip=original_text)
        self._set_table_item(self.details_table, row, 2, "")
        self._set_table_item(self.details_table, row, 3, "等待翻译", color=self._get_status_color("等待翻译"))
        self._set_table_item(self.details_table, row, 4, time.strftime("%H:%M:%S"))

        # 立即刷新界面
        self._force_refresh_table(self.details_table)
        self.details_table.scrollToBottom()

    def update_translation_detail(self, filename: str, key: str,
                                  translated_text: str, status: str = "成功", original_text: str = None):
        """更新翻译详情（智能淘汰版本）"""
        item_id = (filename, key)

        # 如果不存在，直接创建项
        if item_id not in self.translation_items:
            # 检查是否需要淘汰旧条目
            if self.details_table.rowCount() >= self.max_detail_rows:
                self._remove_old_removable_items()
            
            # 如果淘汰后还是满了，则不添加新的可淘汰项
            if self.details_table.rowCount() >= self.max_detail_rows and status in ["增量翻译", "命中缓存"]:
                return
                
            row = self.details_table.rowCount()
            self.details_table.insertRow(row)
            
            # 使用传入的原文，如果没有则使用键
            display_original = original_text if original_text is not None else key
            
            # 恢复变量保护标记后的译文用于显示
            display_translated = self._restore_variables_in_text(translated_text)
            
            current_time = time.time()
            self.translation_items[item_id] = {
                '原文': display_original,
                '译文': translated_text,  # 保存原始译文
                '显示译文': display_translated,  # 保存用于显示的译文
                '状态': status,
                '行号': row,
                '时间': current_time
            }
            
            # 如果是可淘汰的类型，加入淘汰队列
            if status in ["增量翻译", "命中缓存"]:
                self.removable_items.append((current_time, item_id))
            
            # 更新计数
            self._update_status_count(status, 1)
            
            # 设置表格项
            self._set_table_item(self.details_table, row, 0, self._shorten_text(key, 80), tooltip=key)
            self._set_table_item(self.details_table, row, 1, self._shorten_text(display_original, 100), tooltip=display_original)
            self._set_table_item(self.details_table, row, 2, self._shorten_text(display_translated, 100), tooltip=display_translated)
            self._set_table_item(self.details_table, row, 3, status, color=self._get_status_color(status))
            self._set_table_item(self.details_table, row, 4, time.strftime("%H:%M:%S"))
            
            # 更新文件统计（排除质量检查）- 新增条目时更新
            if status in ["完成", "翻译中", "增量翻译", "命中缓存", "成功"] and filename in self.file_items and filename != "quality_issues":
                file_info = self.file_items[filename]
                file_info['译文'] = file_info.get('译文', 0) + 1
                
                # 计算进度
                if file_info['总数'] > 0:
                    progress = min(100, int((file_info['译文'] / file_info['总数']) * 100))
                    # 简化状态显示
                    file_status = "完成" if progress == 100 else "翻译中"
                    
                    self.update_file_progress(filename, file_status, progress, file_info['译文'])
        else:
            # 更新现有项
            item = self.translation_items[item_id]
            old_status = item.get('状态')
            
            # 恢复变量保护标记后的译文用于显示
            display_translated = self._restore_variables_in_text(translated_text)
            
            # 更新译文和状态（包括等待翻译状态）
            item['译文'] = translated_text
            item['显示译文'] = display_translated
            item['状态'] = status
            item['时间'] = time.time()
            
            # 如果状态改变，更新计数和淘汰队列
            if old_status != status:
                if old_status:
                    self._update_status_count(old_status, -1)
                self._update_status_count(status, 1)
                
                # 如果从非成功状态变为成功状态，更新文件的译文计数
                success_statuses = ["完成", "翻译中", "增量翻译", "命中缓存", "成功"]
                if old_status not in success_statuses and status in success_statuses and filename in self.file_items and filename != "quality_issues":
                    file_info = self.file_items[filename]
                    file_info['译文'] = file_info.get('译文', 0) + 1
                    
                    # 更新文件进度
                    if file_info['总数'] > 0:
                        progress = min(100, int((file_info['译文'] / file_info['总数']) * 100))
                        file_status = "完成" if progress == 100 else "翻译中"
                        self.update_file_progress(filename, file_status, progress, file_info['译文'])
                
                # 如果从不可淘汰变为可淘汰
                if old_status not in ["增量翻译", "命中缓存"] and status in ["增量翻译", "命中缓存"]:
                    self.removable_items.append((item['时间'], item_id))
                # 如果从可淘汰变为不可淘汰
                elif old_status in ["增量翻译", "命中缓存"] and status not in ["增量翻译", "命中缓存"]:
                    self.removable_items = [(t, iid) for t, iid in self.removable_items if iid != item_id]
            
            row = item.get('行号', 0)
            if 0 <= row < self.details_table.rowCount():
                self._set_table_item(self.details_table, row, 2, self._shorten_text(display_translated, 100), tooltip=display_translated)
                self._set_table_item(self.details_table, row, 3, status, color=self._get_status_color(status))
                self._set_table_item(self.details_table, row, 4, time.strftime("%H:%M:%S"))

        self._update_statistics()


    @staticmethod
    def _force_refresh_table(table):
        """强制刷新表格"""
        try:
            # 检查表格是否仍然有效
            if table is None or not hasattr(table, 'viewport'):
                return
            
            # 检查表格是否已被销毁
            if not hasattr(table, 'isVisible') or not table.isVisible():
                return
                
            table.viewport().update()
            QApplication.processEvents()
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"表格刷新失败: {e}", {})

    

    # ==================== 辅助方法 ====================

    @staticmethod
    def _set_table_item(table: QTableWidget, row: int, col: int,
                        text: Any, color: QColor = None, tooltip: str = None):
        """安全设置表格项"""
        # 检查表格是否有效
        if table is None:
            return
            
        # 检查行和列是否有效
        if row < 0 or col < 0 or row >= table.rowCount() or col >= table.columnCount():
            return
            
        if not isinstance(text, str):
            text = str(text)

        item = QTableWidgetItem(text)
        if color:
            item.setForeground(color)
        if tooltip:
            item.setToolTip(tooltip)

        table.setItem(row, col, item)

    def _get_status_color(self, status: str) -> QColor:
        """根据状态获取颜色"""
        from core.config import config
        
        # 优先匹配特定的等待状态
        if status == '等待翻译' or status == '等待':
            if config.theme == "dark":
                return QColor(158, 158, 158)  # 浅灰色
            else:
                return QColor(128, 128, 128)  # 灰色
        
        # # 检查是否是动态状态（包含特定关键词）
        # if 'AI翻译' in status or '翻译' in status:
        #     if config.theme == "dark":
        #         return QColor(100, 181, 246)  # 浅蓝色
        #     else:
        #         return QColor(0, 0, 255)  # 蓝色
        
        if config.theme == "dark":
            # 深色主题的颜色
            status_colors = {
                # 文件状态
                '完成': QColor(102, 187, 106),  # 浅绿色
                '错误': QColor(239, 83, 80),  # 浅红色
                '翻译中': QColor(100, 181, 246),  # 浅蓝色
                '等待': QColor(158, 158, 158),  # 浅灰色
                '开始处理': QColor(100, 181, 246),  # 浅蓝色

                # 翻译进度
                '成功': QColor(102, 187, 106),  # 浅绿色
                '失败': QColor(239, 83, 80),  # 浅红色
                '增量翻译': QColor(129, 199, 132),  # 更浅的绿色
                '命中缓存': QColor(255, 183, 77),  # 浅橙色
                '等待翻译': QColor(158, 158, 158),  # 浅灰色
            }
        else:
            # 浅色主题的颜色
            status_colors = {
                # 文件状态
                '完成': QColor(0, 128, 0),  # 绿色
                '错误': QColor(255, 0, 0),  # 红色
                '翻译中': QColor(0, 0, 255),  # 蓝色
                '等待': QColor(128, 128, 128),  # 灰色
                '开始处理': QColor(0, 0, 255),  # 蓝色

                # 翻译进度
                '成功': QColor(0, 128, 0),  # 绿色
                '失败': QColor(255, 0, 0),  # 红色
                '增量翻译': QColor(0, 200, 0),  # 亮绿色
                '命中缓存': QColor(255, 165, 0),  # 橙色
                '等待翻译': QColor(128, 128, 128),  # 灰色
            }
        return status_colors.get(status, QColor(0, 0, 0))

    def _update_statistics(self):
        """更新统计信息"""
        total_translated = sum(item['译文'] for item in self.file_items.values())
        total_items = sum(item['总数'] for item in self.file_items.values())
        # 计算未翻译数量
        total_untranslated = total_items - total_translated

        self.total_items_label.setText(str(total_items))
        self.translated_items_label.setText(str(total_untranslated))  # 显示未翻译数量
        
        # 更新显示条目数
        self.display_count_label.setText(f"{self.details_table.rowCount()}/{self.max_detail_rows}")

        if total_items > 0:
            success_rate = (total_translated / total_items) * 100
            self.success_rate_label.setText(f"{success_rate:.1f}%")
        else:
            self.success_rate_label.setText("0%")

    def _restore_variables_in_text(self, text: str) -> str:
        """恢复文本中的变量保护标记"""
        if not text or not text.strip():
            return text
        
        # 延迟导入避免循环依赖
        from core.variable_protector import VariableProtector
        
        # 创建临时保护器实例
        protector = VariableProtector()
        
        # 检查文本中是否有任何保护标记
        # 新的标记格式：<VAR>XXX</VAR>
        has_markers = '<VAR>' in text and '</VAR>' in text
        
        if has_markers:
            # 尝试从翻译引擎获取全局变量映射
            if hasattr(self, 'parent') and self.parent():
                main_window = self.parent()
                if hasattr(main_window, 'translation_executor') and main_window.translation_executor:
                    if hasattr(main_window.translation_executor, 'engine') and main_window.translation_executor.engine:
                        if hasattr(main_window.translation_executor.engine, 'variable_protector'):
                            protector = main_window.translation_executor.engine.variable_protector
            
            # 使用保护器恢复变量
            restored = protector.restore_variables(text)
            
            # 如果恢复后仍有标记，可能是旧缓存的标记，尝试清理
            if '<VAR>' in restored and '</VAR>' in restored:
                # 尝试清理剩余的标记（将它们移除，而不是替换为变量）
                import re
                # 移除所有<VAR>XXX</VAR>格式的标记
                pattern = r'<VAR>[A-Za-z0-9]*</VAR>'
                restored = re.sub(pattern, '', restored)
                # 清理多余的空格
                restored = re.sub(r'\s+', ' ', restored).strip()
            
            return restored
        
        # 如果没有保护标记，直接返回原文本
        return text

    @staticmethod
    def _shorten_text(text: str, max_length: int) -> str:
        """缩短文本显示"""
        if not text or not isinstance(text, str):
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    def _remove_old_removable_items(self):
        """淘汰旧的可淘汰条目"""
        if not self.removable_items:
            return
        
        # 按时间排序，最早的在前
        self.removable_items.sort(key=lambda x: x[0])
        
        # 计算需要删除的数量（删除80%的可淘汰项）
        remove_count = max(1, len(self.removable_items) * 8 // 10)
        
        # 批量删除
        items_to_remove = self.removable_items[:remove_count]
        
        for _, item_id in items_to_remove:
            if item_id in self.translation_items:
                item = self.translation_items[item_id]
                row = item.get('行号', -1)
                
                if 0 <= row < self.details_table.rowCount():
                    # 删除表格行
                    self.details_table.removeRow(row)
                    
                    # 更新后续行的行号
                    for other_id, other_item in self.translation_items.items():
                        if other_item.get('行号', -1) > row:
                            other_item['行号'] -= 1
                    
                    # 更新计数
                    status = item.get('状态')
                    if status:
                        self._update_status_count(status, -1)
                
                # 从字典中删除
                del self.translation_items[item_id]
        
        # 从可淘汰列表中移除
        self.removable_items = self.removable_items[remove_count:]
        
        signal_bus.log_message.emit("DEBUG", f"已淘汰 {remove_count} 条旧的缓存/增量翻译记录", {})

    def _update_status_count(self, status: str, delta: int):
        """更新状态计数"""
        if status == "成功" or status == "失败":
            self.ai_translation_count += delta
            self.ai_translation_label.setText(str(self.ai_translation_count))
        elif status == "命中缓存":
            self.cache_hit_count += delta
            self.cache_hit_label.setText(str(self.cache_hit_count))
        elif status == "增量翻译":
            self.incremental_count += delta
            self.incremental_label.setText(str(self.incremental_count))
        elif status == "失败":
            self.failed_count += delta
            self.failed_label.setText(str(self.failed_count))

    def update_elapsed_time(self):
        """更新已用时间"""
        self.elapsed_seconds += 1
        hours = self.elapsed_seconds // 3600
        minutes = (self.elapsed_seconds % 3600) // 60
        seconds = self.elapsed_seconds % 60
        self.elapsed_time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def update_overall_progress(self, progress: int):
        """更新总体进度"""
        if isinstance(progress, (int, float)):
            progress = int(progress)
            self.overall_progress.setValue(progress)
            self.progress_percent.setText(f"{progress}%")

    def operation_completed(self, success: bool = True):
        """操作完成"""
        self.elapsed_timer.stop()

        if success:
            self.status_label.setText("完成")
            signal_bus.log_message.emit("SUCCESS","操作完成！",{})

            # 显示最终统计
            total_items = sum(item['总数'] for item in self.file_items.values())
            total_translated = sum(item['译文'] for item in self.file_items.values())

            if total_items > 0:
                success_rate = (total_translated / total_items * 100)
                stats_msg = (
                    f"📊 最终统计: 成功 {total_translated}/{total_items} ({success_rate:.1f}%) | "
                    f"AI翻译: {self.ai_translation_count} | "
                    f"缓存命中: {self.cache_hit_count} | "
                    f"增量翻译: {self.incremental_count} | "
                    f"失败: {self.failed_count}"
                )
                signal_bus.log_message.emit("INFO", stats_msg, {})
        else:
            self.status_label.setText("失败")
            signal_bus.log_message.emit("ERROR", "操作失败！", {})


    def showEvent(self, event):
        """显示事件 - 设置位置"""
        super().showEvent(event)
        if self.parent():
            parent_geometry = self.parent().geometry()
            # 水平居中，垂直往下偏移
            x = parent_geometry.left() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.top() + 20
            self.move(x, y)

    def closeEvent(self, event):
        """关闭事件"""
        self.elapsed_timer.stop()
        # 延迟发送信号，确保窗口完全关闭后再触发质量检查
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, signal_bus.translationDialogClosed.emit)
        super().closeEvent(event)

    def force_refresh(self):
        """强制刷新界面"""
        try:
            self.details_table.viewport().update()
            self.files_table.viewport().update()
            app = QApplication.instance()
            if app:
                app.processEvents()
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"强制刷新失败: {e}", {})
    
    def update_theme(self):
        """更新主题样式"""
        if hasattr(self, 'title_bar'):
            self.title_bar.update_theme()
        self.setStyleSheet(get_progress_dialog_style(config.theme))
        apply_table_header_style(self.files_table, config.theme)
        apply_table_header_style(self.details_table, config.theme)