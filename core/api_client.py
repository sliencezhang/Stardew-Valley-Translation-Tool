"""
API客户端抽象类和具体实现
支持多个API提供商
"""
from abc import ABC, abstractmethod
from typing import Dict, List
import requests
from core.config import config


class APIClient(ABC):
    """API客户端抽象基类"""
    
    def __init__(self, api_key: str, base_url: str, model: str, temperature: float = 0.3, timeout: int = 120):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
    
    @abstractmethod
    def call_api(self, prompt: str) -> str:
        """调用API进行翻译"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """获取API提供商名称"""
        pass


class SiliconFlowClient(APIClient):
    """硅基流动API客户端"""
    
    def get_name(self) -> str:
        return "硅基流动"
    
    def call_api(self, prompt: str) -> str:
        """调用硅基流动API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
            "stream": False
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            json=data,
            timeout=self.timeout,
            proxies=config.get_proxies() if hasattr(config, 'get_proxies') else None
        )
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]


class DeepSeekClient(APIClient):
    """DeepSeek官网API客户端"""
    
    def get_name(self) -> str:
        return "DeepSeek官网"
    
    def call_api(self, prompt: str) -> str:
        """调用DeepSeek官网API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
            "stream": False
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            json=data,
            timeout=self.timeout,
            proxies=config.get_proxies() if hasattr(config, 'get_proxies') else None
        )
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]


class LocalAPIClient(APIClient):
    """本地API客户端 (如 LM Studio)"""
    
    def __init__(self, api_key: str, base_url: str, model: str, temperature: float = 0.3, timeout: int = 180):
        super().__init__(api_key, base_url, model, temperature, timeout)
    
    def get_name(self) -> str:
        return "本地API"
    
    def call_api(self, prompt: str) -> str:
        """调用本地API (如 LM Studio)"""
        headers = {
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
            "stream": False
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            json=data,
            timeout=self.timeout
        )
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]


class OpenAICompatibleClient(APIClient):
    """OpenAI兼容API客户端（通用）"""
    
    def __init__(self, api_key: str, base_url: str, model: str, temperature: float = 0.3, name: str = "OpenAI兼容API", timeout: int = 120):
        super().__init__(api_key, base_url, model, temperature, timeout)
        self.provider_name = name
    
    def get_name(self) -> str:
        return self.provider_name
    
    def call_api(self, prompt: str) -> str:
        """调用OpenAI兼容API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
            "stream": False
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            json=data,
            timeout=self.timeout,
            proxies=config.get_proxies() if hasattr(config, 'get_proxies') else None
        )
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]


class APIClientFactory:
    """API客户端工厂类"""
    
    # 预定义的API提供商配置
    PROVIDERS = {
        "siliconflow": {
            "name": "硅基流动",
            "class": SiliconFlowClient,
            "default_url": "https://api.siliconflow.cn/v1/chat/completions",
            "default_model": "deepseek-ai/DeepSeek-V3"
        },
        "deepseek": {
            "name": "DeepSeek官网",
            "class": DeepSeekClient,
            "default_url": "https://api.deepseek.com/v1/chat/completions",
            "default_model": "deepseek-chat"
        },
        "openai": {
            "name": "OpenAI",
            "class": OpenAICompatibleClient,
            "default_url": "https://api.openai.com/v1/chat/completions",
            "default_model": "gpt-4o-mini"
        },
        "qwen": {
            "name": "通义千问",
            "class": OpenAICompatibleClient,
            "default_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            "default_model": "qwen-plus"
        },
        "kimi": {
            "name": "Kimi",
            "class": OpenAICompatibleClient,
            "default_url": "https://api.moonshot.cn/v1/chat/completions",
            "default_model": "moonshot-v1-8k"
        },
        "zhipu": {
            "name": "智谱AI",
            "class": OpenAICompatibleClient,
            "default_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            "default_model": "glm-4-flash"
        },
        "doubao": {
            "name": "豆包API",
            "class": OpenAICompatibleClient,
            "default_url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            "default_model": "doubao-pro-32k"
        },
        "hunyuan": {
            "name": "混元API",
            "class": OpenAICompatibleClient,
            "default_url": "https://api.hunyuan.cloud.tencent.com/v1/chat/completions",
            "default_model": "hunyuan-lite"
        },
        "local": {
            "name": "本地API",
            "class": LocalAPIClient,
            "default_url": "http://127.0.0.1:1234/v1/chat/completions",
            "default_model": "local-model"
        }
    }
    
    @classmethod
    def create_client(cls, provider: str, api_key: str, base_url: str = None, model: str = None, temperature: float = 0.3, timeout: int = 120) -> APIClient:
        """创建API客户端实例"""
        if provider not in cls.PROVIDERS:
            raise ValueError(f"不支持的API提供商: {provider}")
        
        provider_config = cls.PROVIDERS[provider]
        client_class = provider_config["class"]
        
        # 使用默认值如果没有提供
        if not base_url:
            base_url = provider_config["default_url"]
        if not model:
            model = provider_config["default_model"]
        
        # 如果是OpenAICompatibleClient，需要传递name参数
        if client_class == OpenAICompatibleClient:
            return client_class(api_key, base_url, model, temperature, provider_config["name"], timeout)
        else:
            return client_class(api_key, base_url, model, temperature, timeout)
    
    @classmethod
    def get_providers(cls) -> List[str]:
        """获取所有支持的API提供商"""
        return list(cls.PROVIDERS.keys())
    
    @classmethod
    def get_provider_info(cls, provider: str) -> Dict:
        """获取API提供商信息"""
        if provider not in cls.PROVIDERS:
            raise ValueError(f"不支持的API提供商: {provider}")
        
        config = cls.PROVIDERS[provider]
        return {
            "name": config["name"],
            "default_url": config["default_url"],
            "default_model": config["default_model"]
        }