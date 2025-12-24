# ui/widgets.py
import os
from pathlib import Path
from typing import Optional, Dict

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QDialog, QLineEdit, QFileDialog, QDialogButtonBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QPen, QColor, QLinearGradient, QPixmap, QBrush, QPainterPath

from core.config import config
from core.signal_bus import signal_bus
from ui.styles import (get_dialog_style, get_drag_drop_style, get_red_button_style, get_background_gray_style,
    get_font_gray_style, get_have_file_style, get_no_file_style, get_big_icon_style, get_dragdrop_gradient_colors)


def load_background_image(theme="light"):
    """加载背景图片的辅助函数"""
    try:
        if not config.use_background:
            return None
        
        custom_path = config.custom_background_light if theme == "light" else config.custom_background_dark
        if custom_path and os.path.exists(custom_path):
            return QPixmap(custom_path)
        
        if theme == "dark":
            image_name = "background-dark.png"
        else:
            image_name = "background-night.png"
        
        image_path = Path(__file__).parent.parent / "resources" / "img" / image_name
        
        if image_path.exists():
            return QPixmap(str(image_path))
        else:
            signal_bus.log_message.emit("WARNING", f"背景图片不存在: {image_path}", {})
            return None
    except Exception as e:
        signal_bus.log_message.emit("ERROR", f"加载背景图片失败: {str(e)}", {})
        return None


class BackgroundWidget(QWidget):
    """带背景图片的Widget"""
    
    def __init__(self, pixmap=None, theme="light", parent=None):
        super().__init__(parent)
        self.background_pixmap = pixmap
        self.theme = theme
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    
    def set_background(self, pixmap, theme):
        """设置背景图片和主题"""
        self.background_pixmap = pixmap
        self.theme = theme
        self.update()
    
    def paintEvent(self, event):
        """绘制背景图片"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 获取widget尺寸
        widget_rect = self.rect()
        
        # 创建圆角裁剪路径
        path = QPainterPath()
        path.addRoundedRect(widget_rect.x(), widget_rect.y(), widget_rect.width(), widget_rect.height(), 8, 8)
        painter.setClipPath(path)
        
        if self.background_pixmap:
            # 缩放背景图片以适应widget大小
            scaled_pixmap = self.background_pixmap.scaled(
                widget_rect.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # 计算居中位置
            x = (widget_rect.width() - scaled_pixmap.width()) // 2
            y = (widget_rect.height() - scaled_pixmap.height()) // 2
            
            # 绘制背景图片
            painter.drawPixmap(x, y, scaled_pixmap)
            
            # 绘制半透明遮罩以保证文字可读性（增加不透明度）
            overlay_color = QColor(0, 0, 0, 220) if self.theme == "dark" else QColor(255, 255, 255, 180)
            painter.fillRect(widget_rect, QBrush(overlay_color))
        else:
            # 没有背景图片时使用纯色背景
            bg_color = QColor(30, 30, 30) if self.theme == "dark" else QColor(248, 249, 250)
            painter.fillRect(widget_rect, QBrush(bg_color))


class ProjectDialog(QDialog):
    """项目创建对话框"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setWindowTitle("创建新项目")
        self.setModal(True)
        self.setFixedSize(450, 220)
        self.setStyleSheet(get_dialog_style(config.theme))
        
        # 设置无边框窗口和透明背景以实现圆角
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 加载背景图片
        self.background_pixmap = load_background_image(config.theme)

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
        content_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.addWidget(content_widget)

        # 项目名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("项目名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入项目名称...")
        name_layout.addWidget(self.name_edit)
        content_layout.addLayout(name_layout)

        # 项目路径
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("项目路径:"))
        self.path_edit = QLineEdit()
        # 设置默认路径为软件所在目录
        from pathlib import Path
        
        try:
            # 使用统一的路径工具模块
            from core.path_utils import get_application_directory
            default_path = get_application_directory()
        except ImportError:
            # 如果路径工具不可用，使用回退方案
            import sys
            if getattr(sys, 'frozen', False):
                default_path = Path(sys.executable).parent
            else:
                default_path = Path(__file__).parent.parent
        
        self.path_edit.setText(str(default_path))
        self.path_edit.setPlaceholderText("选择项目保存位置...")
        path_layout.addWidget(self.path_edit)
        self.path_btn = QPushButton("浏览")
        self.path_btn.clicked.connect(self._select_path)
        path_layout.addWidget(self.path_btn)
        content_layout.addLayout(path_layout)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        ok_btn.setText("确认")
        cancel_btn.setText("取消")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        content_layout.addWidget(button_box)

        self.setLayout(main_layout)

    def _select_path(self):
        """选择项目路径"""
        if path := QFileDialog.getExistingDirectory(self, "选择项目路径"):
            self.path_edit.setText(str(Path(path)))

    def get_project_info(self) -> Dict[str, str]:
        """获取项目信息"""
        return {
            'name': self.name_edit.text().strip(),
            'path': self.path_edit.text().strip()
        }


class DragDropWidget(QWidget):
    def __init__(self, text, accept_folders=False, accept_files=True, multi_select=False):
        super().__init__()
        self.accept_folders = accept_folders
        self.accept_files = accept_files
        self.multi_select = multi_select
        self.file_paths = []
        self.allowed_extensions = ['.json']
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self.setStyleSheet(get_drag_drop_style(config.theme))

        # 防止递归绘制
        self._is_painting = False

        layout = QVBoxLayout()

        # 图标和文字
        icon_label = QLabel("📁")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(get_big_icon_style())

        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(get_font_gray_style(config.theme))

        self.path_label = QLabel("未选择文件")
        self.path_label.setStyleSheet(get_background_gray_style(config.theme))
        self.path_label.setWordWrap(True)
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 添加清除按钮
        btn_layout = QHBoxLayout()
        self.clear_btn = QPushButton("清除选择")
        self.clear_btn.clicked.connect(self.clear_selection)
        self.clear_btn.setVisible(False)
        self.clear_btn.setStyleSheet(get_red_button_style(config.theme))
        btn_layout.addStretch()
        btn_layout.addWidget(self.clear_btn)

        layout.addStretch()
        layout.addWidget(icon_label)
        layout.addWidget(self.label)
        layout.addWidget(self.path_label)
        layout.addLayout(btn_layout)  # 添加按钮布局
        layout.addStretch()

        self.setLayout(layout)

    def paintEvent(self, event):
        """重写绘制事件 - 使用渐变色虚线边框"""
        if self._is_painting:
            return

        self._is_painting = True
        try:
            # 调用父类的 paintEvent
            super().paintEvent(event)

            # 绘制边框
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # 获取渐变色配置
            start_rgb, mid_rgb, end_rgb = get_dragdrop_gradient_colors(config.theme, bool(self.file_paths))
            
            # 创建对角线渐变（左上到右下）
            gradient = QLinearGradient(0, 0, self.width(), self.height())
            gradient.setColorAt(0, QColor(*start_rgb))
            gradient.setColorAt(0.5, QColor(*mid_rgb))
            gradient.setColorAt(1, QColor(*end_rgb))
            
            # 使用渐变色创建画笔，增加线宽使渐变更明显
            pen = QPen(gradient, 3, Qt.PenStyle.DashLine)
            painter.setPen(pen)

            # 绘制圆角矩形
            painter.drawRoundedRect(2, 2, self.width() - 4, self.height() - 4, 6, 6)
        finally:
            self._is_painting = False

    def _update_style(self):
        """更新样式"""
        self.setStyleSheet(get_have_file_style(config.theme) if self.file_paths else get_no_file_style(config.theme))
        self.path_label.setStyleSheet(get_background_gray_style(config.theme))
        self.label.setStyleSheet(get_font_gray_style(config.theme))
        self.clear_btn.setStyleSheet(get_red_button_style(config.theme))

    def clear_selection(self):
        """清除选择"""
        self.file_paths = []
        self.path_label.setText("未选择文件")
        self.clear_btn.setVisible(False)
        self._update_style()
        # 安全地请求重绘
        QTimer.singleShot(0, self.update)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if not files:
            return

        # 文件筛选（带后缀检查）
        valid_files = [p for p in files if os.path.isfile(p) and self.accept_files
                       and (not self.allowed_extensions or os.path.splitext(p)[1].lower() in self.allowed_extensions)]

        # 文件夹筛选（无后缀检查）
        valid_folders = [p for p in files if os.path.isdir(p) and self.accept_folders]

        # 处理结果
        if valid_files:
            self.set_paths([valid_files[0]] if not self.multi_select and len(valid_files) > 1 else valid_files)
            # 发送信号时带上来源标识
            signal_bus.filesDropped.emit(valid_files, self.sender_id if hasattr(self, 'sender_id') else None)

        if valid_folders:
            self.set_paths([valid_folders[0]] if not self.multi_select and len(valid_folders) > 1 else valid_folders)
            # 发送信号时带上来源标识
            signal_bus.foldersDropped.emit(valid_folders, self.sender_id if hasattr(self, 'sender_id') else None)

    def set_paths(self, paths):
        self.file_paths = paths
        self.path_label.setText((paths[0][-47:].rjust(50, "…") if len(paths[0]) > 50 else paths[0]) if len(
            paths) == 1 else f"已选择 {len(paths)} 个文件/文件夹")
        self.clear_btn.setVisible(True)
        self._update_style()
        QTimer.singleShot(0, self.update)
