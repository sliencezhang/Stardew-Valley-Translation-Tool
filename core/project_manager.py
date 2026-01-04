# core/project_manager.py
import os
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict
from datetime import datetime
from core.file_tool import file_tool
from PySide6.QtCore import QObject

from core.signal_bus import signal_bus


@dataclass
class ProjectConfig:
    name: str
    path: str
    created_time: str
    last_modified: str


class ProjectManager(QObject):
    """项目管理器 - 使用统一信号机制"""

    
    def __init__(self):
        super().__init__()
        self.current_project: Optional[ProjectConfig] = None
        self.cache_manager = None  # 初始化 cache_manager 属性
        self.project_structure = {
            'en': '存放英文JSON文件',
            'zh': '存放中文JSON文件',
            'output': '存放翻译输出',
            'manifest': '存放Manifest文件',
            'cache': '缓存目录'
        }


    def create_project(self, project_name: str, base_path: str = None) -> str:
        """创建新项目"""
        try:
            # 如果没有提供基础路径，使用用户主目录
            if base_path:
                base_path = Path(base_path)
            else:
                # 使用路径工具模块获取正确的应用目录
                try:
                    from core.path_utils import get_application_directory
                    base_path = get_application_directory()
                except ImportError:
                    # 如果路径工具不可用，使用回退方案
                    if getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS'):
                        # 打包环境
                        base_path = Path(sys.executable).parent
                    else:
                        # 开发环境
                        base_path = Path.cwd()

            project_path = base_path / project_name


            # 确保项目根目录存在
            os.makedirs(project_path, exist_ok=True)

            # 创建项目文件夹结构
            for folder in self.project_structure.keys():
                folder_path = Path(project_path).joinpath(folder)
                os.makedirs(folder_path, exist_ok=True)

            # 创建项目配置文件
            project_config = ProjectConfig(
                name=project_name,
                path=str(project_path),
                created_time=self._get_current_time(),
                last_modified=self._get_current_time()
            )

            self._save_project_config(project_config)
            self.current_project = project_config
            
            # 初始化缓存管理器
            self._initialize_cache_manager()

            signal_bus.log_message.emit("SUCCESS", "项目创建成功", {
                "project_path": project_path,
                "structure": self.project_structure
            })
            
            return str(project_path)

        except Exception as e:
            signal_bus.log_message.emit("ERROR", "创建项目失败", {
                "error": str(e),
                "project_name": project_name
            })
            raise

    def open_project(self, project_path: str) -> bool:
        """打开现有项目"""
        config_file = Path(project_path) / 'project_config.json'
        if not config_file.exists():
            signal_bus.log_message.emit("ERROR", "项目配置文件不存在", {
                "config_file": str(config_file)
            })
            return False

        try:
            config_data = file_tool.read_json_file(str(config_file))
            
            # 更新路径为当前传入的路径，而不是配置文件中的路径
            config_data['path'] = project_path
            self.current_project = ProjectConfig(**config_data)
            
            # 保存更新后的配置
            self._save_project_config(self.current_project)

            # 检查项目结构
            self._check_project_structure()
            
            # 初始化缓存管理器
            self._initialize_cache_manager()
            
            return True
            
        except Exception as e:
            signal_bus.log_message.emit("ERROR", "打开项目失败", {
                "error": str(e),
                "project_path": project_path
            })
            return False

    def _check_project_structure(self):
        """检查项目结构，但不自动创建文件夹"""
        if not self.current_project:
            return

        project_path = self.current_project.path
        missing_folders = []

        for folder in self.project_structure.keys():
            folder_path = os.path.join(project_path, folder)
            if not os.path.exists(folder_path):
                missing_folders.append(folder)
                signal_bus.log_message.emit("INFO", f"缺失文件夹: {folder}", {})
                # 不自动创建文件夹，只记录日志

        if missing_folders:
            signal_bus.log_message.emit("INFO", f"发现 {len(missing_folders)} 个缺失文件夹", {
                "missing_folders": missing_folders
            })

    def get_project_info(self) -> Dict:
        """获取项目信息"""
        if not self.current_project:
            return {}

        info = asdict(self.current_project)

        # 添加文件夹统计信息
        for folder in self.project_structure.keys():
            folder_path = os.path.join(self.current_project.path, folder)
            if os.path.exists(folder_path):
                file_count = len([f for f in os.listdir(folder_path)
                                if os.path.isfile(os.path.join(folder_path, f)) and not f.startswith('.')])
                info[f'{folder}_file_count'] = file_count

        return info

    def get_folder_path(self, folder_type: str, auto_create: bool = True, emit_message: bool = True) -> str:
        """获取文件夹路径（改进版）"""
        if not self.current_project:
            signal_bus.log_message.emit("ERROR", "没有当前项目", {
                "operation": "get_folder_path",
                "folder_type": folder_type
            })
            return ""

        try:
            from pathlib import Path
            base_path = Path(self.current_project.path)
            folder_path = base_path / folder_type
            
            # 根据参数决定是否自动创建文件夹
            if auto_create:
                folder_path.mkdir(parents=True, exist_ok=True)
                action_msg = "创建并获取"
            else:
                action_msg = "获取"

            # 转换为标准字符串（统一使用正斜杠）
            result_path = str(folder_path).replace('\\', '/')

            if emit_message:
                signal_bus.log_message.emit("SUCCESS", f"{action_msg} {folder_type} 文件夹📁 路径成功", {
                    "folder_path": result_path
                })

            return result_path

        except Exception as e:
            signal_bus.log_message.emit("ERROR", "获取文件夹路径失败", {
                "folder_type": folder_type,
                "error": str(e)
            })
            return ""

    @staticmethod
    def _save_project_config(config: ProjectConfig) -> None:
        """保存项目配置"""
        try:
            config_file_path = str((Path(config.path) / 'project_config.json').as_posix())
            # config_file_path = os.path.join(config.path, 'project_config.json')
            file_tool.save_json_file(asdict(config),config_file_path, )
            signal_bus.log_message.emit("SUCCESS", "项目配置已保存", {
                "config_file": config_file_path
            })
        except Exception as e:
            signal_bus.log_message.emit("ERROR", "保存项目配置失败", {
                "error": str(e)
            })

    def _initialize_cache_manager(self):
        """初始化缓存管理器"""
        if self.current_project and not self.cache_manager:
            try:
                from core.translation_cache import TranslationCache
                self.cache_manager = TranslationCache(self)
                # signal_bus.log_message.emit("SUCCESS", "缓存管理器初始化成功", {
                #     "cache_file": self.cache_manager.cache_file
                # })
            except Exception as e:
                signal_bus.log_message.emit("ERROR", "缓存管理器初始化失败", {
                    "error": str(e)
                })

    def _update_project_modified_time(self) -> None:
        """更新项目修改时间"""
        if self.current_project:
            self.current_project.last_modified = self._get_current_time()
            self._save_project_config(self.current_project)
            signal_bus.log_message.emit("INFO", "更新项目修改时间", {
                "project_name": self.current_project.name,
                "new_time": self.current_project.last_modified
            })

    # 工具方法
    @staticmethod
    def _get_current_time():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")



