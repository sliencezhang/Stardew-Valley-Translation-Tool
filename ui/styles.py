# ui/styles.py
"""
统一的样式定义文件
"""
from pathlib import Path
from PySide6.QtGui import QIcon, QColor

# 图标资源路径
def get_icon_path():
    from core.config import get_resource_path
    return get_resource_path("resources/icons")

ICON_PATH = get_icon_path()


# ============================================
# 辅助函数
# ============================================
def _get_rgba_color(r, g, b, opacity):
    """生成rgba颜色字符串的辅助函数
    
    Args:
        r, g, b: RGB颜色值 (0-255)
        opacity: 透明度 (0-255)
    
    Returns:
        str: rgba颜色字符串，如 "rgba(255, 255, 255, 200)"
    """
    return f"rgba({r}, {g}, {b}, {opacity})"


class ColorPalette:
    """颜色调色板 - 统一管理所有颜色"""
    
    # ============================================
    # 透明度配置 - 统一管理所有控件的透明度
    # 数值范围: 0(完全透明) - 255(完全不透明)
    # ============================================
    class Opacity:
        """透明度配置 - 方便统一调整"""
        # 基础控件透明度
        GROUPBOX = 80           # 分组框背景
        TEXT_INPUT = 80        # 文本输入框、表格、列表
        TAB_WIDGET_PANE = 80   # 标签页面板
        TAB_WIDGET_TAB = 80    # 标签页标签
        TAB_SELECTED = 80      # 选中的标签
        TAB_HOVER = 80         # 悬停的标签
        
        # 表格相关
        TABLE_HEADER = 80      # 表头
        TABLE_SELECTION = 80   # 表格选中项
        
        # 特殊控件
        COMBOBOX = 80          # 下拉框
        COMBOBOX_VIEW = 200     # 下拉框弹出列表
        SPINBOX = 80           # 数字输入框
        PROGRESS_BAR_BG = 80   # 进度条背景
        
        # 说明文本和框架
        SETTINGS_DESC = 80      # 设置说明文本框
        MANUAL_FRAME = 80      # 人工翻译条目框架
        SCROLL_AREA = 80         # 滚动区域(完全透明)
        
        # 背景标签
        BG_LABEL_YELLOW = 80   # 黄色背景标签(警告)
        BG_LABEL_BLUE = 80     # 蓝色背景标签(信息)
        BG_LABEL_GRAY = 80     # 灰色背景标签(次要信息)
        
        # 步骤和其他
        STEP_CIRCLE = 80       # 步骤圆圈背景
        
        # 拖放框
        DRAGDROP_HOVER = 80    # 拖放框悬停背景
    
    # 浅色主题颜色
    class Light:
        # 主色调（蓝色系）
        PRIMARY, PRIMARY_HOVER, PRIMARY_PRESSED = "#4dabf7", "#339af0", "#1c7ed6"
        
        # 成功色（绿色系）
        SUCCESS, SUCCESS_HOVER, SUCCESS_PRESSED = "#51cf66", "#40c057", "#37b24d"
        
        # 危险色（红色系）
        DANGER, DANGER_HOVER = "#ff6b6b", "#ff5252"
        
        # 背景色
        BG_MAIN, BG_CARD, BG_INPUT = "#f8f9fa", "white", "white"
        BG_GRAY, BG_BLUE, BG_YELLOW = "#e9ecef", "#e7f5ff", "#fff9db"
        BG_GREEN_LIGHT, BG_TEXTEDIT = "#f0f9f0", "white"
        BG_NEW_TRANSLATION, BG_EDITED = "rgb(230, 245, 230)", "rgb(255, 228, 196)"
        
        # 文字色
        TEXT_PRIMARY, TEXT_GRAY = "#495057", "#868e96"
        TEXT_RED, TEXT_WARNING = "#fa5252", "#e8590c"
        
        # 边框色
        BORDER, BORDER_DASHED = "#dee2e6", "#adb5bd"
        BORDER_GREEN, BORDER_YELLOW = "#51cf66", "#ffd8a8"
        
        # 禁用状态
        DISABLED_BG, DISABLED_TEXT = "#adb5bd", "#868e96"
        
        # 表格色
        TABLE_GRID, TABLE_SELECTION = "#dee2e6", "#e7f5ff"
        TABLE_HEADER, TABLE_ALT_ROW = "#f8f9fa", "#f5f5f5"
        
        # 高亮色
        HIGHLIGHT = "rgb(255, 255, 130)"
        
        # 特殊组件颜色
        MANUAL_CHINESE_BORDER = "#74c0fc"  # 人工翻译-现有翻译框边框
        TAB_HOVER = "#f1f3f5"  # Tab悬停背景
        PROGRESS_CHUNK = "#43a047"  # 进度条填充色
        DISABLED_BTN = "#ccc"  # 禁用按钮背景
        DRAGDROP_HOVER_BORDER = "#7cb342"  # 拖放框悬停边框(绿色)
        DRAGDROP_HOVER_BG = "#e9f7e9"  # 拖放框悬停背景(绿色)
        VAR_ERROR_BG = "#fff5f5"  # 变量错误提示背景
        VAR_ERROR_BORDER = "#e53935"  # 变量错误提示边框
        VAR_RIGHT_TEXT = "#66bb6a"  # 变量正确提示文字
        VAR_RIGHT_BG = "#ebfbee"  # 变量正确提示背景
        VAR_RIGHT_BORDER = "#43a047"  # 变量正确提示边框
        SETTINGS_DESC_BG = "#f5f5f5"  # 设置说明背景
        SETTINGS_DESC_TEXT = "#666"  # 设置说明文字
        STOP_BTN_HOVER = "#e03131"  # 停止按钮悬停
        STEP_TEXT = "white"  # 步骤圆圈文字颜色
        
        # 拖放框渐变色（已选择文件-绿色系）
        DRAGDROP_GRADIENT_START = (56, 142, 60)  # 绿色起点
        DRAGDROP_GRADIENT_MID = (139, 195, 74)  # 浅绿中点
        DRAGDROP_GRADIENT_END = (27, 94, 32)  # 深绿终点
        
        # 拖放框渐变色（未选择-蓝色系）
        DRAGDROP_EMPTY_GRADIENT_START = (33, 150, 243)  # 蓝色起点
        DRAGDROP_EMPTY_GRADIENT_MID = (100, 181, 246)  # 浅蓝中点
        DRAGDROP_EMPTY_GRADIENT_END = (13, 71, 161)  # 深蓝终点
    
    # 深色主题颜色
    class Dark:
        # 主色调（蓝灰色系）
        PRIMARY, PRIMARY_HOVER, PRIMARY_PRESSED = "#455a64", "#546e7a", "#37474f"
        
        # 成功色（绿色系）
        SUCCESS, SUCCESS_HOVER, SUCCESS_PRESSED = "#558b2f", "#689f38", "#33691e"
        
        # 危险色（红色系）
        DANGER, DANGER_HOVER = "#c62828", "#d32f2f"
        
        # 背景色
        BG_MAIN, BG_CARD, BG_INPUT = "#1e1e1e", "#2b2b2b", "#1e1e1e"
        BG_GRAY, BG_BLUE, BG_YELLOW = "#424242", "#37474f", "#3e2723"
        BG_GREEN_DARK, BG_TEXTEDIT = "#33691e", "#2b2b2b"
        BG_NEW_TRANSLATION, BG_EDITED = "rgb(85, 139, 47)", "rgb(191, 87, 0)"
        
        # 文字色
        TEXT_PRIMARY, TEXT_GRAY = "#e0e0e0", "#9e9e9e"
        TEXT_RED, TEXT_WARNING = "#ef5350", "#ffb74d"
        
        # 边框色
        BORDER, BORDER_DASHED = "#424242", "#546e7a"
        BORDER_GREEN, BORDER_YELLOW = "#689f38", "#5d4037"
        
        # 禁用状态
        DISABLED_BG, DISABLED_TEXT = "#424242", "#757575"
        
        # 表格色
        TABLE_GRID, TABLE_SELECTION = "#424242", "#455a64"
        TABLE_HEADER, TABLE_ALT_ROW = "#37474f", "#2b2b2b"
        
        # 高亮色
        HIGHLIGHT = "rgb(194, 165, 0)"
        
        # 特殊组件颜色
        MANUAL_ENGLISH_BORDER = "#616161"  # 人工翻译-英文原文框边框
        MANUAL_CHINESE_BORDER = "#1e88e5"  # 人工翻译-现有翻译框边框
        MANUAL_NEW_BORDER = "#43a047"  # 人工翻译-新翻译框边框
        TAB_HOVER = "#455a64"  # Tab悬停背景(与PRIMARY相同)
        PROGRESS_CHUNK = "#43a047"  # 进度条填充色
        DRAGDROP_HOVER_BORDER = "#78909c"  # 拖放框悬停边框(灰色)
        VAR_ERROR_BG = "#3e2723"  # 变量错误提示背景
        VAR_ERROR_BORDER = "#e53935"  # 变量错误提示边框
        VAR_RIGHT_TEXT = "#66bb6a"  # 变量正确提示文字
        VAR_RIGHT_BG = "#1b5e20"  # 变量正确提示背景
        VAR_RIGHT_BORDER = "#43a047"  # 变量正确提示边框
        SETTINGS_DESC_BG = "#424242"  # 设置说明背景(与BG_GRAY相同)
        SETTINGS_DESC_TEXT = "#bdbdbd"  # 设置说明文字
        STOP_BTN = "#e53935"  # 停止按钮背景
        
        # 拖放框渐变色（已选择文件-绿色系）
        DRAGDROP_GRADIENT_START = (46, 125, 50)  # 绿色起点
        DRAGDROP_GRADIENT_MID = (102, 187, 106)  # 浅绿中点
        DRAGDROP_GRADIENT_END = (27, 94, 32)  # 深绿终点
        
        # 拖放框渐变色（未选择-蓝灰系）
        DRAGDROP_EMPTY_GRADIENT_START = (69, 90, 100)  # 蓝灰起点
        DRAGDROP_EMPTY_GRADIENT_MID = (120, 144, 156)  # 浅蓝灰中点
        DRAGDROP_EMPTY_GRADIENT_END = (55, 71, 79)  # 深蓝灰终点


class _BaseStylesClass:
    """基础样式类 - 统一的样式定义"""
    
    @staticmethod
    def get_button_style(theme="light", button_type="normal"):
        """生成按钮样式"""
        colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
        
        # 根据按钮类型选择颜色
        if button_type == "primary":
            bg, hover, pressed = colors.SUCCESS, colors.SUCCESS_HOVER, colors.SUCCESS_PRESSED
        elif button_type == "":
            bg, hover = colors.DANGER, colors.DANGER_HOVER
            pressed = hover
        else:  # normal
            bg, hover, pressed = colors.PRIMARY, colors.PRIMARY_HOVER, colors.PRIMARY_PRESSED
        
        text_color = colors.TEXT_PRIMARY if theme == "dark" else "white"
        
        return f"""
        QPushButton {{
            background-color: {bg};
            color: {text_color};
            border: none;
            border-radius: 6px;
            padding: 4px 10px;
            font-weight: bold;
            font-size: 12px;
            min-height: 20px;
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
        QPushButton:pressed {{
            background-color: {pressed};
        }}
        QPushButton:disabled {{
            background-color: {colors.DISABLED_BG};
            color: {colors.DISABLED_TEXT};
        }}
        """
    
    # 保持向后兼容的属性
    @property
    def BUTTON(self):
        return self.get_button_style("light", "normal")
    
    @property
    def BUTTON_DARK(self):
        return self.get_button_style("dark", "normal")
    
    @property
    def BUTTON_PRIMARY(self):
        return self.get_button_style("light", "primary")
    
    @property
    def BUTTON_PRIMARY_DARK(self):
        return self.get_button_style("dark", "primary")
    
    @property
    def BUTTON_DANGER(self):
        return self.get_button_style("light", "danger")
    
    @property
    def BUTTON_DANGER_DARK(self):
        return self.get_button_style("dark", "danger")
    
    @staticmethod
    def get_groupbox_style(theme="light"):
        """生成分组框样式"""
        colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
        border_color = colors.BORDER if theme == "dark" else colors.BG_GRAY
        
        # 使用统一配置的透明度
        opacity = ColorPalette.Opacity.GROUPBOX
        bg_color = _get_rgba_color(50, 50, 50, opacity) if theme == "dark" else _get_rgba_color(255, 255, 255, opacity)
        
        return f"""
        QGroupBox {{
            font-weight: bold;
            font-size: 13px;
            border: 2px solid {border_color};
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
            background-color: {bg_color};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            color: {colors.TEXT_PRIMARY};
        }}
        """
    
    @property
    def GROUPBOX(self):
        return self.get_groupbox_style("light")
    
    @property
    def GROUPBOX_DARK(self):
        return self.get_groupbox_style("dark")
    
    @staticmethod
    def get_tab_widget_style(theme="light"):
        """生成标签页样式"""
        colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
        color_style = f"color: {colors.TEXT_PRIMARY};" if theme == "dark" else ""
        
        # 使用统一配置的透明度
        opacity_pane = ColorPalette.Opacity.TAB_WIDGET_PANE
        opacity_tab = ColorPalette.Opacity.TAB_WIDGET_TAB
        opacity_selected = ColorPalette.Opacity.TAB_SELECTED
        opacity_hover = ColorPalette.Opacity.TAB_HOVER
        
        if theme == "dark":
            pane_bg = _get_rgba_color(40, 40, 40, opacity_pane)
            tab_bg = _get_rgba_color(60, 60, 60, opacity_tab)
            tab_selected_bg = _get_rgba_color(80, 80, 80, opacity_selected)
            tab_hover_bg = _get_rgba_color(84, 110, 122, opacity_hover)
        else:
            pane_bg = _get_rgba_color(255, 255, 255, opacity_pane)
            tab_bg = _get_rgba_color(230, 230, 230, opacity_tab)
            tab_selected_bg = _get_rgba_color(255, 255, 255, opacity_selected)
            tab_hover_bg = _get_rgba_color(241, 243, 245, opacity_hover)
        
        return f"""
        QTabWidget::pane {{
            border: 1px solid {colors.BORDER};
            border-radius: 6px;
            background-color: {pane_bg};
            min-height: 30px;
        }}
        QTabBar::tab {{
            background-color: {tab_bg};
            border: 1px solid {colors.BORDER};
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 12px 16px;
            margin-right: 2px;
            font-weight: 500;
            min-width: 80px;
            min-height: 20px;
            {color_style}
        }}
        QTabBar::tab:selected {{
            background-color: {tab_selected_bg};
            border-bottom: 1px solid {tab_selected_bg};
        }}
        QTabBar::tab:hover {{
            background-color: {tab_hover_bg};
        }}
        """
    
    @property
    def TAB_WIDGET(self):
        return self.get_tab_widget_style("light")
    
    @property
    def TAB_WIDGET_DARK(self):
        return self.get_tab_widget_style("dark")
    
    @staticmethod
    def get_text_input_style(theme="light"):
        """生成文本输入样式"""
        colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
        color_style = f"color: {colors.TEXT_PRIMARY};" if theme == "dark" else ""
        
        # 使用统一配置的透明度
        opacity_input = ColorPalette.Opacity.TEXT_INPUT
        opacity_header = ColorPalette.Opacity.TABLE_HEADER
        opacity_selection = ColorPalette.Opacity.TABLE_SELECTION
        
        input_bg = _get_rgba_color(40, 40, 40, opacity_input) if theme == "dark" else _get_rgba_color(255, 255, 255, opacity_input)
        header_bg = _get_rgba_color(55, 71, 79, opacity_header) if theme == "dark" else _get_rgba_color(248, 249, 250, opacity_header)
        selection_bg = _get_rgba_color(69, 90, 100, opacity_selection) if theme == "dark" else _get_rgba_color(231, 245, 255, opacity_selection)
        
        return f"""
        QTextEdit, QLineEdit, QTableWidget, QListWidget {{
            border: 1px solid {colors.BORDER};
            border-radius: 6px;
            background-color: {input_bg};
            {color_style}
            font-size: 12px;
        }}
        QTableWidget {{
            gridline-color: {colors.TABLE_GRID};
            selection-background-color: {selection_bg};
        }}
        QTableWidget::item {{
            padding: 5px;
        }}
        QListWidget {{
            background-color: {input_bg};
            color: {colors.TEXT_PRIMARY};
        }}
        QListWidget::item:selected {{
            background-color: {selection_bg};
            color: {colors.TEXT_PRIMARY};
        }}
        QHeaderView::section {{
            background-color: {header_bg};
            color: {colors.TEXT_PRIMARY};
            padding: 4px;
            border: 1px solid {colors.BORDER};
        }}
        QTableCornerButton::section {{
            background-color: {header_bg};
            border: 1px solid {colors.BORDER};
        }}
        """
    
    @property
    def TEXT_INPUT(self):
        return self.get_text_input_style("light")
    
    @property
    def TEXT_INPUT_DARK(self):
        return self.get_text_input_style("dark")
    
    @staticmethod
    def get_progress_bar_style(theme="light"):
        """生成进度条样式"""
        colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
        chunk_color = colors.PROGRESS_CHUNK if theme == "dark" else colors.SUCCESS_HOVER
        color_style = f"color: {colors.TEXT_PRIMARY};" if theme == "dark" else ""
        
        # 使用统一配置的透明度
        opacity = ColorPalette.Opacity.PROGRESS_BAR_BG
        bg_color = _get_rgba_color(30, 30, 30, opacity) if theme == "dark" else _get_rgba_color(233, 236, 239, opacity)
        
        return f"""
        QProgressBar {{
            border: 1px solid {colors.BORDER};
            border-radius: 4px;
            background-color: {bg_color};
            text-align: center;
            {color_style}
        }}
        QProgressBar::chunk {{
            background-color: {chunk_color};
            border-radius: 3px;
        }}
        """
    
    @property
    def PROGRESS_BAR(self):
        return self.get_progress_bar_style("light")
    
    @property
    def PROGRESS_BAR_DARK(self):
        return self.get_progress_bar_style("dark")
    
    PROGRESS_BAR_GRADIENT = f"""
        QProgressBar::chunk {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {ColorPalette.Light.SUCCESS}, stop:1 {ColorPalette.Light.PRIMARY});
            border-radius: 3px;
        }}
    """
    
    @staticmethod
    def get_label_style(theme="light", label_type="normal"):
        """生成标签样式"""
        colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
        
        if label_type == "gray":
            color = colors.TEXT_GRAY
            extra = ""
        elif label_type == "red":
            color = colors.TEXT_RED
            extra = "font-weight: bold;"
        else:  # normal
            color = colors.TEXT_PRIMARY
            extra = ""
        
        return f"""
        QLabel {{
            color: {color};
            font-size: 12px;
            {extra}
        }}
        """
    
    @property
    def LABEL(self):
        return self.get_label_style("light", "normal")
    
    @property
    def LABEL_DARK(self):
        return self.get_label_style("dark", "normal")
    
    @property
    def LABEL_GRAY(self):
        return self.get_label_style("light", "gray")
    
    @property
    def LABEL_GRAY_DARK(self):
        return self.get_label_style("dark", "gray")
    
    @property
    def LABEL_RED(self):
        return self.get_label_style("light", "red")
    
    @property
    def LABEL_RED_DARK(self):
        return self.get_label_style("dark", "red")
    
    @staticmethod
    def get_spinbox_style(theme="light"):
        """生成数字输入框样式"""
        colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
        color_style = f"color: {colors.TEXT_PRIMARY};" if theme == "dark" else ""
        
        # 使用统一配置的透明度
        opacity = ColorPalette.Opacity.SPINBOX
        bg_color = _get_rgba_color(40, 40, 40, opacity) if theme == "dark" else _get_rgba_color(255, 255, 255, opacity)
        
        return f"""
        QSpinBox {{
            border: 1px solid {colors.BORDER};
            border-radius: 4px;
            padding: 4px;
            background-color: {bg_color};
            {color_style}
            min-width: 60px;
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            width: 16px;
        }}
        """
    
    @property
    def SPINBOX(self):
        return self.get_spinbox_style("light")
    
    @property
    def SPINBOX_DARK(self):
        return self.get_spinbox_style("dark")
    
    @staticmethod
    def get_combobox_style(theme="light"):
        """生成下拉框样式"""
        colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
        color_style = f"color: {colors.TEXT_PRIMARY};" if theme == "dark" else ""
        
        # 使用统一配置的透明度
        opacity_combo = ColorPalette.Opacity.COMBOBOX
        opacity_view = ColorPalette.Opacity.COMBOBOX_VIEW
        opacity_selection = ColorPalette.Opacity.TAB_HOVER
        
        bg_color = _get_rgba_color(40, 40, 40, opacity_combo) if theme == "dark" else _get_rgba_color(255, 255, 255, opacity_combo)
        view_bg = _get_rgba_color(43, 43, 43, opacity_view) if theme == "dark" else _get_rgba_color(255, 255, 255, opacity_view)
        selection_bg = _get_rgba_color(69, 90, 100, opacity_selection) if theme == "dark" else _get_rgba_color(231, 245, 255, opacity_selection)
        
        return f"""
        QComboBox {{
            border: 1px solid {colors.BORDER};
            border-radius: 4px;
            padding: 4px;
            background-color: {bg_color};
            {color_style}
            min-width: 60px;
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {colors.BORDER};
            background-color: {view_bg};
            color: {colors.TEXT_PRIMARY};
            selection-background-color: {selection_bg};
        }}
        """
    
    @property
    def COMBOBOX(self):
        return self.get_combobox_style("light")
    
    @property
    def COMBOBOX_DARK(self):
        return self.get_combobox_style("dark")


# 创建BaseStyles实例供使用
BaseStyles = _BaseStylesClass()


def get_icon(icon_name):
    """获取图标"""
    icon_path = ICON_PATH / f"{icon_name}.ico"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()  # 返回空图标

def get_main_window_style(theme="light"):
    """主窗口样式"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    
    # 使用统一配置的透明度
    opacity = 80
    main_bg = _get_rgba_color(30, 30, 30, opacity) if theme == "dark" else _get_rgba_color(248, 249, 250, opacity)
    # 状态栏使用和BackgroundWidget遮罩层相同的颜色，保持视觉一致
    statusbar_bg = _get_rgba_color(0, 0, 0, 220) if theme == "dark" else _get_rgba_color(255, 255, 255, 230)
    messagebox_bg = _get_rgba_color(43, 43, 43, opacity) if theme == "dark" else _get_rgba_color(255, 255, 255, opacity)
    
    # 获取对应主题的基础样式
    if theme == "dark":
        base_styles = (BaseStyles.GROUPBOX_DARK + BaseStyles.BUTTON_DARK + BaseStyles.TEXT_INPUT_DARK + 
                      BaseStyles.PROGRESS_BAR_DARK + BaseStyles.TAB_WIDGET_DARK + BaseStyles.LABEL_DARK + 
                      BaseStyles.SPINBOX_DARK + BaseStyles.COMBOBOX_DARK)
    else:
        base_styles = (BaseStyles.GROUPBOX + BaseStyles.BUTTON + BaseStyles.TEXT_INPUT + 
                      BaseStyles.PROGRESS_BAR + BaseStyles.TAB_WIDGET + BaseStyles.LABEL + 
                      BaseStyles.SPINBOX + BaseStyles.COMBOBOX)
    
    return f"""
    QMainWindow {{
        background-color: transparent;
        font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
    }}
    QMainWindow > QWidget {{
        background-color: {main_bg};
        border: 1px solid {colors.BORDER};
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        border-bottom-left-radius: 0px;
        border-bottom-right-radius: 0px;
    }}
    QMainWindow QStatusBar {{
        background-color: {statusbar_bg} !important;
        color: {colors.TEXT_PRIMARY};
        font-size: 11px;
        border: 1px solid {colors.BORDER};
        border-top: none;
        margin-top: -1px;
        border-top-left-radius: 0px !important;
        border-top-right-radius: 0px !important;
        border-bottom-left-radius: 8px !important;
        border-bottom-right-radius: 8px !important;
    }}
    QStatusBar {{
        background-color: {statusbar_bg};
        color: {colors.TEXT_PRIMARY};
        font-size: 11px;
        border-top-left-radius: 0px;
        border-top-right-radius: 0px;
        border-bottom-left-radius: 8px;
        border-bottom-right-radius: 8px;
    }}
    QMessageBox {{
        background-color: {messagebox_bg};
        color: {colors.TEXT_PRIMARY};
    }}
    QMessageBox QLabel {{
        color: {colors.TEXT_PRIMARY};
    }}
    QMessageBox QPushButton {{
        min-width: 60px;
    }}
    """ + base_styles


def get_dialog_style(theme="light"):
    """对话框样式"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    
    # 使用统一配置的透明度
    opacity = 80
    dialog_bg = _get_rgba_color(58, 58, 58, opacity) if theme == "dark" else _get_rgba_color(248, 249, 250, opacity)
    
    # 获取对应主题的基础样式
    if theme == "dark":
        base_styles = BaseStyles.TAB_WIDGET_DARK + BaseStyles.GROUPBOX_DARK + BaseStyles.BUTTON_DARK + BaseStyles.TEXT_INPUT_DARK
    else:
        base_styles = BaseStyles.TAB_WIDGET + BaseStyles.GROUPBOX + BaseStyles.BUTTON + BaseStyles.TEXT_INPUT
    
    return f"""
    QDialog {{
        background-color: transparent;
        font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
    }}
    QDialog #dialogContainer {{
        background-color: {dialog_bg};
        border: 1px solid {colors.BORDER};
        border-radius: 8px;
    }}
    """ + base_styles

def get_drag_drop_style(theme="light"):
    """拖放组件样式"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    
    # 根据主题选择不同的背景和悬停颜色
    bg = colors.BG_CARD if theme == "dark" else colors.BG_MAIN
    hover_border = colors.DRAGDROP_HOVER_BORDER if theme == "dark" else colors.PRIMARY
    hover_bg = colors.PRIMARY_PRESSED if theme == "dark" else colors.BG_BLUE
    
    return f"""
    DragDropWidget {{
        border: 2px dashed {colors.BORDER_DASHED};
        border-radius: 8px;
        background-color: {bg};
    }}
    DragDropWidget:hover {{
        border-color: {hover_border};
        background-color: {hover_bg};
    }}
    DragDropWidget[dragOver="true"] {{
        border-color: {hover_border};
        background-color: {hover_bg};
    }}
    """

def get_background_yellow_style(theme="light"):
    """黄色背景标签样式（用于警告提示）"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    # 使用统一配置的透明度
    opacity = ColorPalette.Opacity.BG_LABEL_YELLOW
    bg_color = _get_rgba_color(62, 39, 35, opacity) if theme == "dark" else _get_rgba_color(255, 249, 219, opacity)
    return f"""
        QLabel {{
            font-weight: bold;
            color: {colors.TEXT_WARNING};
            background-color: {bg_color};
            padding: 6px 12px;
            border-radius: 4px;
            border: 1px solid {colors.BORDER_YELLOW};
            margin: 5px 0;
        }}
    """

def get_background_blue_style(theme="light"):
    """蓝色背景标签样式（用于信息提示）"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    # 使用统一配置的透明度
    opacity = ColorPalette.Opacity.BG_LABEL_BLUE
    bg_color = _get_rgba_color(55, 71, 79, opacity) if theme == "dark" else _get_rgba_color(231, 245, 255, opacity)
    return f"color: {colors.TEXT_PRIMARY}; font-size: 12px; background-color: {bg_color}; padding: 10px; border-radius: 6px; font-weight: 500;"

def get_step_style(theme="light"):
    """步骤圆圈样式 - 外层套圆圈"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    text_color = colors.TEXT_PRIMARY if theme == "dark" else colors.STEP_TEXT
    circle_color = colors.SUCCESS if theme == "dark" else colors.PRIMARY
    
    # 使用统一配置的透明度
    opacity = ColorPalette.Opacity.STEP_CIRCLE
    if theme == "dark":
        # 深色模式：绿色系加深
        fill_color = _get_rgba_color(13, 93, 61, opacity)
    else:
        # 浅色模式：蓝色系加深
        fill_color = _get_rgba_color(0, 86, 179, opacity)
    
    return f"""
        QLabel {{
            background-color: {fill_color};
            color: {text_color};
            border: 3px solid {circle_color};
            border-radius: 15px;
            font-weight: bold;
            font-size: 14px;
        }}
    """
def get_manual_english_style(theme="light"):
    """人工翻译-英文原文框样式"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    border_color = colors.MANUAL_ENGLISH_BORDER if theme == "dark" else colors.BORDER_DASHED
    return f"""
        QGroupBox {{ 
            border: 1px solid {border_color}; 
            border-radius: 4px; 
            padding-top: 10px;
            font-size: 12px;
        }}
    """

def get_manual_chinese_style(theme="light"):
    """人工翻译-现有翻译框样式"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    border_color = colors.MANUAL_CHINESE_BORDER
    return f"""
        QGroupBox {{
            border: 1px solid {border_color};
            border-radius: 4px;
            padding-top: 10px;
            font-size: 12px;
        }}
    """

def get_manual_new_chinese_style(theme="light"):
    """人工翻译-新翻译输入框样式"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    border_color = colors.MANUAL_NEW_BORDER if theme == "dark" else colors.BORDER_GREEN
    return f"""
        QGroupBox {{ 
            border: 1px solid {border_color}; 
            border-radius: 4px; 
            padding-top: 10px;
            font-size: 12px;
        }}
    """

def get_var_error_style(theme="light"):
    """变量不匹配错误提示样式"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    bg_color = colors.BG_YELLOW if theme == "dark" else colors.VAR_ERROR_BG
    border_color = colors.VAR_ERROR_BORDER if theme == "dark" else colors.DANGER
    return f"color: {colors.TEXT_RED}; font-size: 12px; font-weight: bold; background-color: {bg_color}; padding: 2px 8px; border-radius: 10px; border: 1px solid {border_color};"

def get_var_right_style(theme="light"):
    """变量匹配正确提示样式"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    return f"color: {colors.VAR_RIGHT_TEXT}; font-size: 12px; font-weight: bold; background-color: {colors.VAR_RIGHT_BG}; padding: 2px 8px; border-radius: 10px; border: 1px solid {colors.VAR_RIGHT_BORDER};"

def get_manual_basic_style(theme="light"):
    """人工翻译-条目框架样式"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    # 使用统一配置的透明度
    opacity = ColorPalette.Opacity.MANUAL_FRAME
    bg_color = _get_rgba_color(43, 43, 43, opacity) if theme == "dark" else _get_rgba_color(255, 255, 255, opacity)
    return f"""
        QFrame {{
            background-color: {bg_color};
            border: 1px solid {colors.BORDER};
            border-radius: 8px;
            padding: 12px;
        }}
    """


def get_progress_dialog_style(theme="light"):
    """进度对话框样式"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    
    # 使用统一配置的透明度
    opacity = 80
    dialog_bg = _get_rgba_color(30, 30, 30, opacity) if theme == "dark" else _get_rgba_color(248, 249, 250, opacity)
    titlebar_bg = _get_rgba_color(58, 58, 58, opacity) if theme == "dark" else _get_rgba_color(248, 249, 250, opacity)
    
    # 获取对应主题的基础样式
    if theme == "dark":
        base_styles = BaseStyles.GROUPBOX_DARK + BaseStyles.BUTTON_DARK + BaseStyles.PROGRESS_BAR_DARK + BaseStyles.TEXT_INPUT_DARK

    else:
        base_styles = BaseStyles.GROUPBOX + BaseStyles.BUTTON + BaseStyles.PROGRESS_BAR + BaseStyles.TEXT_INPUT

    return f"""
    QDialog {{
        background-color: transparent;
        font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    }}
    QDialog > QWidget {{
        background-color: {dialog_bg};
        border: 1px solid {colors.BORDER};
        border-radius: 8px;
    }}
    /* 确保标题栏也使用透明背景 */
    QDialog CustomTitleBar {{
        background-color: {titlebar_bg} !important;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }}
    """ + base_styles + BaseStyles.PROGRESS_BAR_GRADIENT

def get_settings_desc_style(theme="light"):
    """设置说明文本样式"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    # 使用统一配置的透明度
    opacity = ColorPalette.Opacity.SETTINGS_DESC
    bg_color = _get_rgba_color(66, 66, 66, opacity) if theme == "dark" else _get_rgba_color(245, 245, 245, opacity)
    text_color = colors.SETTINGS_DESC_TEXT
    return f"color: {text_color}; font-size: 12px; background-color: {bg_color}; padding: 10px; border-radius: 5px;"


def get_start_button_style(theme="light"):
    """开始按钮样式"""
    return BaseStyles.BUTTON_PRIMARY_DARK if theme == "dark" else BaseStyles.BUTTON_PRIMARY

def get_red_button_style(theme="light"):
    """红色危险按钮样式"""
    return BaseStyles.BUTTON_DANGER_DARK if theme == "dark" else BaseStyles.BUTTON_DANGER
def get_background_gray_style(theme="light"):
    """灰色背景标签样式（用于次要信息）"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    # 使用统一配置的透明度
    opacity = ColorPalette.Opacity.BG_LABEL_GRAY
    bg_color = _get_rgba_color(66, 66, 66, opacity) if theme == "dark" else _get_rgba_color(233, 236, 239, opacity)
    return f"color: {colors.TEXT_PRIMARY}; font-size: 11px; background-color: {bg_color}; padding: 6px; border-radius: 4px;"

def get_roll_button_style(theme="light"):
    """滚动按钮样式"""
    return BaseStyles.SPINBOX_DARK if theme == "dark" else BaseStyles.SPINBOX

def get_save_button_style(theme="light"):
    """保存按钮样式"""
    return BaseStyles.BUTTON_PRIMARY_DARK if theme == "dark" else BaseStyles.BUTTON_PRIMARY

def get_font_red_style(theme="light"):
    """红色文字样式"""
    return BaseStyles.LABEL_RED_DARK if theme == "dark" else BaseStyles.LABEL_RED

def get_font_gray_style(theme="light"):
    """灰色文字样式"""
    return BaseStyles.LABEL_GRAY_DARK if theme == "dark" else BaseStyles.LABEL_GRAY

def get_have_file_style(theme="light"):
    """拖放框-已选择文件样式（绿色）"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    border = colors.BORDER_GREEN if theme == "dark" else colors.SUCCESS
    bg = colors.BG_GREEN_DARK if theme == "dark" else colors.BG_GREEN_LIGHT
    hover_border = colors.DRAGDROP_HOVER_BORDER if theme == "dark" else colors.SUCCESS_HOVER
    hover_bg = colors.SUCCESS if theme == "dark" else colors.DRAGDROP_HOVER_BG
    return f"""DragDropWidget {{
                    border: 2px dashed {border};
                    border-radius: 8px;
                    background-color: {bg};
                }}
                DragDropWidget:hover {{
                    border-color: {hover_border};
                    background-color: {hover_bg};
                }}
            """

def get_no_file_style(theme="light"):
    """拖放框-未选择文件样式（灰色）"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    bg = colors.BG_CARD if theme == "dark" else colors.BG_MAIN
    hover_border = colors.DRAGDROP_HOVER_BORDER if theme == "dark" else colors.PRIMARY
    hover_bg = colors.PRIMARY_PRESSED if theme == "dark" else colors.BG_BLUE
    return f"""DragDropWidget {{
                    border: 2px dashed {colors.BORDER_DASHED};
                    border-radius: 8px;
                    background-color: {bg};
                }}
                DragDropWidget:hover {{
                    border-color: {hover_border};
                    background-color: {hover_bg};
                }}
            """
def get_big_icon_style():
    """大图标样式"""
    return "font-size: 24px;"

def get_scroll_area_style(theme="light"):
    """滚动区域样式"""
    # 使用透明背景以显示背景图片
    return "QScrollArea { background-color: transparent; border: none; }"

def get_widget_background_style(theme="light"):
    """Widget背景样式"""
    # 使用透明背景以显示背景图片
    return "QWidget { background-color: transparent; }"

def get_new_translation_bg_color(theme="light"):
    """新翻译单元格背景色"""
    if theme == "dark":
        return QColor(85, 139, 47)
    else:
        return QColor(230, 245, 230)

def get_table_edit_button_style(theme="light"):
    """表格内编辑按钮样式"""
    return """
        QPushButton {
            padding: 2px 6px;
            font-size: 12px;
        }
    """

def get_edited_translation_bg_color(theme="light"):
    """编辑后翻译单元格背景色"""
    if theme == "dark":
        return QColor(191, 87, 0)  # 深橙色
    else:
        return QColor(255, 228, 196)  # 浅橙色

def get_edit_dialog_textedit_style(theme="light"):
    """编辑对话框文本框样式"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    # 使用统一配置的透明度
    opacity = ColorPalette.Opacity.TEXT_INPUT
    bg_color = _get_rgba_color(43, 43, 43, opacity) if theme == "dark" else _get_rgba_color(255, 255, 255, opacity)
    return f"""
        QTextEdit {{
            background-color: {bg_color};
            color: {colors.TEXT_PRIMARY};
            border: 1px solid {colors.BORDER};
            border-radius: 4px;
            padding: 4px;
        }}
    """

def get_log_text_style(theme="light"):
    """操作日志样式"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    # 使用统一配置的透明度
    opacity = ColorPalette.Opacity.TEXT_INPUT
    bg_color = _get_rgba_color(43, 43, 43, opacity) if theme == "dark" else _get_rgba_color(255, 255, 255, opacity)
    return f"""
        QTextEdit {{
            background-color: {bg_color};
            color: {colors.TEXT_PRIMARY};
            border: 1px solid {colors.BORDER};
            border-radius: 6px;
            padding: 8px;
        }}
    """

def get_dragdrop_gradient_colors(theme="light", has_files=False):
    """获取拖放框渐变色 - 返回(起点, 中点, 终点)元组"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    
    if has_files:
        return (colors.DRAGDROP_GRADIENT_START, 
                colors.DRAGDROP_GRADIENT_MID, 
                colors.DRAGDROP_GRADIENT_END)
    else:
        return (colors.DRAGDROP_EMPTY_GRADIENT_START, 
                colors.DRAGDROP_EMPTY_GRADIENT_MID, 
                colors.DRAGDROP_EMPTY_GRADIENT_END)

def apply_table_header_style(table_widget, theme="light"):
    """应用表头样式 - 小字体、低高度、隐藏序号列"""
    colors = ColorPalette.Dark if theme == "dark" else ColorPalette.Light
    
    # 使用统一配置的透明度
    opacity = ColorPalette.Opacity.TABLE_HEADER
    bg_color = _get_rgba_color(55, 71, 79, opacity) if theme == "dark" else _get_rgba_color(248, 249, 250, opacity)
    
    # 隐藏垂直表头（序号列）
    table_widget.verticalHeader().setVisible(False)
    
    # 设置水平表头样式
    header = table_widget.horizontalHeader()
    header.setStyleSheet(f"""
        QHeaderView::section {{
            background-color: {bg_color};
            color: {colors.TEXT_PRIMARY};
            padding: 4px;
            border: 1px solid {colors.BORDER};
            font-size: 11px;
            font-weight: bold;
            height: 28px;
        }}
    """)
    header.setMinimumHeight(28)
    header.setMaximumHeight(28)