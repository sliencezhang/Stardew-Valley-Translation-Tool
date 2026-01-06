# ui/dialogs/name_detection_result_dialog.py
import os
import json
from typing import List, Dict
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QTableWidget, QTableWidgetItem,
                               QHeaderView, QSplitter, QFileDialog, QWidget, QCheckBox)
from PySide6.QtCore import Qt

from core.config import config
from core.signal_bus import signal_bus
from core.terminology_manager import TerminologyManager
from ui.styles import get_dialog_style, apply_table_header_style, get_red_button_style
from ui.widgets import BackgroundWidget, load_background_image
from ui.custom_message_box import CustomMessageBox


class NameDetectionResultDialog(QDialog):
    """人名地名检测结果对话框"""
    
    def __init__(self, results_list: List[Dict], project_manager, parent=None):
        super().__init__(parent)
        # 过滤掉中文列中有符号的结果
        self.results_list = self.filter_results_with_symbols(results_list)
        # 按置信度倒序排列
        self.results_list.sort(key=lambda x: x['confidence'], reverse=True)
        self.confirmed_list = []  # 已确认的列表
        self.project_manager = project_manager
        # 排序状态
        self.pending_sort_column = 2  # 置信度列
        self.pending_sort_order = Qt.SortOrder.DescendingOrder  # 默认倒序
        self.confirmed_sort_column = -1
        self.confirmed_sort_order = Qt.SortOrder.AscendingOrder
        
        # 加载背景图片
        self.background_pixmap = load_background_image(config.theme)
        
        self.init_ui()
        self.populate_pending_table()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("人名地名检测结果")
        self.setGeometry(200, 200, 1000, 700)
        
        # 设置无边框窗口和透明背景以实现圆角
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setStyleSheet(get_dialog_style(config.theme))
        
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
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)  # 添加边距
        content_layout.setSpacing(10)  # 设置合适的间距
        container_layout.addWidget(content_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：待确认列表
        left_widget = self.create_pending_widget()
        splitter.addWidget(left_widget)
        
        # 右侧：已确认列表
        right_widget = self.create_confirmed_widget()
        splitter.addWidget(right_widget)
        
        # 设置分割比例
        splitter.setSizes([500, 500])
        
        content_layout.addWidget(splitter)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        
        self.export_pending_btn = QPushButton("📄 导出待确认")
        self.export_pending_btn.clicked.connect(self.export_pending_results)
        bottom_layout.addWidget(self.export_pending_btn)
        
        self.export_confirmed_btn = QPushButton("📄 导出已确认")
        self.export_confirmed_btn.clicked.connect(self.export_confirmed_results)
        bottom_layout.addWidget(self.export_confirmed_btn)
        
        self.append_to_terminology_btn = QPushButton("➕ 已确认追加到术语表")
        self.append_to_terminology_btn.clicked.connect(self.append_confirmed_to_terminology)
        self.append_to_terminology_btn.setEnabled(False)
        bottom_layout.addWidget(self.append_to_terminology_btn)
        
        bottom_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)
        
        content_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)
    
    def create_pending_widget(self):
        """创建待确认列表组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标题和操作按钮
        header_layout = QHBoxLayout()
        
        # 待确认标题和数量统计
        pending_title_layout = QHBoxLayout()
        title_label = QLabel("待确认列表")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        pending_title_layout.addWidget(title_label)
        
        self.pending_count_label = QLabel("(0项)")
        self.pending_count_label.setStyleSheet("color: gray; font-size: 12px;")
        pending_title_layout.addWidget(self.pending_count_label)
        
        header_layout.addLayout(pending_title_layout)
        header_layout.addStretch()
        
        # 选择操作按钮
        self.select_all_pending_btn = QPushButton("全选")
        self.select_all_pending_btn.clicked.connect(self.select_all_pending)
        self.select_all_pending_btn.setMaximumWidth(60)
        header_layout.addWidget(self.select_all_pending_btn)
        
        self.deselect_all_pending_btn = QPushButton("反选")
        self.deselect_all_pending_btn.clicked.connect(self.deselect_all_pending)
        self.deselect_all_pending_btn.setMaximumWidth(60)
        header_layout.addWidget(self.deselect_all_pending_btn)
        
        self.move_to_confirmed_btn = QPushButton("➡️ 移动到已确认")
        self.move_to_confirmed_btn.clicked.connect(self.move_to_confirmed)
        self.move_to_confirmed_btn.setEnabled(False)
        header_layout.addWidget(self.move_to_confirmed_btn)
        
        self.delete_pending_btn = QPushButton("🗑️ 删除选中")
        self.delete_pending_btn.clicked.connect(self.delete_selected_pending)
        self.delete_pending_btn.setEnabled(False)
        self.delete_pending_btn.setStyleSheet(get_red_button_style(config.theme))
        header_layout.addWidget(self.delete_pending_btn)
        
        layout.addLayout(header_layout)
        
        # 表格
        self.pending_table = QTableWidget()
        self.pending_table.setColumnCount(4)
        self.pending_table.setHorizontalHeaderLabels(["英文", "中文", "置信度", "选择"])
        self.pending_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # 设置表格列宽
        header = self.pending_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 50)  # 设置选择列宽度为50像素
        
        # 应用表头样式
        apply_table_header_style(self.pending_table, config.theme)
        
        # 设置选择样式
        if config.theme == "dark":
            self.pending_table.setStyleSheet("""
                QTableWidget::item:selected {
                    background-color: #455a64;
                    color: #e0e0e0;
                }
                QTableWidget::item:selected:hover {
                    background-color: #546e7a;
                }
                QTableWidget {
                    alternate-background-color: #2b2b2b;
                    background-color: #1e1e1e;
                    color: #e0e0e0;
                }
            """)
        else:
            self.pending_table.setStyleSheet("""
                QTableWidget::item:selected {
                    background-color: #0078d4;
                    color: white;
                }
                QTableWidget::item:selected:hover {
                    background-color: #106ebe;
                }
                QTableWidget {
                    alternate-background-color: #f5f5f5;
                }
            """)
        
        # 连接选择变化信号
        self.pending_table.itemSelectionChanged.connect(self.on_pending_selection_changed)
        self.pending_table.itemChanged.connect(self.on_pending_item_changed)
        # 连接表头点击信号用于排序
        self.pending_table.horizontalHeader().sectionClicked.connect(self.on_pending_header_clicked)
        
        layout.addWidget(self.pending_table)
        
        return widget
    
    def create_confirmed_widget(self):
        """创建已确认列表组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标题和操作按钮
        header_layout = QHBoxLayout()
        title_label = QLabel("已确认列表")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title_label)
        
        self.confirmed_count_label = QLabel("(0项)")
        self.confirmed_count_label.setStyleSheet("color: gray; font-size: 12px;")
        header_layout.addWidget(self.confirmed_count_label)
        header_layout.addStretch()
        
        # 选择操作按钮
        self.select_all_confirmed_btn = QPushButton("全选")
        self.select_all_confirmed_btn.clicked.connect(self.select_all_confirmed)
        self.select_all_confirmed_btn.setMaximumWidth(60)
        header_layout.addWidget(self.select_all_confirmed_btn)
        
        self.deselect_all_confirmed_btn = QPushButton("反选")
        self.deselect_all_confirmed_btn.clicked.connect(self.deselect_all_confirmed)
        self.deselect_all_confirmed_btn.setMaximumWidth(60)
        header_layout.addWidget(self.deselect_all_confirmed_btn)
        
        self.move_back_btn = QPushButton("⬅️ 移回待确认")
        self.move_back_btn.clicked.connect(self.move_back_to_pending)
        self.move_back_btn.setEnabled(False)
        header_layout.addWidget(self.move_back_btn)
        
        self.delete_confirmed_btn = QPushButton("🗑️ 删除选中")
        self.delete_confirmed_btn.clicked.connect(self.delete_selected_confirmed)
        self.delete_confirmed_btn.setEnabled(False)
        self.delete_confirmed_btn.setStyleSheet(get_red_button_style(config.theme))
        header_layout.addWidget(self.delete_confirmed_btn)
        
        layout.addLayout(header_layout)
        
        # 表格
        self.confirmed_table = QTableWidget()
        self.confirmed_table.setColumnCount(4)
        self.confirmed_table.setHorizontalHeaderLabels(["英文", "中文", "置信度", "选择"])
        self.confirmed_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # 设置表格列宽
        header = self.confirmed_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 50)  # 设置选择列宽度为50像素
        
        # 应用表头样式
        apply_table_header_style(self.confirmed_table, config.theme)
        
        # 设置选择样式
        self.confirmed_table.setStyleSheet(self.pending_table.styleSheet())
        
        # 连接选择变化信号
        self.confirmed_table.itemSelectionChanged.connect(self.on_confirmed_selection_changed)
        self.confirmed_table.itemChanged.connect(self.on_confirmed_item_changed)
        # 连接表头点击信号用于排序
        self.confirmed_table.horizontalHeader().sectionClicked.connect(self.on_confirmed_header_clicked)
        
        layout.addWidget(self.confirmed_table)
        
        return widget
    
    def filter_results_with_symbols(self, results_list: List[Dict]) -> List[Dict]:
        """过滤掉中文列中有符号的结果"""
        filtered_results = []
        # 扩展符号列表，包含更多中文标点符号
        symbols = '.,?!:;—–…()[]{}""''《》【】""''<>《》【】、。，；：？！""''（）【】《》""''、。·'
        symbols += '～@#$%^&*+=|\\/`~!@#$%^&*()_+-={}[]|:";\'<>?,./'
        
        for item in results_list:
            zh_text = item['zh']
            # 检查中文文本中是否包含符号
            has_symbol = any(char in symbols for char in zh_text)
            if not has_symbol:
                filtered_results.append(item)
        
        return filtered_results
    
    def populate_pending_table(self):
        """填充待确认表格"""
        from PySide6.QtWidgets import QCheckBox
        
        self.pending_table.setRowCount(len(self.results_list))
        for i, item in enumerate(self.results_list):
            # 英文
            self.pending_table.setItem(i, 0, QTableWidgetItem(item['en']))
            # 中文
            self.pending_table.setItem(i, 1, QTableWidgetItem(item['zh']))
            # 置信度
            self.pending_table.setItem(i, 2, QTableWidgetItem(f"{item['confidence']:.2f}"))
            # 选择复选框 - 使用QCheckBox控件
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            checkbox.stateChanged.connect(self.on_pending_checkbox_changed)
            self.pending_table.setCellWidget(i, 3, checkbox)
        
        # 设置默认排序指示器
        self.update_header_sort_indicator(self.pending_table, 2, Qt.SortOrder.DescendingOrder)
        # 更新数量统计
        self.update_count_labels()
    
    def update_count_labels(self):
        """更新数量统计标签"""
        pending_count = self.pending_table.rowCount()
        confirmed_count = self.confirmed_table.rowCount()
        self.pending_count_label.setText(f"({pending_count}项)")
        self.confirmed_count_label.setText(f"({confirmed_count}项)")
    
    def on_pending_selection_changed(self):
        """待确认列表选择变化"""
        has_selection = len(self.pending_table.selectedItems()) > 0
        self.delete_pending_btn.setEnabled(has_selection)
    
    def on_confirmed_selection_changed(self):
        """已确认列表选择变化"""
        has_selection = len(self.confirmed_table.selectedItems()) > 0
        self.delete_confirmed_btn.setEnabled(has_selection)
        self.move_back_btn.setEnabled(has_selection)
    
    def on_pending_checkbox_changed(self):
        """待确认列表checkbox状态变化"""
        has_checked = False
        for row in range(self.pending_table.rowCount()):
            widget = self.pending_table.cellWidget(row, 3)
            if isinstance(widget, QCheckBox):
                if widget.isChecked():
                    has_checked = True
                    break
        self.move_to_confirmed_btn.setEnabled(has_checked)
        self.delete_pending_btn.setEnabled(has_checked)
    
    def on_confirmed_checkbox_changed(self):
        """已确认列表checkbox状态变化"""
        has_checked = False
        for row in range(self.confirmed_table.rowCount()):
            widget = self.confirmed_table.cellWidget(row, 3)
            if isinstance(widget, QCheckBox):
                if widget.isChecked():
                    has_checked = True
                    break
        self.move_back_btn.setEnabled(has_checked)
        self.delete_confirmed_btn.setEnabled(has_checked)
    
    def on_pending_item_changed(self, item):
        """待确认列表项目变化 - 保留用于其他列"""
        pass
    
    def on_confirmed_item_changed(self, item):
        """已确认列表项目变化 - 保留用于其他列"""
        pass
    
    def move_to_confirmed(self):
        """移动选中的项目到已确认列表"""
        # 获取选中的行
        selected_rows = []
        for i in range(self.pending_table.rowCount()):
            widget = self.pending_table.cellWidget(i, 3)
            if isinstance(widget, QCheckBox):
                if widget.isChecked():
                    selected_rows.append(i)
        
        if not selected_rows:
            return
        
        # 移动项目
        items_to_move = []
        for row in reversed(selected_rows):  # 从后往前删除
            # 获取数据
            en_item = self.pending_table.item(row, 0)  # 英文现在是第0列
            zh_item = self.pending_table.item(row, 1)  # 中文现在是第1列
            conf_item = self.pending_table.item(row, 2)  # 置信度现在是第2列
            
            if en_item and zh_item and conf_item:
                items_to_move.append({
                    'en': en_item.text(),
                    'zh': zh_item.text(),
                    'confidence': float(conf_item.text())
                })
            
            # 从待确认列表删除
            self.pending_table.removeRow(row)
            del self.results_list[row]
        
        # 添加到已确认列表
        for item in items_to_move:
            self.confirmed_list.append(item)
        
        # 刷新已确认表格
        self.refresh_confirmed_table()
        
        # 更新按钮状态
        self.move_to_confirmed_btn.setEnabled(False)
        self.append_to_terminology_btn.setEnabled(True)
        
        # 更新数量统计
        self.update_count_labels()
        
        signal_bus.log_message.emit("INFO", f"已移动 {len(items_to_move)} 个项目到已确认列表", {})
    
    def move_back_to_pending(self):
        """移动选中的项目回待确认列表"""
        # 获取选中的行
        selected_rows = []
        for i in range(self.confirmed_table.rowCount()):
            widget = self.confirmed_table.cellWidget(i, 3)
            if isinstance(widget, QCheckBox):
                if widget.isChecked():
                    selected_rows.append(i)
        
        if not selected_rows:
            return
        
        # 移动项目
        items_to_move = []
        for row in reversed(selected_rows):  # 从后往前删除
            # 获取数据
            en_item = self.confirmed_table.item(row, 0)  # 英文现在是第0列
            zh_item = self.confirmed_table.item(row, 1)  # 中文现在是第1列
            conf_item = self.confirmed_table.item(row, 2)  # 置信度现在是第2列
            
            if en_item and zh_item and conf_item:
                items_to_move.append({
                    'en': en_item.text(),
                    'zh': zh_item.text(),
                    'confidence': float(conf_item.text())
                })
            
            # 从已确认列表删除
            self.confirmed_table.removeRow(row)
            del self.confirmed_list[row]
        
        # 添加回待确认列表
        for item in items_to_move:
            self.results_list.append(item)
        
        # 刷新待确认表格
        self.refresh_pending_table()
        
        # 更新按钮状态
        self.move_back_btn.setEnabled(False)
        if not self.confirmed_list:
            self.append_to_terminology_btn.setEnabled(False)
        
        # 更新数量统计
        self.update_count_labels()
        
        signal_bus.log_message.emit("INFO", f"已移回 {len(items_to_move)} 个项目到待确认列表", {})
    
    def delete_selected_pending(self):
        """删除待确认列表中的选中项"""
        selected_rows = []
        for i in range(self.pending_table.rowCount()):
            widget = self.pending_table.cellWidget(i, 3)
            if isinstance(widget, QCheckBox):
                if widget.isChecked():
                    selected_rows.append(i)
        
        if not selected_rows:
            return
        
        reply = CustomMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的 {len(selected_rows)} 个项目吗？"
        )
        
        if reply == CustomMessageBox.Yes:
            for row in reversed(selected_rows):
                self.pending_table.removeRow(row)
                del self.results_list[row]
            
            self.move_to_confirmed_btn.setEnabled(False)
            signal_bus.log_message.emit("INFO", f"已删除 {len(selected_rows)} 个项目", {})
            
            # 更新数量统计
            self.update_count_labels()
    
    def delete_selected_confirmed(self):
        """删除已确认列表中的选中项"""
        selected_rows = []
        for i in range(self.confirmed_table.rowCount()):
            widget = self.confirmed_table.cellWidget(i, 3)
            if isinstance(widget, QCheckBox):
                if widget.isChecked():
                    selected_rows.append(i)
        
        if not selected_rows:
            return
        
        reply = CustomMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的 {len(selected_rows)} 个项目吗？"
        )
        
        if reply == CustomMessageBox.Yes:
            for row in reversed(selected_rows):
                self.confirmed_table.removeRow(row)
                del self.confirmed_list[row]
            
            self.move_back_btn.setEnabled(False)
            if not self.confirmed_list:
                self.append_to_terminology_btn.setEnabled(False)
            signal_bus.log_message.emit("INFO", f"已删除 {len(selected_rows)} 个项目", {})
            
            # 更新数量统计
            self.update_count_labels()
    
    def refresh_pending_table(self):
        """刷新待确认表格"""
        self.pending_table.setRowCount(0)
        self.populate_pending_table()
    
    def refresh_confirmed_table(self):
        """刷新已确认表格"""
        from PySide6.QtWidgets import QCheckBox
        
        self.confirmed_table.setRowCount(len(self.confirmed_list))
        for i, item in enumerate(self.confirmed_list):
            # 英文
            self.confirmed_table.setItem(i, 0, QTableWidgetItem(item['en']))
            # 中文
            self.confirmed_table.setItem(i, 1, QTableWidgetItem(item['zh']))
            # 置信度
            self.confirmed_table.setItem(i, 2, QTableWidgetItem(f"{item['confidence']:.2f}"))
            # 选择复选框 - 使用QCheckBox控件
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            checkbox.stateChanged.connect(self.on_confirmed_checkbox_changed)
            self.confirmed_table.setCellWidget(i, 3, checkbox)
    
    def export_pending_results(self):
        """导出待确认结果"""
        if not self.results_list:
            CustomMessageBox.warning(self, "警告", "没有可导出的结果")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出待确认结果",
            os.path.join(self.project_manager.current_project.path if self.project_manager else "", "pending_names.json"),
            "JSON文件 (*.json)"
        )
        
        if file_path:
            try:
                result_data = []
                for item in self.results_list:
                    result_data.append({
                        'en': item['en'],
                        'zh': item['zh'],
                        'confidence': item['confidence']
                    })
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)
                
                CustomMessageBox.information(self, "成功", f"结果已导出到：{file_path}")
                signal_bus.log_message.emit("INFO", f"待确认结果已导出到：{file_path}", {})
            except Exception as e:
                CustomMessageBox.critical(self, "错误", f"导出失败：{str(e)}")
                signal_bus.log_message.emit("ERROR", f"导出待确认结果失败：{str(e)}", {})
    
    def export_confirmed_results(self):
        """导出已确认结果"""
        if not self.confirmed_list:
            CustomMessageBox.warning(self, "警告", "没有可导出的结果")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出已确认结果",
            os.path.join(self.project_manager.current_project.path if self.project_manager else "", "confirmed_names.json"),
            "JSON文件 (*.json)"
        )
        
        if file_path:
            try:
                result_data = []
                for item in self.confirmed_list:
                    result_data.append({
                        'en': item['en'],
                        'zh': item['zh'],
                        'confidence': item['confidence']
                    })
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)
                
                CustomMessageBox.information(self, "成功", f"结果已导出到：{file_path}")
                signal_bus.log_message.emit("INFO", f"已确认结果已导出到：{file_path}", {})
            except Exception as e:
                CustomMessageBox.critical(self, "错误", f"导出失败：{str(e)}")
                signal_bus.log_message.emit("ERROR", f"导出已确认结果失败：{str(e)}", {})
    
    def append_confirmed_to_terminology(self):
        """将已确认的术语追加到术语表"""
        if not self.confirmed_list:
            CustomMessageBox.warning(self, "警告", "没有可追加的结果")
            return
        
        reply = CustomMessageBox.question(
            self,
            "确认追加",
            f"确定要将 {len(self.confirmed_list)} 个已确认的术语追加到术语表吗？\n"
            "注意：已存在的术语将被覆盖。"
        )
        
        if reply == CustomMessageBox.Yes:
            try:
                # 创建术语管理器
                terminology_manager = TerminologyManager()
                
                # 使用当前Python项目的resources目录
                from core.config import get_resource_path
                terminology_path = get_resource_path("resources/terminology.json")
                
                # 加载现有术语表
                if os.path.exists(terminology_path):
                    with open(terminology_path, 'r', encoding='utf-8') as f:
                        existing_terms = json.load(f)
                    signal_bus.log_message.emit("INFO", f"加载了 {len(existing_terms)} 个现有术语", {})
                    # 将现有术语添加到管理器
                    for en, zh in existing_terms.items():
                        terminology_manager.add_terminology(en, zh)
                    signal_bus.log_message.emit("INFO", f"管理器中现有术语数量: {terminology_manager.get_term_count()}", {})
                else:
                    signal_bus.log_message.emit("INFO", "术语表文件不存在，将创建新的", {})
                
                # 追加新术语
                added_count = 0
                for item in self.confirmed_list:
                    en_term = item['en']
                    zh_term = item['zh']
                    if en_term and zh_term:
                        terminology_manager.add_terminology(en_term, zh_term)
                        added_count += 1
                        signal_bus.log_message.emit("DEBUG", f"添加术语: {en_term} -> {zh_term}", {})
                
                # 保存术语表
                signal_bus.log_message.emit("DEBUG", f"当前术语数量: {terminology_manager.get_term_count()}", {})
                
                # 确保目录存在
                os.makedirs(os.path.dirname(terminology_path), exist_ok=True)
                
                if terminology_manager.save_terminology(terminology_path):
                    signal_bus.terminology_updated.emit()
                    CustomMessageBox.information(self, "成功", f"已成功追加 {added_count} 个术语到术语表\n保存路径: {terminology_path}")
                    signal_bus.log_message.emit("INFO", f"已追加 {added_count} 个术语到术语表", {})
                else:
                    raise Exception("保存术语表失败")
                
            except Exception as e:
                CustomMessageBox.critical(self, "错误", f"追加到术语表失败：{str(e)}")
                signal_bus.log_message.emit("ERROR", f"追加到术语表失败：{str(e)}", {})
    
    def on_pending_header_clicked(self, column):
        """待确认列表表头点击事件"""
        # 跳过选择列（现在是第3列）
        if column == 3:
            return
        
        # 切换排序顺序
        if self.pending_sort_column == column:
            self.pending_sort_order = Qt.SortOrder.DescendingOrder if self.pending_sort_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        else:
            self.pending_sort_column = column
            self.pending_sort_order = Qt.SortOrder.AscendingOrder
        
        # 执行排序
        self.sort_pending_table()
    
    def on_confirmed_header_clicked(self, column):
        """已确认列表表头点击事件"""
        # 跳过选择列（现在是第3列）
        if column == 3:
            return
        
        # 切换排序顺序
        if self.confirmed_sort_column == column:
            self.confirmed_sort_order = Qt.SortOrder.DescendingOrder if self.confirmed_sort_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        else:
            self.confirmed_sort_column = column
            self.confirmed_sort_order = Qt.SortOrder.AscendingOrder
        
        # 执行排序
        self.sort_confirmed_table()
    
    def sort_pending_table(self):
        """对待确认列表进行排序"""
        if self.pending_sort_column == -1:
            return
        
        # 获取排序键
        sort_key = None
        if self.pending_sort_column == 0:  # 英文列（现在是第0列）
            sort_key = lambda x: x['en'].lower()
        elif self.pending_sort_column == 1:  # 中文列（现在是第1列）
            sort_key = lambda x: x['zh']
        elif self.pending_sort_column == 2:  # 置信度列（现在是第2列）
            sort_key = lambda x: x['confidence']
        
        if sort_key:
            # 执行排序
            reverse = (self.pending_sort_order == Qt.SortOrder.DescendingOrder)
            self.results_list.sort(key=sort_key, reverse=reverse)
            
            # 重新填充表格
            self.refresh_pending_table()
            
            # 更新表头显示排序方向
            self.update_header_sort_indicator(self.pending_table, self.pending_sort_column, self.pending_sort_order)
    
    def sort_confirmed_table(self):
        """对已确认列表进行排序"""
        if self.confirmed_sort_column == -1:
            return
        
        # 获取排序键
        sort_key = None
        if self.confirmed_sort_column == 0:  # 英文列（现在是第0列）
            sort_key = lambda x: x['en'].lower()
        elif self.confirmed_sort_column == 1:  # 中文列（现在是第1列）
            sort_key = lambda x: x['zh']
        elif self.confirmed_sort_column == 2:  # 置信度列（现在是第2列）
            sort_key = lambda x: x['confidence']
        
        if sort_key:
            # 执行排序
            reverse = (self.confirmed_sort_order == Qt.SortOrder.DescendingOrder)
            self.confirmed_list.sort(key=sort_key, reverse=reverse)
            
            # 重新填充表格
            self.refresh_confirmed_table()
            
            # 更新表头显示排序方向
            self.update_header_sort_indicator(self.confirmed_table, self.confirmed_sort_column, self.confirmed_sort_order)
    
    def update_header_sort_indicator(self, table, column, order):
        """更新表头排序指示器"""
        header = table.horizontalHeader()
        
        # 设置当前列的排序指示器
        if column < 3:  # 跳过选择列（现在是第3列）
            header.setSortIndicator(column, order)
            header.setSortIndicatorShown(True)
        else:
            header.setSortIndicatorShown(False)

    def select_all_pending(self):
        """全选待确认列表"""
        for row in range(self.pending_table.rowCount()):
            widget = self.pending_table.cellWidget(row, 3)
            if isinstance(widget, QCheckBox):
                widget.setChecked(True)

    def deselect_all_pending(self):
        """反选待确认列表"""
        for row in range(self.pending_table.rowCount()):
            widget = self.pending_table.cellWidget(row, 3)
            if isinstance(widget, QCheckBox):
                widget.setChecked(not widget.isChecked())

    def select_all_confirmed(self):
        """全选已确认列表"""
        for row in range(self.confirmed_table.rowCount()):
            widget = self.confirmed_table.cellWidget(row, 3)
            if isinstance(widget, QCheckBox):
                widget.setChecked(True)

    def deselect_all_confirmed(self):
        """反选已确认列表"""
        for row in range(self.confirmed_table.rowCount()):
            widget = self.confirmed_table.cellWidget(row, 3)
            if isinstance(widget, QCheckBox):
                widget.setChecked(not widget.isChecked())