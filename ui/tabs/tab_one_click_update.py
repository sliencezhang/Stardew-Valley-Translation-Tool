# ui/tabs/tab_one_click_update.py
from pathlib import Path
import shutil
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox, QLabel)

from core.config import config
from core.signal_bus import signal_bus
from core.file_tool import file_tool
from ui.styles import get_start_button_style
from ui.widgets import DragDropWidget


class TabOneClickUpdate(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_manager = None
        self.en_mod_paths = []
        self.zh_mod_paths = []
        self.init_ui()

    def set_project_manager(self, project_manager):
        """设置项目管理器"""
        self.project_manager = project_manager

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 步骤1: 拖放英文mod文件夹
        step1_group = QGroupBox("步骤1: 拖放英文mod文件夹")
        step1_layout = QVBoxLayout(step1_group)
        
        # 说明文字
        step1_info = QLabel("请将英文mod文件夹拖放到下方区域")
        step1_info.setWordWrap(True)
        step1_layout.addWidget(step1_info)
        
        # 拖放区域
        self.en_mod_widget = DragDropWidget(
            "拖放英文mod文件夹到这里（支持多个）",
            accept_folders=True,
            accept_files=False,
            multi_select=True
        )
        # 设置标识
        self.en_mod_widget.sender_id = 'en_mod'
        signal_bus.foldersDropped.connect(self.on_folders_dropped)
        step1_layout.addWidget(self.en_mod_widget)
        
        # 状态显示
        self.en_status_label = QLabel("状态: 未选择文件夹")
        self.en_status_label.setStyleSheet("color: #666;")
        step1_layout.addWidget(self.en_status_label)
        
        layout.addWidget(step1_group)

        # 步骤2: 拖放中文mod文件夹
        step2_group = QGroupBox("步骤2: 拖放中文mod文件夹")
        step2_layout = QVBoxLayout(step2_group)
        
        # 说明文字
        step2_info = QLabel("请将中文mod文件夹拖放到下方区域")
        step2_info.setWordWrap(True)
        step2_layout.addWidget(step2_info)
        
        # 拖放区域
        self.zh_mod_widget = DragDropWidget(
            "拖放中文mod文件夹到这里（支持多个）",
            accept_folders=True,
            accept_files=False,
            multi_select=True
        )
        # 设置标识
        self.zh_mod_widget.sender_id = 'zh_mod'
        signal_bus.foldersDropped.connect(self.on_folders_dropped)
        step2_layout.addWidget(self.zh_mod_widget)
        
        # 状态显示
        self.zh_status_label = QLabel("状态: 未选择文件夹")
        self.zh_status_label.setStyleSheet("color: #666;")
        step2_layout.addWidget(self.zh_status_label)
        
        layout.addWidget(step2_group)

        # 一键更新按钮
        update_group = QGroupBox("步骤3: 执行更新")
        update_layout = QVBoxLayout(update_group)
        
        # 跳过人名地名检测选项
        from PySide6.QtWidgets import QCheckBox
        self.skip_name_detection_checkbox = QCheckBox("跳过人名地名检测步骤")
        self.skip_name_detection_checkbox.setChecked(False)
        update_layout.addWidget(self.skip_name_detection_checkbox)
        
        self.update_btn = QPushButton("🔄 一键更新")
        self.update_btn.clicked.connect(self.start_one_click_update)
        self.update_btn.setStyleSheet(get_start_button_style(config.theme))
        self.update_btn.setEnabled(False)  # 初始禁用，需要两个文件夹都选择
        update_layout.addWidget(self.update_btn)
        
        layout.addWidget(update_group)

        # 添加弹性空间
        layout.addStretch()

        self.setLayout(layout)

    def on_folders_dropped(self, paths, sender_id):
        """处理文件夹拖放"""
        if sender_id == 'en_mod':
            if paths:
                self.en_mod_paths = paths
                if len(paths) == 1:
                    folder_name = Path(paths[0]).name
                    self.en_status_label.setText(f"状态: 已选择 {folder_name}")
                else:
                    self.en_status_label.setText(f"状态: 已选择 {len(paths)} 个文件夹")
                self.en_status_label.setStyleSheet("color: #2e7d32;")
        elif sender_id == 'zh_mod':
            if paths:
                self.zh_mod_paths = paths
                if len(paths) == 1:
                    folder_name = Path(paths[0]).name
                    self.zh_status_label.setText(f"状态: 已选择 {folder_name}")
                else:
                    self.zh_status_label.setText(f"状态: 已选择 {len(paths)} 个文件夹")
                self.zh_status_label.setStyleSheet("color: #2e7d32;")
        
        # 检查是否可以启用更新按钮
        if self.en_mod_paths and self.zh_mod_paths:
            self.update_btn.setEnabled(True)
        else:
            self.update_btn.setEnabled(False)

    def start_one_click_update(self):
        """开始一键更新"""
        if not self.en_mod_paths or not self.zh_mod_paths:
            signal_bus.log_message.emit("ERROR", "请先选择英文和中文mod文件夹", {})
            return
        
        if not self.project_manager or not self.project_manager.current_project:
            signal_bus.log_message.emit("ERROR", "请先创建或打开项目", {})
            return

        # 准备参数
        params = {
            '英文mod路径': self.en_mod_paths,
            '中文mod路径': self.zh_mod_paths,
            '跳过人名检测': self.skip_name_detection_checkbox.isChecked()
        }

        # 发送信号执行核心逻辑
        signal_bus.startOneClickUpdate.emit(params)