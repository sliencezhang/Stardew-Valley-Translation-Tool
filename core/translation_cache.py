# core/translation_cache.py
import os
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.project_manager import ProjectManager
from core.file_tool import file_tool
from core.signal_bus import signal_bus


class TranslationCache:
    """独立的翻译缓存管理器"""
    
    # 类变量，用于跟踪缓存实例
    _instances = {}
    
    def __new__(cls, project_manager: ProjectManager = None):
        """创建单例实例"""
        # 只有在有项目时才创建缓存实例
        if not project_manager or not project_manager.current_project:
            return None
        
        project_path = project_manager.current_project.path

        
        if project_path not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[project_path] = instance
        
        return cls._instances[project_path]

    def __init__(self, project_manager: ProjectManager = None):
        # 避免重复初始化
        if hasattr(self, '_initialized'):
            return
        
        self.project_manager = project_manager
        self._initialized = True
        
        
        # 安全获取缓存文件夹路径
        cache_folder = None
        if project_manager and hasattr(project_manager, 'get_folder_path'):
            cache_folder = project_manager.get_folder_path("cache")
        
        if cache_folder and cache_folder.strip():
            self.cache_file = str(Path(cache_folder) / "translation_cache.json")
        else:
            # 使用默认缓存路径
            self.cache_file = "cache/translation_cache.json"

        self.cache = self.load_cache() or {}

    def __repr__(self):
        """安全的字符串表示，避免递归"""
        try:
            return f"<TranslationCache entries={len(self.cache)}>"
        except:
            return "<TranslationCache>"

    def __str__(self):
        """安全的字符串表示，避免递归"""
        try:
            return f"TranslationCache({len(self.cache)} entries)"
        except:
            return "TranslationCache"

    def load_cache(self):
        """加载缓存文件"""
        if os.path.exists(self.cache_file):
            
            cache_data = file_tool.read_json_file(self.cache_file)
            signal_bus.log_message.emit("INFO", f"加载的缓存条目数：{len(cache_data)}", {})
            return cache_data
        else:
            return {}

    def save_cache(self) -> bool:
        """保存缓存到文件"""
        try:
            # 确保目录存在
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir and cache_dir.strip():
                os.makedirs(cache_dir, exist_ok=True)
                
                # 直接保存
                file_tool.save_json_file(self.cache, self.cache_file)
            return True
        except Exception:
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def _get_text_hash(text: str) -> str:
        """生成文本的哈希值"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def get_cached_translation(self, original_text: str) -> Optional[str]:
        """获取缓存的翻译"""
        text_hash = self._get_text_hash(original_text)
        return self.cache.get(text_hash)


    def set_cached_translation(self, original_text: str, translated_text: str) -> bool:
        """设置缓存翻译"""
        text_hash = self._get_text_hash(original_text)
        self.cache[text_hash] = translated_text

        # 保存到文件
        success = self.save_cache()

        return success

    

    def batch_set_cached(self, original_texts: List[str], translated_texts: List[str]) -> bool:
        """批量设置缓存"""
        for original, translated in zip(original_texts, translated_texts):
            text_hash = self._get_text_hash(original)
            self.cache[text_hash] = translated
        
        # 批量完成后保存一次
        return self.save_cache()
    
    

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            '缓存条目数': len(self.cache),
            '缓存文件': self.cache_file
        }

