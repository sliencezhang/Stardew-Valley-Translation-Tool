"""
星露谷物语翻译工具 - 更新检查模块
检查GitHub仓库是否有新版本发布
"""

import requests
import json
from datetime import datetime, timedelta
from packaging import version
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from core.config import config
from version import VERSION
from core.signal_bus import signal_bus


class UpdateChecker:
    """
    星露谷物语翻译工具更新检查器

    功能：
    1. 检查GitHub仓库是否有新版本
    2. 缓存检查结果，避免频繁请求
    3. 显示更新信息
    4. 提供下载链接
    """

    def __init__(self):
        """
        初始化更新检查器
        使用项目配置中的仓库信息和当前版本
        """
        # GitHub仓库信息（可在config.py中配置）
        self.repo_owner = getattr(config, 'github_owner', 'your-username')
        self.repo_name = getattr(config, 'github_repo', 'Stardew-Valley-Translation-Tool')
        self.current_version = VERSION

        # GitHub API 基础URL
        self.api_base = "https://api.github.com"

        # 缓存文件路径（动态获取，优先resources，失败则使用用户目录）
        self.cache_file = None  # 将在需要时动态获取

        # 请求超时时间（秒）
        self.timeout = 10

        # 自定义User-Agent（GitHub要求）
        self.user_agent = f"StardewValleyTranslationTool/{self.current_version}"

    def get_latest_release(self) -> dict:
        """获取最新的Release信息"""
        # 构建API URL
        api_url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/releases/latest"

        # 设置请求头
        headers = {
            "Accept": "application/vnd.github.v3+json",  # 指定API版本
            "User-Agent": self.user_agent
        }

        try:
            print("正在检查更新...")
            print(f"API URL: {api_url}")

            # 发送GET请求，禁用SSL验证（解决证书问题）
            response = requests.get(
                api_url,
                headers=headers,
                timeout=self.timeout,
                verify=False  # 禁用SSL证书验证
            )

            # 检查响应状态
            response.raise_for_status()  # 如果状态码不是200，抛出异常

            # 解析JSON响应
            release_data = response.json()

            print(f"获取到Release: {release_data.get('tag_name')}")
            return release_data

        except requests.exceptions.Timeout:
            print("请求超时，请检查网络连接")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print("未找到该仓库或没有Release")
            elif e.response.status_code == 403:
                # 可能是速率限制
                limit = e.response.headers.get('X-RateLimit-Limit', '?')
                remaining = e.response.headers.get('X-RateLimit-Remaining', '?')
                reset_time = e.response.headers.get('X-RateLimit-Reset', '?')
                print(f"API限制：{remaining}/{limit} 次，重置时间：{reset_time}")
            else:
                print(f"HTTP错误: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"网络请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return None

    def parse_version(self, version_str: str) -> version.Version:
        """
        解析版本字符串

        GitHub的tag_name可能有多种格式：
        - v1.0.0
        - version-1.0.0
        - 1.0.0
        - release-v1.0.0

        这个方法会清理前缀，提取纯版本号
        """
        # 移除常见的前缀
        prefixes = ['v', 'V', 'version', 'release-', 'ver.']
        clean_version = version_str

        for prefix in prefixes:
            if clean_version.lower().startswith(prefix.lower()):
                clean_version = clean_version[len(prefix):]
                # 如果移除前缀后以-或_开头，继续移除
                if clean_version.startswith(('-', '_')):
                    clean_version = clean_version[1:]

        # 使用packaging.version解析
        try:
            return version.parse(clean_version)
        except version.InvalidVersion:
            print(f"无法解析版本号: {version_str}")
            return version.parse("0.0.0")

    def compare_versions(self, latest_version_str: str) -> dict:
        """比较版本号"""
        # 解析版本
        current_ver = self.parse_version(self.current_version)
        latest_ver = self.parse_version(latest_version_str)

        print(f"当前版本: {current_ver}")
        print(f"最新版本: {latest_ver}")

        # 比较版本
        if latest_ver > current_ver:
            return {
                "has_update": True,
                "is_major": latest_ver.major > current_ver.major,
                "is_minor": latest_ver.minor > current_ver.minor,
                "is_patch": latest_ver.micro > current_ver.micro,
                "current_version": str(current_ver),
                "latest_version": str(latest_ver),
                "update_type": self._get_update_type(current_ver, latest_ver)
            }
        elif latest_ver < current_ver:
            # 本地版本比最新版本还新（可能是开发版）
            return {
                "has_update": False,
                "is_dev": True,
                "current_version": str(current_ver),
                "latest_version": str(latest_ver)
            }
        else:
            return {
                "has_update": False,
                "is_latest": True,
                "current_version": str(current_ver),
                "latest_version": str(latest_ver)
            }

    def _get_update_type(self, current: version.Version, latest: version.Version) -> str:
        """获取更新类型"""
        if latest.major > current.major:
            return "major"  # 主要版本更新（可能不兼容）
        elif latest.minor > current.minor:
            return "minor"  # 次要版本更新（新增功能）
        else:
            return "patch"  # 补丁更新（修复bug）


    def check_with_cache(self, force_check: bool = False) -> dict:
        """
        检查更新，使用缓存机制

        缓存策略：
        1. 如果force_check为True，强制检查
        2. 读取缓存文件中的timestamp
        3. 如果读取不到timestamp或超过1天，检查github
        4. 检查github后保存timestamp
        """
        from .config import get_resource_path

        cache_file = get_resource_path("resources/update_cache.json")

        # 1. 检查是否需要跳过缓存
        if force_check:
            signal_bus.log_message.emit("INFO", f"[更新] - 强制检查更新...", {})
            return self._check_and_cache()

        # 2. 检查缓存文件是否存在
        if not cache_file.exists():
            # 确保resources文件夹存在
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            signal_bus.log_message.emit("INFO", f"[更新] - 无缓存，开始检查更新...", {})
            return self._check_and_cache()

        # 3. 读取缓存
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # 检查缓存时间
            timestamp = cache_data.get('timestamp')
            if not timestamp:
                signal_bus.log_message.emit("INFO", f"[更新] - 无时间戳，开始检查更新...", {})
                return self._check_and_cache()

            cache_time = datetime.fromisoformat(timestamp)
            now = datetime.now()

            # 如果缓存超过1天，重新检查
            if now - cache_time > timedelta(days=1):
                signal_bus.log_message.emit("INFO", f"[更新] - 缓存过期（{(now - cache_time).days}天前），重新检查...",
                                            {})
                return self._check_and_cache()

            # 使用缓存数据，但确保current_version是最新的
            update_info = cache_data.get('update_info', {})
            old_current_version = update_info.get('current_version')
            update_info['current_version'] = self.current_version
            
            # 如果缓存中有latest_version，重新比较版本以确保has_update状态正确
            if 'latest_version' in update_info:
                version_comparison = self.compare_versions(update_info['latest_version'])
                # 更新has_update状态，但保留其他缓存信息
                update_info['has_update'] = version_comparison.get('has_update', False)
                if version_comparison.get('is_latest'):
                    update_info['is_latest'] = True
            
            # 如果current_version发生变化，保存更新后的缓存（但不更新时间戳）
            if old_current_version != self.current_version:
                # 保存更新后的缓存，但保留原始时间戳
                cache_data['update_info'] = update_info
                cache_file = get_resource_path("resources/update_cache.json")
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=2, ensure_ascii=False)
            return update_info

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            signal_bus.log_message.emit("ERROR", f"[更新] - 缓存读取失败: {e}，重新检查...", {})
            return self._check_and_cache()


    def _check_and_cache(self) -> dict:
        """检查更新并缓存结果"""
        # 获取最新Release
        release_data = self.get_latest_release()

        if not release_data:
            # 如果获取失败，返回空结果，但仍包含当前版本信息
            result = {
                "has_update": False,
                "error": "无法获取更新信息",
                "current_version": self.current_version,
                "latest_version": self.current_version  # 无法获取最新版本时使用当前版本
            }
            self._save_cache(result)
            return result

        # 比较版本
        version_comparison = self.compare_versions(release_data.get('tag_name', '0.0.0'))

        # 构建完整结果，确保始终包含版本信息
        result = {
            **version_comparison,
            "current_version": self.current_version,
            "latest_version": release_data.get('tag_name', '0.0.0'),
            "release_info": {
                "tag_name": release_data.get('tag_name'),
                "name": release_data.get('name', ''),
                "body": release_data.get('body', ''),
                "html_url": release_data.get('html_url', ''),
                "published_at": release_data.get('published_at', ''),
                "prerelease": release_data.get('prerelease', False),
                "assets_count": len(release_data.get('assets', []))
            },
            "checked_at": datetime.now().isoformat(),
            "repository": f"{self.repo_owner}/{self.repo_name}"
        }

        # 保存到缓存
        self._save_cache(result)
        return result


    def _save_cache(self, update_info: dict):
        """保存检查结果到缓存"""
        from .config import get_resource_path

        # 确保update_info包含正确的current_version
        if 'current_version' not in update_info:
            update_info['current_version'] = self.current_version

        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "update_info": update_info,
            "repository": f"{self.repo_owner}/{self.repo_name}"
        }

        cache_file = get_resource_path("resources/update_cache.json")
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        signal_bus.log_message.emit("INFO", f"[更新] - 缓存保存到: {cache_file}", {})


# ============================================================================
# 项目集成函数
# ============================================================================

def check_for_updates_background():
    """后台检查更新，不阻塞主线程"""
    import threading

    def check():
        try:
            checker = UpdateChecker()
            update_info = checker.check_with_cache()
            if update_info.get('has_update'):
                # 通过信号总线发送更新通知
                signal_bus.update_available.emit(update_info)
        except Exception as e:
            print(f"后台更新检查失败: {e}")

    # 在新线程中检查，避免阻塞启动
    thread = threading.Thread(target=check, daemon=True)
    thread.start()


