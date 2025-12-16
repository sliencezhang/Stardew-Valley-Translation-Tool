# ui/tabs/tab_manifest.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                               QLabel, QGroupBox)

from ui.custom_message_box import CustomMessageBox
from core.config import config
from core.signal_bus import signal_bus
from ui.styles import get_start_button_style, get_settings_desc_style, get_background_gray_style
from ui.widgets import DragDropWidget


class TabManifest(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_manager = None
        self.dropped_folders = []  # 存储拖放的文件夹路径（英文）
        self.dropped_zh_folders = []  # 存储拖放的文件夹路径（中文）
        self.init_ui()

    def set_project_manager(self, project_manager):
        """设置项目管理器"""
        self.project_manager = project_manager

    def init_ui(self):
        layout = QVBoxLayout()

        # 使用说明
        help_text = QLabel(
            "使用说明：\n"
            "1. 此tab更多的是用于 mod 更新时恢复已翻译的名字和介绍\n"
            "2. 将原 mod 文件夹拖入步骤2，新下载的 mod 文件夹拖入步骤1 即可恢复翻译\n"
            "3. 恢复翻译的manifest文件在项目文件夹的manifest同mod文件夹内\n"
            "4. 多 mod 文件夹需保持 en 与 zh 的 mod 文件夹名字一一对应，单 mod 文件夹不需要一致\n"
            "5. 也可拖入大量 mod 文件夹到步骤1，统一由AI翻译，但是会缺少诸如[前置][美化]这样的自定义标签"
        )
        help_text.setStyleSheet(get_settings_desc_style(config.theme))
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # 步骤1: 拖放英文文件夹
        step1_group = QGroupBox("步骤1: 拖放英文 mod 文件夹")
        step1_layout = QVBoxLayout(step1_group)
        self.manifest_widget = DragDropWidget(
            "拖放包含英文 manifest.json 的 mod 文件夹到这里（可多选）",
            accept_folders=True,
            accept_files=False,
            multi_select=True
        )
        self.manifest_widget.sender_id = 'manifest_en'
        signal_bus.foldersDropped.connect(self.on_folders_dropped)
        step1_layout.addWidget(self.manifest_widget)
        
        # 显示已选择的英文文件夹
        self.selected_en_folders_label = QLabel("已选择: 0 个mod文件夹")
        self.selected_en_folders_label.setStyleSheet(get_background_gray_style(config.theme))
        step1_layout.addWidget(self.selected_en_folders_label)
        
        layout.addWidget(step1_group)

        # 步骤2: 拖放中文文件夹（增量翻译用）
        step2_group = QGroupBox("步骤2: 拖放中文 mod 文件夹（增量翻译用）")
        step2_layout = QVBoxLayout(step2_group)
        self.manifest_zh_widget = DragDropWidget(
            "拖放包含中文 manifest.json 的 mod 文件夹到这里（可多选，可选）",
            accept_folders=True,
            accept_files=False,
            multi_select=True
        )
        self.manifest_zh_widget.sender_id = 'manifest_zh'
        signal_bus.foldersDropped.connect(self.on_folders_dropped)
        step2_layout.addWidget(self.manifest_zh_widget)
        
        # 显示已选择的中文文件夹
        self.selected_zh_folders_label = QLabel("已选择: 0 个mod文件夹")
        self.selected_zh_folders_label.setStyleSheet(get_background_gray_style(config.theme))
        step2_layout.addWidget(self.selected_zh_folders_label)
        
        layout.addWidget(step2_group)

        # 步骤3: 开始翻译
        step3_group = QGroupBox("步骤3: 开始翻译")
        step3_layout = QVBoxLayout(step3_group)

        # 翻译按钮（自动判断增量或AI）
        self.manifest_translate_btn = QPushButton("🤖 开始翻译Manifest")
        self.manifest_translate_btn.clicked.connect(self.start_manifest_translation)
        self.manifest_translate_btn.setStyleSheet(get_start_button_style(config.theme))
        step3_layout.addWidget(self.manifest_translate_btn)

        layout.addWidget(step3_group)

        layout.addStretch()
        self.setLayout(layout)

    def on_folders_dropped(self, paths, sender_id=None):
        """处理文件夹拖放 - 只记录路径，不自动开始翻译"""
        
        if sender_id == 'manifest_en':
            # 英文文件夹
            if paths:
                self.dropped_folders = paths
                self.selected_en_folders_label.setText(f"已选择: {len(paths)} 个mod文件夹")
                
                # 显示前几个文件夹路径
                preview_text = "已选择的英文文件夹:\n"
                for i, path in enumerate(paths[:3]):
                    folder_name = os.path.basename(path)
                    preview_text += f"  {i + 1}. {folder_name}\n"
                if len(paths) > 3:
                    preview_text += f"  ... 还有 {len(paths) - 3} 个文件夹"
                
                self.selected_en_folders_label.setToolTip(preview_text)
                signal_bus.log_message.emit("INFO", f"已选择 {len(paths)} 个英文文件夹", {})
                    
        elif sender_id == 'manifest_zh':
            # 中文文件夹
            if paths:
                self.dropped_zh_folders = paths
                self.selected_zh_folders_label.setText(f"已选择: {len(paths)} 个mod文件夹")
                
                # 显示前几个文件夹路径
                preview_text = "已选择的中文文件夹:\n"
                for i, path in enumerate(paths[:3]):
                    folder_name = os.path.basename(path)
                    preview_text += f"  {i + 1}. {folder_name}\n"
                if len(paths) > 3:
                    preview_text += f"  ... 还有 {len(paths) - 3} 个文件夹"
                
                self.selected_zh_folders_label.setToolTip(preview_text)
                signal_bus.log_message.emit("INFO", f"已选择 {len(paths)} 个中文文件夹", {})


    def start_manifest_translation(self):
        """开始Manifest翻译 - 自动判断增量或AI翻译"""
        # 检查1: 是否有当前项目
        if not self.project_manager or not self.project_manager.current_project:
            CustomMessageBox.warning(self, "提示", "请先打开或创建一个项目")
            return
        
        # 检查2: 是否选择了文件夹
        if not self.dropped_folders:
            CustomMessageBox.warning(self, "提示", "请先拖放英文mod文件夹到步骤1中")
            return
        
        # 判断是增量翻译还是AI翻译
        if self.dropped_zh_folders:
            # 有中文文件夹，使用增量翻译
            params = {
                '英文文件夹': self.dropped_folders,
                '中文文件夹': self.dropped_zh_folders,
                '项目路径': self.project_manager.current_project.path
            }
            signal_bus.log_message.emit("INFO", f"开始增量翻译 {len(self.dropped_folders)} 个Manifest文件", {})
            signal_bus.manifest_incremental_request.emit(params)
        else:
            # 检查3: 是否配置了API密钥（AI翻译需要，本地API除外）
            if config.api_provider != "local" and not config.api_key:
                reply = CustomMessageBox.question(
                    self,
                    "需要配置API密钥",
                    "检测到未配置API密钥，无法进行AI翻译。\n\n是否前往全局设置配置API密钥？"
                )
                if reply == CustomMessageBox.Yes:
                    # 打开全局设置
                    from ui.main_window import GlobalSettingsDialog
                    dialog = GlobalSettingsDialog(self)
                    dialog.set_project_manager(self.project_manager)
                    dialog.exec()
                return
            
            # 没有中文文件夹，使用AI翻译
            params = {
                '文件夹路径': self.dropped_folders,
                '项目路径': self.project_manager.current_project.path
            }
            signal_bus.log_message.emit("INFO", f"开始AI翻译 {len(self.dropped_folders)} 个Manifest文件", {})
            signal_bus.manifest_translate_request.emit(params)