# ui/highlight_util.py
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextDocument
from PySide6.QtCore import QRegularExpression, QTimer
from typing import List, Optional

from core.variable_protector import VariableProtector


class VariableHighlighter(QSyntaxHighlighter):
    """变量高亮器 - 使用淡黄色高亮所有变量"""

    # 常量定义
    MAX_TEXT_LENGTH = 10000  # 最大处理文本长度
    REHIGHLIGHT_DELAY = 50  # 重新高亮延迟（毫秒）

    def __init__(self, document: Optional[QTextDocument] = None, theme: str = "light"):
        """初始化高亮器"""
        super().__init__(document)
        self._theme = theme
        self._highlight_format = self._create_highlight_format(theme)
        self._init_highlighter()

    def _init_highlighter(self):
        """初始化高亮器组件"""
        # 获取编译好的正则表达式
        protector = VariableProtector()
        self._compiled_patterns = protector.get_pattern_string()

        # 初始化延迟重新高亮的计时器
        self._rehighlight_timer = QTimer()
        self._rehighlight_timer.setSingleShot(True)
        self._rehighlight_timer.setInterval(self.REHIGHLIGHT_DELAY)

    @staticmethod
    def _create_highlight_format(theme: str = "light") -> QTextCharFormat:
        """创建高亮格式"""
        highlight_format = QTextCharFormat()
        if theme == "dark":
            highlight_format.setBackground(QColor(194, 165, 0))  # 暗黄色背景
        else:
            highlight_format.setBackground(QColor(255, 255, 130))  # 淡黄色背景
        highlight_format.setFontWeight(QFont.Weight.Bold)
        return highlight_format
    
    def set_theme(self, theme: str):
        """设置主题并更新高亮格式"""
        self._theme = theme
        self._highlight_format = self._create_highlight_format(theme)
        self.rehighlight()

    def highlightBlock(self, text: str):
        """高亮文本块中的所有变量 - 优化版本"""
        # 空文本检查
        if not text:
            return

        # 长度限制检查
        if len(text) > self.MAX_TEXT_LENGTH:
            return

        try:
            self._apply_highlighting(text)
        except Exception:
            # 高亮失败不应影响正常功能
            pass

    def _apply_highlighting(self, text: str):
        """应用高亮逻辑"""
        if not self._compiled_patterns:
            return

        # 直接使用字符串创建 Qt 正则表达式
        pattern = QRegularExpression(self._compiled_patterns)

        if pattern.isValid():
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                if match.hasMatch():
                    self.setFormat(match.capturedStart(), match.capturedLength(), self._highlight_format)

    def set_patterns(self, patterns: List[QRegularExpression]):
        """设置新的正则表达式模式"""
        self._compiled_patterns = patterns
        self.delayed_rehighlight()

    def delayed_rehighlight(self):
        """延迟重新高亮，避免频繁重绘"""
        if self._rehighlight_timer.isActive():
            self._rehighlight_timer.stop()
        self._rehighlight_timer.start()

    def setDocument(self, document: Optional[QTextDocument]):
        """重写setDocument以重新设置计时器"""
        super().setDocument(document)

        # 如果文档被清除，停止计时器
        if not document and self._rehighlight_timer.isActive():
            self._rehighlight_timer.stop()

    def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self, '_rehighlight_timer') and self._rehighlight_timer is not None:
                if self._rehighlight_timer.isActive():
                    self._rehighlight_timer.stop()
        except RuntimeError:
            pass

    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            self.cleanup()
        except:
            pass