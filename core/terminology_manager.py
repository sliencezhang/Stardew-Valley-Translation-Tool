# core/terminology_manager.py
from pathlib import Path
from typing import Dict, List
from PySide6.QtCore import QObject

from core.file_tool import file_tool
from core.signal_bus import signal_bus

# 新增导入
import ahocorasick


class TerminologyManager(QObject):
    """术语表管理器 - 负责术语管理和提示词构建"""

    def __init__(self, prompt: str = None, parent=None):
        super().__init__(parent)
        self.terminology: Dict[str, str] = {}
        self.default_prompt = self.get_default_prompt(prompt)
        # 新增：Aho-Corasick自动机
        self._automaton = None
        self._automaton_dirty = True  # 标记自动机是否需要重建

    @staticmethod
    def get_default_prompt(prompt: str) -> Dict:
        """获取默认提示词"""
        current_dir = Path(__file__).parent
        file_path = current_dir / "../resources/default_prompts.json"
        file_path = file_path.resolve()
        return file_tool.read_json_file(str(file_path)).get(prompt)

    @staticmethod
    def save_default_prompt(prompt_data: Dict) -> None:
        current_dir = Path(__file__).parent
        file_path = current_dir / "../resources/default_prompts.json"
        file_path = file_path.resolve()
        return file_tool.save_json_file(prompt_data, str(file_path))

    def _build_automaton_if_needed(self):
        """如果需要，构建Aho-Corasick自动机"""
        if not self.terminology:
            self._automaton = None
            self._automaton_dirty = False
            return

        if self._automaton_dirty or self._automaton is None:
            try:
                automaton = ahocorasick.Automaton()
                for en_term, zh_term in self.terminology.items():
                    automaton.add_word(en_term, (en_term, zh_term))
                automaton.make_automaton()
                self._automaton = automaton
                self._automaton_dirty = False
            except Exception:
                # 如果构建失败，保持None，回退到原始方法
                self._automaton = None
                self._automaton_dirty = False

    def get_terms_in_text(self, text: str) -> Dict[str, str]:
        """获取文本中出现的术语（使用Aho-Corasick优化）

        Args:
            text: 要检查的文本

        Returns:
            Dict[str, str]: 找到的术语字典 {英文: 中文}
        """
        found_terms = {}

        if not text or not self.terminology:
            return found_terms

        # 尝试使用Aho-Corasick
        self._build_automaton_if_needed()

        if self._automaton:
            # 使用Aho-Corasick自动机高效查找
            for end_index, (en_term, zh_term) in self._automaton.iter(text):
                found_terms[en_term] = zh_term
        else:
            # 回退到原始方法
            for term_en, term_zh in self.terminology.items():
                if term_en and term_en in text:
                    found_terms[term_en] = term_zh

        return found_terms

    def build_translation_prompt(self, text_values: List[str]) -> str:
        """构建翻译提示词

        Args:
            text_values: 待翻译的文本列表

        Returns:
            str: 构建好的提示词
        """
        # 提取所有文本中的术语
        all_text = " ".join(text_values)
        found_terms = self.get_terms_in_text(all_text)

        # 构建术语表部分
        terminology_section = self._build_terminology_section(found_terms)

        # 构建内容部分
        content_section = self._build_content_section(text_values)

        # 构建完整提示词
        full_prompt = f"{self.default_prompt}\n{terminology_section}\n{content_section}"

        # 发送信号
        signal_bus.prompt_built.emit(
            len(full_prompt),  # 提示词总长度
            len(found_terms),  # 找到的术语数
            len(text_values),  # 待翻译文本数
            found_terms  # 匹配到的术语表
        )

        return full_prompt

    @staticmethod
    def _build_terminology_section(found_terms: Dict[str, str]) -> str:
        """构建术语表部分"""
        if not found_terms:
            return "【术语表】\n无匹配术语\n"

        terminology_lines = ["【术语表】"]
        for en, zh in found_terms.items():
            terminology_lines.append(f"{en}: {zh}")
        terminology_lines.append("")  # 添加空行分隔

        return "\n".join(terminology_lines)

    def _build_content_section(self, text_values: List[str]) -> str:
        """构建翻译内容部分"""
        content_lines = ["【翻译内容】"]
        for i, value in enumerate(text_values):
            content_lines.append(f"{i + 1}. {value}")

        return "\n".join(content_lines)

    def add_terminology(self, en_term: str, zh_term: str) -> None:
        """添加术语到术语表

        Args:
            en_term: 英文术语
            zh_term: 中文翻译
        """
        self.terminology[en_term] = zh_term
        self._automaton_dirty = True  # 标记自动机需要重建

    def remove_terminology(self, en_term: str) -> bool:
        """从术语表移除术语

        Args:
            en_term: 英文术语

        Returns:
            bool: 是否移除成功
        """
        if en_term in self.terminology:
            del self.terminology[en_term]
            self._automaton_dirty = True  # 标记自动机需要重建
            return True
        return False

    def clear_terminology(self) -> None:
        """清空术语表"""
        self.terminology.clear()
        self._automaton = None
        self._automaton_dirty = False

    def save_terminology(self, file_path: str) -> bool:
        """保存术语表到文件

        Args:
            file_path: 保存路径

        Returns:
            bool: 是否保存成功
        """
        try:
            result = file_tool.save_json_file(self.terminology, file_path)
            return result
        except Exception as e:
            signal_bus.error_occurred.emit(f"保存术语表失败: {e}")
            return False

    def get_term_count(self) -> int:
        """获取术语数量"""
        return len(self.terminology)