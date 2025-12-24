# core/translation_engine.py
import re
import traceback
from typing import List
from PySide6.QtCore import QObject

from core.config import config
from core.file_tool import file_tool
from core.terminology_manager import TerminologyManager
from core.variable_protector import VariableProtector
from core.api_client import APIClientFactory
from core.signal_bus import signal_bus


class TranslationEngine(QObject):
    """翻译引擎 - 只负责AI翻译"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 配置
        self.batch_size = config.default_batch_size
        self.max_retries = config.max_retries
        self.temperature = config.temperature
        
        # 管理器
        self.terminology_manager = TerminologyManager("translation_prompt", parent=self)
        self.variable_protector = VariableProtector()
        
        # API客户端
        self.api_client = None
        self._init_api_client()
        
        # 加载默认术语表
        self._load_default_terminology()
        
        # 连接设置保存信号（统一处理所有配置更新）
        signal_bus.settingsSaved.connect(self._on_settings_saved)
    
    def _count_tokens(self, text: str) -> int:
        """
        手动计算文本的token数量（适用于DeepSeek V3等模型）
        DeepSeek V3的token计算规律：
        - 中文字符：每个字符约1.3-1.5个token
        - 英文单词：平均4个字符约1个token
        - 数字和符号：通常每个占1个token
        """
        if not text:
            return 0
        
        # 统计不同类型的字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        numbers = len(re.findall(r'[0-9]', text))
        spaces = len(re.findall(r'\s', text))
        punctuation = len(re.findall(r'[^\w\s]', text))
        
        # DeepSeek V3的近似计算
        tokens = (
            chinese_chars * 1.4 +  # 中文每个字符约1.4个token
            english_chars / 4.0 +  # 英文平均4个字符1个token
            numbers * 0.8 +        # 数字通常每个不到1个token
            spaces * 0.3 +         # 空格通常多个算1个token
            punctuation * 0.7      # 标点符号通常每个不到1个token
        )
        
        return int(tokens)
    
    def _init_api_client(self):
        """初始化API客户端"""
        try:
            api_config = config.get_current_api_config()
            provider = api_config["provider"]
            api_key = api_config["api_key"]
            api_url = api_config["api_url"]
            model = api_config["model"]
            
            if api_key or provider == "local":
                self.api_client = APIClientFactory.create_client(
                    provider, api_key, api_url, model, self.temperature
                )
                provider_name = self.api_client.get_name()
                signal_bus.log_message.emit("INFO", f"🔌 使用API: {provider_name} | URL: {api_url} | 模型: {model}", {})
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"API客户端初始化失败: {e}", {})
    
    def _on_settings_saved(self, settings):
        """设置保存回调，自动更新所有相关配置"""
        # 更新批次大小和温度参数
        old_batch_size = self.batch_size
        old_temperature = self.temperature
        
        self.batch_size = config.default_batch_size
        self.temperature = config.temperature
        
        # 重新初始化API客户端（会使用新的API配置和温度参数）
        self._init_api_client()
        
        # 重新加载术语表
        self._reload_terminology()
        
        # 重新加载翻译提示词
        self._reload_prompt()
        
        # 记录参数变化
        if old_temperature != self.temperature:
            signal_bus.log_message.emit("INFO", f"温度参数已更新: {old_temperature} -> {self.temperature}", {})
        
        if old_batch_size != self.batch_size:
            signal_bus.log_message.emit("INFO", f"每批翻译数量已更新: {old_batch_size} -> {self.batch_size}", {})
        
        signal_bus.log_message.emit("INFO", "翻译引擎配置已自动更新", {})
    
    def _load_default_terminology(self):
        """加载默认术语表"""
        try:
            from pathlib import Path
            current_dir = Path(__file__).parent
            terminology_file = current_dir / "../resources/terminology.json"
            terminology_file = terminology_file.resolve()
            
            if terminology_file.exists():
                signal_bus.log_message.emit("INFO", f"[术语表] 从文件加载默认术语: {terminology_file}", {})
                terminology_data = file_tool.read_json_file(str(terminology_file))
                for en_term, zh_term in terminology_data.items():
                    self.terminology_manager.add_terminology(en_term, zh_term)
                signal_bus.log_message.emit("INFO", f"已加载 {len(terminology_data)} 个默认术语", {})
            else:
                signal_bus.log_message.emit("WARNING", f"默认术语表文件不存在: {terminology_file}", {})
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"加载默认术语表失败: {e}", {})
    
    def _reload_terminology(self):
        """重新加载术语表"""
        try:
            self.terminology_manager.clear_terminology()
            self._load_default_terminology()
            signal_bus.log_message.emit("INFO", "术语表已重新加载", {})
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"重新加载术语表失败: {e}", {})
    
    def _reload_prompt(self):
        """重新加载提示词"""
        try:
            self.terminology_manager.default_prompt = self.terminology_manager.get_default_prompt("translation_prompt")
            signal_bus.log_message.emit("INFO", "提示词已重新加载", {})
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"重新加载提示词失败: {e}", {})
    
    def translate_texts(self, texts: List[str]) -> List[str]:
            """翻译文本列表"""
            if not texts:
                return []

            if not self.api_client:
                raise ValueError("API客户端未初始化")

            translations = [""] * len(texts)
            original_batch_size = len(texts)  # 记录原始批次大小
            current_batch_size = original_batch_size

            # 动态调整批次大小的策略
            batch_sizes = [original_batch_size, 5, 1]
            batch_size_index = 0

            for retry in range(self.max_retries + 1):
                try:
                    # 根据重试次数调整批次大小
                    if retry > 0 and batch_size_index < len(batch_sizes) - 1:
                        # 第一次失败后，尝试较小的批次
                        current_batch_size = batch_sizes[min(batch_size_index + 1, len(batch_sizes) - 1)]
                        batch_size_index += 1
                        signal_bus.log_message.emit("INFO", f"重试时调整批次大小: {original_batch_size} -> {current_batch_size}", {})

                    # 如果批次大小小于原始大小，需要分批处理
                    if current_batch_size < original_batch_size:
                        # 分批翻译
                        all_translations = []
                        for i in range(0, len(texts), current_batch_size):
                            batch_texts = texts[i:i + current_batch_size]
                            batch_translations = self._translate_single_batch(batch_texts)
                            all_translations.extend(batch_translations)
                        # 如果成功，返回所有翻译结果
                        if all_translations and all(t.strip() for t in all_translations):
                            return all_translations
                        else:
                            raise Exception("分批翻译失败")
    
                    else:
                        # 直接翻译整个批次
                        # 变量保护
                        protected_texts = []
                        batch_var_info = set()  # 用于去重
                        for i, text in enumerate(texts):
                            if text and text.strip():
                                protected, var_map = self.variable_protector.protect_variables(text)
                                protected_texts.append(protected)
                                # 收集变量信息，用于去重显示
                                if var_map:
                                    for var, marker in var_map.items():
                                        var_info = f"{marker}→{var}"
                                        if var_info not in batch_var_info:
                                            batch_var_info.add(var_info)
                        # 批次结束后统一发送一次信号
                        if batch_var_info:
                            var_info_str = ", ".join(sorted(batch_var_info))
                            signal_bus.log_message.emit("DEBUG", f"批次变量保护({len(texts)}条): {var_info_str}", {})
                        else:
                            protected_texts.append(text)
                        # 构建提示词
                        prompt = self.terminology_manager.build_translation_prompt(protected_texts)
                        # 获取匹配到的术语表信息
                        found_terms = self.terminology_manager.get_terms_in_text(" ".join(protected_texts))
                        if found_terms:
                            terms_info = ", ".join([f"{en}→{zh}" for en, zh in found_terms.items()])
                            signal_bus.log_message.emit("DEBUG", f"匹配到术语: {terms_info}", {})
                        # 调用API
                        response = self.api_client.call_api(prompt)
                        # 使用更准确的token计算
                        prompt_tokens = self._count_tokens(prompt)
                        response_tokens = self._count_tokens(response) if response else 0
                        signal_bus.log_message.emit("DEBUG", f"提示词tokens: {prompt_tokens}, 响应tokens: {response_tokens}, 字符长度(提示/响应): {len(prompt)}/{len(response) if response else 0}", {})

                        # 输出API返回的原始内容
                        if response:
                            signal_bus.log_message.emit("DEBUG", f"API原始响应内容:\n{response}", {})
                        else:
                            signal_bus.log_message.emit("WARNING", "API返回空响应", {})
                        # 解析响应
                        parsed_translations = self._parse_value_response(response, len(texts))
                        # 恢复变量
                        for i, translated in enumerate(parsed_translations):
                            if i < len(texts):
                                translations[i] = self.variable_protector.restore_variables(translated)
                        
                        return translations
                except Exception as e:
                    signal_bus.log_message.emit("ERROR", f"翻译失败 (重试 {retry}/{self.max_retries}, 批次大小: {current_batch_size}): {str(e)}", {})
                    traceback.print_exc()
                    # 如果是最后一次重试，返回空字符串
                    if retry == self.max_retries:
                        return [""] * len(texts)
                    # 等待一段时间再重试
                    import time
                    time.sleep(2)  # 等待2秒
                    continue
            return translations
    
            
    
                
    
            
    
    def _translate_single_batch(self, texts: List[str]) -> List[str]:
        """翻译单个批次"""
        if not texts:
            return []
        # 变量保护
        protected_texts = []
        batch_var_info = set()  # 用于去重
        for i, text in enumerate(texts):
            if text and text.strip():
                protected, var_map = self.variable_protector.protect_variables(text)
                protected_texts.append(protected)
                # 收集变量信息，用于去重显示
                if var_map:
                    for var, marker in var_map.items():
                        var_info = f"{var}→{marker}"
                        if var_info not in batch_var_info:
                            batch_var_info.add(var_info)
        # 批次结束后统一发送一次信号
        if batch_var_info:
            var_info_str = ", ".join(sorted(batch_var_info))
            signal_bus.log_message.emit("DEBUG", f"批次[{len(texts)}]变量保护: {var_info_str}", {})
        # 构建提示词
        prompt = self.terminology_manager.build_translation_prompt(protected_texts)
        # 调用API
        response = self.api_client.call_api(prompt)
        # 解析响应
        parsed_translations = self._parse_value_response(response, len(texts))
        # 恢复变量
        translations = []
        for i, translated in enumerate(parsed_translations):
            if i < len(texts):
                translations.append(self.variable_protector.restore_variables(translated))
        return translations
    
    @staticmethod
    def _parse_value_response(response: str, expected_count: int) -> List[str]:
        """解析API响应 - 支持多行翻译内容"""
        lines = response.strip().split('\n')
        translations = []
        current_index = None
        current_content = []

        for line in lines:
            line = line.rstrip()  # 保留行内空格，只去掉行尾空格
            
            # 检查是否是新翻译项的开始（如 "1. "）
            if re.match(r'^\d+\. ', line):
                # 保存上一个翻译项
                if current_index is not None:
                    # 合并当前收集的内容
                    translation = '\n'.join(current_content).strip()
                    while len(translations) <= current_index:
                        translations.append("")
                    translations[current_index] = translation
                
                # 开始新的翻译项
                parts = line.split('. ', 1)
                if len(parts) == 2 and parts[0].isdigit():
                    current_index = int(parts[0]) - 1
                    current_content = [parts[1]]
                else:
                    current_index = None
                    current_content = []
            else:
                # 继续当前翻译项的内容
                if current_index is not None:
                    current_content.append(line)

        # 保存最后一个翻译项
        if current_index is not None:
            translation = '\n'.join(current_content).strip()
            while len(translations) <= current_index:
                translations.append("")
            translations[current_index] = translation

        # 确保返回正确数量的翻译
        while len(translations) < expected_count:
            translations.append("")
        
        return translations[:expected_count]
