# core/config.py
from typing import Dict
import sys
from pathlib import Path
from core.signal_bus import signal_bus
from version import VERSION


def get_resource_path(relative_path):
    """获取资源文件的绝对路径，支持开发环境和打包后的环境"""
    base_path = Path(sys.argv[0]).parent
    return base_path / relative_path




class Config:
    """配置管理器"""

    def __init__(self):
        # 版本信息
        self.version = VERSION
        self.app_name = "星露谷物语翻译工具"
        
        # GitHub仓库配置
        self.github_owner = "sliencezhang"  # 替换为实际的GitHub用户名
        self.github_repo = "Stardew-Valley-Translation-Tool"
        
        # 更新下载配置
        self.update_download_url = "https://wwbml.lanzoum.com/b0187zweze"  # 替换为实际的蓝奏云链接
        self.update_download_password = "5pza"  # 替换为实际的下载密码
        
        # 默认配置
        self.api_provider = "siliconflow"  # 默认使用硅基流动
        self.api_keys = {}  # 存储多个API提供商的密钥
        self.api_urls = {}  # 存储多个API提供商的URL
        self.api_models = {}  # 存储多个API提供商的模型
        
        # 硅基流动默认配置
        self.api_keys["siliconflow"] = ""
        self.api_urls["siliconflow"] = "https://api.siliconflow.cn/v1/chat/completions"
        self.api_models["siliconflow"] = "deepseek-ai/DeepSeek-V3"
        
        # DeepSeek官网默认配置
        self.api_keys["deepseek"] = ""
        self.api_urls["deepseek"] = "https://api.deepseek.com/v1/chat/completions"
        self.api_models["deepseek"] = "deepseek-chat"
        
        # OpenAI默认配置
        self.api_keys["openai"] = ""
        self.api_urls["openai"] = "https://api.openai.com/v1/chat/completions"
        self.api_models["openai"] = "gpt-4o-mini"
        
        # 通义千问默认配置
        self.api_keys["qwen"] = ""
        self.api_urls["qwen"] = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.api_models["qwen"] = "qwen-plus"
        
        # Kimi默认配置
        self.api_keys["kimi"] = ""
        self.api_urls["kimi"] = "https://api.moonshot.cn/v1/chat/completions"
        self.api_models["kimi"] = "moonshot-v1-8k"
        
        # 智谱AI默认配置
        self.api_keys["zhipu"] = ""
        self.api_urls["zhipu"] = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        self.api_models["zhipu"] = "glm-4-flash"
        
        # 豆包API默认配置
        self.api_keys["doubao"] = ""
        self.api_urls["doubao"] = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        self.api_models["doubao"] = "doubao-pro-32k"
        
        # 混元API默认配置
        self.api_keys["hunyuan"] = ""
        self.api_urls["hunyuan"] = "https://api.hunyuan.cloud.tencent.com/v1/chat/completions"
        self.api_models["hunyuan"] = "hunyuan-lite"
        
        # 本地API默认配置
        self.api_keys["local"] = ""
        self.api_urls["local"] = "http://127.0.0.1:1234/v1/chat/completions"
        self.api_models["local"] = "local-model"
        
        # 兼容旧配置
        self.api_key = ""
        self.api_url = self.api_urls[self.api_provider]
        self.default_model = self.api_models[self.api_provider]
        
        # 其他配置
        self.default_batch_size = 20
        self.max_retries = 2
        self.api_timeout = 120  # API请求超时时间（秒）
        self.temperature = 0.3
        self.theme = "light"
        self.use_background = True
        self.custom_background_light = ""
        self.custom_background_dark = ""

        # 加载保存的配置
        self.load_from_settings()
        
        # 确保所有API提供商都有默认配置
        self._ensure_default_configs()

    def load_from_settings(self):
        """从QSettings加载配置"""
        try:
            from PySide6.QtCore import QSettings
            settings = QSettings("StardewTranslator", "StardewTranslator")

            # 加载API提供商配置
            self.api_provider = settings.value("api_provider", self.api_provider)
            
            # 加载各API提供商的密钥
            for provider in ["siliconflow", "deepseek", "openai", "qwen", "kimi", "zhipu", "doubao", "hunyuan", "local"]:
                key = settings.value(f"api_key_{provider}", "")
                url = settings.value(f"api_url_{provider}", self.api_urls.get(provider))  # 使用默认值
                model = settings.value(f"api_model_{provider}", self.api_models.get(provider))  # 使用默认值
                
                if key:
                    self.api_keys[provider] = key
                # 总是更新URL和模型，确保使用默认值或保存的值
                self.api_urls[provider] = url
                self.api_models[provider] = model
            
            # 兼容旧配置
            old_key = settings.value("api_key", "")
            if old_key and not self.api_keys.get(self.api_provider):
                self.api_keys[self.api_provider] = old_key
            
            # 只有在没有保存过新格式的URL时才使用旧格式的URL
            old_url = settings.value("api_url", "")
            if old_url and not settings.value(f"api_url_{self.api_provider}", None):
                self.api_urls[self.api_provider] = old_url
            
            # 只有在没有保存过新格式的模型时才使用旧格式的模型
            old_model = settings.value("model", "")
            if old_model and not settings.value(f"api_model_{self.api_provider}", None):
                self.api_models[self.api_provider] = old_model
            
            # 更新兼容属性
            self.api_key = self.api_keys.get(self.api_provider, "")
            self.api_url = self.api_urls.get(self.api_provider, "")
            self.default_model = self.api_models.get(self.api_provider, "")
            
            # 加载版本相关配置
            self.github_owner = settings.value("github_owner", self.github_owner)
            self.github_repo = settings.value("github_repo", self.github_repo)
            self.update_download_url = settings.value("update_download_url", self.update_download_url)
            self.update_download_password = settings.value("update_download_password", self.update_download_password)
            
            # 加载其他配置
            self.default_batch_size = int(settings.value("batch_size", self.default_batch_size))
            self.max_retries = int(settings.value("max_retries", self.max_retries))
            self.api_timeout = int(settings.value("api_timeout", self.api_timeout))
            self.temperature = float(settings.value("temperature", self.temperature))
            self.theme = settings.value("theme", self.theme)
            self.use_background = settings.value("use_background", self.use_background, type=bool)
            self.custom_background_light = settings.value("custom_background_light", self.custom_background_light)
            self.custom_background_dark = settings.value("custom_background_dark", self.custom_background_dark)
            
        except Exception:
            # 如果QSettings不可用，使用默认值
            pass
        
        # 检查是否在打包环境中运行
        if getattr(sys, 'frozen', False):
            # 尝试从文件加载配置（如果存在）
            from pathlib import Path
            config_file = Path.home() / "Documents" / "StardewTranslator" / "config.json"
            if config_file.exists():
                self._load_from_file(config_file)
            else:
                # 如果配置文件不存在，确保保存默认配置
                # 这样下次启动时就能加载到默认值
                self._save_to_file()
    
    def save_to_settings(self):
        """保存配置到QSettings"""
        try:
            from PySide6.QtCore import QSettings
            settings = QSettings("StardewTranslator", "StardewTranslator")
            
            # 保存API提供商配置
            settings.setValue("api_provider", self.api_provider)
            
            # 保存各API提供商的配置
            for provider in ["siliconflow", "deepseek", "openai", "qwen", "kimi", "zhipu", "doubao", "hunyuan", "local"]:
                settings.setValue(f"api_key_{provider}", self.api_keys.get(provider, ""))
                settings.setValue(f"api_url_{provider}", self.api_urls.get(provider, ""))
                settings.setValue(f"api_model_{provider}", self.api_models.get(provider, ""))
            
            # 保存版本相关配置
            settings.setValue("github_owner", self.github_owner)
            settings.setValue("github_repo", self.github_repo)
            settings.setValue("update_download_url", self.update_download_url)
            settings.setValue("update_download_password", self.update_download_password)
            
            # 检查是否在打包环境中运行
            if getattr(sys, 'frozen', False):
                # 同时保存到文件
                self._save_to_file()
            
            # 保存其他配置
            settings.setValue("batch_size", self.default_batch_size)
            settings.setValue("max_retries", self.max_retries)
            settings.setValue("api_timeout", self.api_timeout)
            settings.setValue("temperature", self.temperature)
            settings.setValue("theme", self.theme)
            settings.setValue("use_background", self.use_background)
            settings.setValue("custom_background_light", self.custom_background_light)
            settings.setValue("custom_background_dark", self.custom_background_dark)
            
        except Exception:
            # 如果QSettings不可用，忽略保存
            pass
    
    def _save_to_file(self):
        """保存配置到文件"""
        try:
            import json
            from pathlib import Path
            
            # 创建配置目录
            config_dir = Path.home() / "Documents" / "StardewTranslator"
            config_dir.mkdir(parents=True, exist_ok=True)
            
            config_file = config_dir / "config.json"
            
            config_data = {
                "api_provider": self.api_provider,
                "api_keys": self.api_keys,
                "api_urls": self.api_urls,
                "api_models": self.api_models,
                "api_key": self.api_key,  # 兼容旧配置
                "api_url": self.api_url,  # 兼容旧配置
                "default_model": self.default_model,  # 兼容旧配置
                "default_batch_size": self.default_batch_size,
                "max_retries": self.max_retries,
                "api_timeout": self.api_timeout,
                "temperature": self.temperature,
                "theme": self.theme,
                "use_background": self.use_background,
                "custom_background_light": self.custom_background_light,
                "custom_background_dark": self.custom_background_dark
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"保存配置文件失败: {e}", {})
    
    def _load_from_file(self, config_file=None):
        """从文件加载配置"""
        try:
            import json
            from pathlib import Path
            
            if config_file is None:
                config_file = Path.home() / "Documents" / "StardewTranslator" / "config.json"
            
            if not config_file.exists():
                return
                
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            self.api_provider = config_data.get("api_provider", "siliconflow")
            
            # 加载API密钥
            loaded_keys = config_data.get("api_keys", {})
            for provider in ["siliconflow", "deepseek", "openai", "qwen", "kimi", "zhipu", "doubao", "hunyuan", "local"]:
                self.api_keys[provider] = loaded_keys.get(provider, "")
            
            # 加载API URL，确保使用默认值
            loaded_urls = config_data.get("api_urls", {})
            for provider in ["siliconflow", "deepseek", "openai", "qwen", "kimi", "zhipu", "doubao", "hunyuan", "local"]:
                # 如果文件中没有这个provider的URL，使用初始化时的默认值
                if provider in loaded_urls:
                    self.api_urls[provider] = loaded_urls[provider]
                # 保持初始化时设置的默认值
            
            # 加载API模型，确保使用默认值
            loaded_models = config_data.get("api_models", {})
            for provider in ["siliconflow", "deepseek", "openai", "qwen", "kimi", "zhipu", "doubao", "hunyuan", "local"]:
                # 如果文件中没有这个provider的模型，使用初始化时的默认值
                if provider in loaded_models:
                    self.api_models[provider] = loaded_models[provider]
                # 保持初始化时设置的默认值
            
            # 兼容旧配置
            self.api_key = config_data.get("api_key", "")
            self.api_url = config_data.get("api_url", "")
            self.default_model = config_data.get("default_model", "")
            
            self.default_batch_size = config_data.get("default_batch_size", 20)
            self.max_retries = config_data.get("max_retries", 3)
            self.api_timeout = config_data.get("api_timeout", 120)
            self.temperature = config_data.get("temperature", 0.3)
            self.theme = config_data.get("theme", "light")
            self.use_background = config_data.get("use_background", True)
            self.custom_background_light = config_data.get("custom_background_light", "")
            self.custom_background_dark = config_data.get("custom_background_dark", "")
            
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"加载配置文件失败: {e}", {})
    
    def get_current_api_config(self) -> Dict:
        """获取当前API提供商的配置"""
        return {
            "provider": self.api_provider,
            "api_key": self.api_keys.get(self.api_provider, ""),
            "api_url": self.api_urls.get(self.api_provider, ""),
            "model": self.api_models.get(self.api_provider, "")
        }
    
    def set_current_api_config(self, provider: str, api_key: str, api_url: str = None, model: str = None):
        """设置当前API提供商的配置"""
        if provider not in ["siliconflow", "deepseek", "openai", "qwen", "kimi", "zhipu", "doubao", "hunyuan", "local"]:
            raise ValueError(f"不支持的API提供商: {provider}")
        
        self.api_provider = provider
        self.api_keys[provider] = api_key
        
        if api_url is not None:
            self.api_urls[provider] = api_url
        if model is not None:
            self.api_models[provider] = model
        
        # 更新兼容属性
        self.api_key = api_key
        self.api_url = self.api_urls[provider]
        self.default_model = self.api_models[provider]
        
        # 保存配置
        self.save_to_settings()

    

    def _ensure_default_configs(self):
        """确保所有API提供商都有默认配置"""
        # 定义所有API提供商的默认配置
        default_configs = {
            "siliconflow": {
                "url": "https://api.siliconflow.cn/v1/chat/completions",
                "model": "deepseek-ai/DeepSeek-V3"
            },
            "deepseek": {
                "url": "https://api.deepseek.com/v1/chat/completions",
                "model": "deepseek-chat"
            },
            "openai": {
                "url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4o-mini"
            },
            "qwen": {
                "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                "model": "qwen-plus"
            },
            "kimi": {
                "url": "https://api.moonshot.cn/v1/chat/completions",
                "model": "moonshot-v1-8k"
            },
            "zhipu": {
                "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "model": "glm-4-flash"
            },
            "doubao": {
                "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                "model": "doubao-pro-32k"
            },
            "hunyuan": {
                "url": "https://api.hunyuan.cloud.tencent.com/v1/chat/completions",
                "model": "hunyuan-lite"
            },
            "local": {
                "url": "http://127.0.0.1:1234/v1/chat/completions",
                "model": "local-model"
            }
        }
        
        # 确保每个提供商都有URL和模型
        for provider, config in default_configs.items():
            if provider not in self.api_urls or not self.api_urls[provider]:
                self.api_urls[provider] = config["url"]
            if provider not in self.api_models or not self.api_models[provider]:
                self.api_models[provider] = config["model"]
            if provider not in self.api_keys:
                self.api_keys[provider] = ""
        
        # 更新兼容属性
        self.api_key = self.api_keys.get(self.api_provider, "")
        self.api_url = self.api_urls.get(self.api_provider, "")
        self.default_model = self.api_models.get(self.api_provider, "")

    def get(self, key, default=None):
        """获取配置值（兼容字典接口）"""
        return getattr(self, key, default)

    def update(self, settings_dict):
        """更新配置"""
        for key, value in settings_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save_to_settings()

# 全局配置实例
config = Config()