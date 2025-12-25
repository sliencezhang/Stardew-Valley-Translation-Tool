"""
星露谷物语翻译工具 - 更新检查模块
检查GitHub仓库是否有新版本发布
"""

import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
from packaging import version
import webbrowser
import os
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
        带缓存的更新检查
        
        Args:
            force_check: 是否强制检查（忽略缓存）
        
        缓存策略：
        1. 如果force_check为True，强制检查
        2. 读取缓存文件中的timestamp
        3. 如果读取不到timestamp或超过7天，检查github
        4. 检查github后保存timestamp
        5. 新增：检查当前版本与缓存中的版本是否一致，如果不一致说明已更新，重新检查
        """
        from .path_utils import (get_readable_resource_path, get_resource_path, 
                           is_frozen, is_nuitka_onefile)
        
        cache_file = get_readable_resource_path("update_cache.json")
        env = "打包环境" if (is_frozen() or is_nuitka_onefile()) else "开发环境"
        
        # 1. 检查是否需要跳过缓存
        if force_check:
            signal_bus.log_message.emit("INFO", f"[更新] {env} - 强制检查更新...", {})
            return self._check_and_cache()
        
        # 2. 检查缓存文件是否存在
        if not cache_file.exists():
            # 确保用户目录的resources文件夹存在
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            signal_bus.log_message.emit("INFO", f"[更新] {env} - 无缓存，开始检查更新...", {})
            return self._check_and_cache()
        
        # 3. 读取缓存
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            update_info = cache_data.get('update_info', {})
            cached_current_version = update_info.get('current_version')
            cached_latest_version = update_info.get('latest_version')
            
            # 检查缓存中的当前版本是否与实际版本一致
            if cached_current_version and cached_current_version != self.current_version:
                signal_bus.log_message.emit("INFO", f"[更新] {env} - 检测到版本变化：{cached_current_version} -> {self.current_version}，重新检查更新", {})
                # 版本发生变化，需要重新检查更新
                return self._check_and_cache()
            
            # 检查版本一致性
            if cached_latest_version:
                # 如果当前版本等于缓存中的最新版本，说明已经是最新版本
                if self.parse_version(self.current_version) >= self.parse_version(cached_latest_version):
                    signal_bus.log_message.emit("INFO", f"[更新] {env} - 当前版本{self.current_version}已是最新，清除更新标记", {})
                    # 更新缓存为无更新状态，确保current_version正确
                    no_update_result = {
                        "has_update": False, 
                        "is_latest": True,
                        "current_version": self.current_version,
                        "latest_version": cached_latest_version
                    }
                    self._save_cache(no_update_result)
                    return no_update_result
            
            # 检查缓存时间
            cache_time = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01'))
            now = datetime.now()
            
            # 如果缓存超过7天，重新检查
            if now - cache_time > timedelta(days=7):
                signal_bus.log_message.emit("INFO", f"[更新] {env} - 缓存过期，重新检查...", {})
                return self._check_and_cache()
            
            # 使用缓存，但确保current_version是最新的
            update_info['current_version'] = self.current_version
            signal_bus.log_message.emit("INFO", f"[更新] {env} - 使用缓存数据...", {})
            return update_info
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            signal_bus.log_message.emit("ERROR", f"[更新] {env} - 缓存读取失败: {e}，重新检查...", {})
            return self._check_and_cache()
    
    def _get_cache_file(self) -> Path:
        """获取缓存文件路径（只使用resources目录）"""
        from .path_utils import get_resource_path
        return get_resource_path("update_cache.json")
    
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
        from .path_utils import get_writable_resource_path
        
        # 确保update_info包含正确的current_version
        if 'current_version' not in update_info:
            update_info['current_version'] = self.current_version
        
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "update_info": update_info,
            "repository": f"{self.repo_owner}/{self.repo_name}"
        }
        
        from .path_utils import get_writable_resource_path, is_frozen, is_nuitka_onefile
        
        cache_file = get_writable_resource_path("update_cache.json")
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        env = "打包环境" if (is_frozen() or is_nuitka_onefile()) else "开发环境"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            signal_bus.log_message.emit("INFO", f"[更新] {env}，缓存保存到: {cache_file}", {})
        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"[更新] 缓存保存失败: {e}", {})
    
    def display_update_info(self, update_info: dict):
        """显示更新信息"""
        if not update_info.get('has_update'):
            if update_info.get('is_latest'):
                print("已经是最新版本！")
            elif update_info.get('is_dev'):
                print("当前是开发版本")
            else:
                print("无需更新")
            return
        
        # 有更新时的显示
        print("\n" + "="*60)
        print("发现新版本！")
        print("="*60)
        
        # 版本信息
        print(f"当前版本: {update_info['current_version']}")
        print(f"最新版本: {update_info['latest_version']}")
        
        # 更新类型
        update_type = update_info.get('update_type', 'patch')
        type_emojis = {
            "major": "主要更新（可能包含不兼容变更）",
            "minor": "功能更新",
            "patch": "修复更新"
        }
        print(f"更新类型: {type_emojis.get(update_type, '更新')}")
        
        # Release信息
        release = update_info.get('release_info', {})
        if release.get('name'):
            print(f"发布名称: {release['name']}")
        
        if release.get('published_at'):
            pub_date = release['published_at'][:10]  # 只取日期部分
            print(f"发布时间: {pub_date}")
        
        # 更新内容
        if release.get('body'):
            body = release['body'].strip()
            # 限制显示长度
            if len(body) > 500:
                body = body[:500] + "..."
            print(f"\n更新内容:")
            print("-"*40)
            print(body)
            print("-"*40)
        
        # 下载信息 - 使用配置的蓝奏云链接
        from core.config import config
        print(f"\n下载链接: {config.update_download_url}")
        print(f"下载密码: {config.update_download_password}")
        
        print("="*60)
        
        # 询问用户是否打开下载页面
        try:
            response = input("\n是否打开下载页面？(y/N): ").strip().lower()
            if response == 'y':
                webbrowser.open(config.update_download_url)
                print("已打开浏览器...")
                print(f"下载密码: {config.update_download_password}")
        except EOFError:
            # 非交互式环境，直接显示信息
            print(f"\n下载链接: {config.update_download_url}")
            print(f"下载密码: {config.update_download_password}")
    
    def check_and_notify(self, force_check: bool = False):
        """检查并通知的主方法"""
        print(f"\n检查 {self.repo_owner}/{self.repo_name} 的更新...")
        
        # 检查更新
        update_info = self.check_with_cache(force_check)
        
        # 显示结果
        self.display_update_info(update_info)
        
        return update_info


# ============================================================================
# 项目集成函数
# ============================================================================

def check_for_updates():
    """检查更新的便捷函数，可在应用启动时调用"""
    checker = UpdateChecker()
    return checker.check_and_notify()

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

def get_update_info():
    """获取更新信息，不显示通知"""
    checker = UpdateChecker()
    return checker.check_with_cache()

