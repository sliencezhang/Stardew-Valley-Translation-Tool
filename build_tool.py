#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
星露谷翻译工具 - 自动打包脚本
作者：自动生成
版本：1.0.0

功能：
1. 使用Nuitka打包为单文件或独立目录
2. 自动设置Visual Studio环境变量
3. 清理旧构建文件
4. 验证打包结果
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

class BuildTool:
    """打包工具类"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.vs_path = Path(r"D:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat")
        
        # 颜色代码（Windows CMD）
        self.COLORS = {
            'reset': '\033[0m',
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m'
        }
    
    def print_color(self, text, color='reset'):
        """彩色打印"""
        # 在Windows上禁用颜色代码以避免编码问题
        print(text)
    
    def print_header(self, title):
        """打印标题"""
        self.print_color("\n" + "=" * 60, 'cyan')
        self.print_color(f" {title}", 'cyan')
        self.print_color("=" * 60, 'cyan')
    
    def check_prerequisites(self):
        """检查前提条件"""
        self.print_header("检查前提条件")
        
        checks = []
        
        # 1. 检查Visual Studio
        if self.vs_path.exists():
            self.print_color(f"✅ Visual Studio 2022: {self.vs_path}", 'green')
            
            # 额外检查编译器是否可用
            try:
                # 尝试运行vcvarsall.bat并检查cl.exe
                # 使用cmd.exe来执行批处理文件
                test_cmd = f'cmd /c "call \"{self.vs_path}\" x64 && cl"'
                result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=10)
                if result.returncode != 0 and ('Microsoft (R) C/C++ Optimizing Compiler' in result.stderr or 
                                              'Microsoft (R) C/C++ Optimizing Compiler' in result.stdout):
                    self.print_color("✅ C/C++编译器可用", 'green')
                    checks.append(True)
                else:
                    self.print_color("⚠️  C/C++编译器检查结果异常", 'yellow')
                    if result.stdout:
                        self.print_color(f"   输出: {result.stdout[:100]}", 'yellow')
                    if result.stderr:
                        self.print_color(f"   错误: {result.stderr[:100]}", 'yellow')
                    checks.append(True)  # 仍然尝试继续
            except Exception as e:
                self.print_color(f"⚠️  编译器检查失败: {e}", 'yellow')
                checks.append(True)  # 仍然尝试继续
        else:
            self.print_color(f"❌ Visual Studio未找到: {self.vs_path}", 'red')
            self.print_color("   请确保Visual Studio 2022 BuildTools已安装到D盘", 'yellow')
            checks.append(False)
        
        # 2. 检查Nuitka
        try:
            # 使用utf-8编码避免GBK问题
            result = subprocess.run(['nuitka', '--version'], capture_output=True, text=True, encoding='utf-8', errors='ignore', shell=True)
            
            if result.returncode == 0:
                version_line = result.stdout.splitlines()[0] if result.stdout else "未知版本"
                self.print_color(f"✅ Nuitka: {version_line}", 'green')
                checks.append(True)
            else:
                self.print_color("❌ Nuitka未安装或不可用", 'red')
                self.print_color("   安装: pip install nuitka", 'yellow')
                checks.append(False)
        except (FileNotFoundError, subprocess.CalledProcessError):
            self.print_color("❌ Nuitka未安装", 'red')
            self.print_color("   安装: pip install nuitka", 'yellow')
            checks.append(False)
        
        # 3. 检查主程序
        main_py = self.project_root / 'main.py'
        if main_py.exists():
            self.print_color(f"✅ 主程序: {main_py.name}", 'green')
            checks.append(True)
        else:
            self.print_color(f"❌ 主程序未找到: {main_py}", 'red')
            checks.append(False)
        
        # 4. 检查资源文件
        resources = [
            self.project_root / 'resources' / 'icons' / 'logo.ico',
            self.project_root / 'resources' / 'default_prompts.json',
            self.project_root / 'resources' / 'terminology.json'
        ]
        
        for resource in resources:
            if resource.exists():
                self.print_color(f"✅ 资源: {resource.relative_to(self.project_root)}", 'green')
            else:
                self.print_color(f"⚠️  资源缺失: {resource.relative_to(self.project_root)}", 'yellow')
        
        return all(checks)
    
    def clean_old_builds(self, output_dir):
        """清理旧构建文件"""
        self.print_header("清理旧构建")
        
        if output_dir.exists():
            try:
                shutil.rmtree(output_dir)
                self.print_color(f"✅ 已删除: {output_dir}", 'green')
            except Exception as e:
                self.print_color(f"⚠️  清理失败: {e}", 'yellow')
        else:
            self.print_color(f"✅ 无需清理: {output_dir} 不存在", 'green')
    
    def build_onefile(self, output_dir):
        """构建单文件版本"""
        self.print_header("构建单文件版本")
        
        # Nuitka命令
        cmd = [
            'nuitka',
            '--standalone',
            '--onefile',
            '--windows-console-mode=disable',
            '--enable-plugin=pyside6',
            f'--windows-icon-from-ico={self.project_root / "resources" / "icons" / "logo.ico"}',
            f'--include-data-dir={self.project_root / "resources"}=resources',
            f'--output-dir={output_dir}',
            str(self.project_root / 'main.py')
        ]
        
        self.print_color("执行命令:", 'blue')
        self.print_color(' '.join(cmd), 'yellow')
        
        try:
            self.print_color("\n开始编译...（这需要一些时间）", 'cyan')
            # 直接运行命令，Nuitka应该能自动找到编译器
            # 使用实时输出而不是捕获全部，这样可以更好地监控进度
            process = subprocess.Popen(' '.join(cmd), shell=True, stdout=subprocess.PIPE, 
                                     stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
            
            # 实时显示输出
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    # 只显示重要信息，避免过多输出
                    if any(keyword in output for keyword in ['Successfully created', 'Error:', 'WARNING:', 'Nuitka:', 'Nuitka-Options']):
                        self.print_color(output.strip(), 'cyan')
            
            # 获取返回码
            return_code = process.poll()
            
            if return_code == 0:
                self.print_color("✅ 单文件构建成功！", 'green')
                
                # 检查生成的文件
                # Nuitka应该直接在输出目录创建main.exe
                exe_file = output_dir / 'main.exe'
                
                if exe_file.exists():
                    size_mb = exe_file.stat().st_size / (1024 * 1024)
                    self.print_color(f"📦 生成文件: {exe_file}", 'green')
                    self.print_color(f"📏 文件大小: {size_mb:.2f} MB", 'green')
                    return True
                else:
                    # 调试：列出输出目录的内容
                    self.print_color(f"⚠️  未找到文件: {exe_file}", 'yellow')
                    self.print_color(f"   输出目录内容:", 'yellow')
                    try:
                        if output_dir.exists():
                            for item in output_dir.iterdir():
                                self.print_color(f"    - {item.name} ({'文件' if item.is_file() else '目录'})", 'yellow')
                        else:
                            self.print_color(f"    - 输出目录不存在: {output_dir}", 'yellow')
                    except Exception as e:
                        self.print_color(f"    - 列出目录时出错: {e}", 'yellow')
                    
                    # 检查其他可能的位置
                    other_locations = [
                        self.project_root / 'main.exe',
                        self.project_root / 'main.dist' / 'main.exe',
                        output_dir / 'main.dist' / 'main.exe'
                    ]
                    
                    for location in other_locations:
                        if location.exists():
                            self.print_color(f"   ✅ 在其他位置找到: {location}", 'green')
                            size_mb = location.stat().st_size / (1024 * 1024)
                            self.print_color(f"   📏 文件大小: {size_mb:.2f} MB", 'green')
                            
                            # 移动到输出目录
                            output_dir.mkdir(parents=True, exist_ok=True)
                            target_file = output_dir / 'main.exe'
                            import shutil
                            shutil.move(str(location), str(target_file))
                            self.print_color(f"   📦 已移动到: {target_file}", 'green')
                            return True
                    
                    self.print_color("❌ 构建成功但未找到生成的可执行文件", 'red')
                    return False
            else:
                self.print_color("❌ 构建失败", 'red')
                self.print_color(f"错误输出:\n{result.stderr}", 'red')
                return False
                
        except Exception as e:
            self.print_color(f"❌ 执行失败: {e}", 'red')
            return False
    
    def build_standalone(self, output_dir):
        """构建独立目录版本"""
        self.print_header("构建独立目录版本")
        
        # Nuitka命令
        cmd = [
            'nuitka',
            '--standalone',
            '--windows-console-mode=disable',
            '--enable-plugin=pyside6',
            f'--windows-icon-from-ico={self.project_root / "resources" / "icons" / "logo.ico"}',
            f'--include-data-dir={self.project_root / "resources"}=resources',
            f'--output-dir={output_dir}',
            str(self.project_root / 'main.py')
        ]
        
        self.print_color("执行命令:", 'blue')
        self.print_color(' '.join(cmd), 'yellow')
        
        try:
            self.print_color("\n开始编译...（这需要一些时间）", 'cyan')
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                self.print_color("✅ 独立目录构建成功！", 'green')
                
                # 检查生成的文件
                dist_dir = output_dir / 'main.dist'
                if dist_dir.exists():
                    total_size = sum(f.stat().st_size for f in dist_dir.rglob('*') if f.is_file())
                    size_mb = total_size / (1024 * 1024)
                    file_count = len(list(dist_dir.rglob('*')))
                    
                    self.print_color(f"📦 生成目录: {dist_dir}", 'green')
                    self.print_color(f"📏 总大小: {size_mb:.2f} MB", 'green')
                    self.print_color(f"📄 文件数量: {file_count}", 'green')
                return True
            else:
                self.print_color("❌ 构建失败", 'red')
                self.print_color(f"错误输出:\n{result.stderr}", 'red')
                return False
                
        except Exception as e:
            self.print_color(f"❌ 执行失败: {e}", 'red')
            return False
    
    def create_zip_package(self, source_dir, package_name):
        """创建ZIP发布包"""
        self.print_header("创建发布包")
        
        zip_path = self.project_root / f"{package_name}.zip"
        
        try:
            # 使用Python内置zipfile
            import zipfile
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, self.project_root)
                        zipf.write(file_path, arcname)
            
            size_mb = zip_path.stat().st_size / (1024 * 1024)
            self.print_color(f"✅ ZIP包创建成功: {zip_path}", 'green')
            self.print_color(f"📦 包大小: {size_mb:.2f} MB", 'green')
            return True
            
        except Exception as e:
            self.print_color(f"❌ 创建ZIP失败: {e}", 'red')
            return False
    
    def verify_build(self, build_path):
        """验证构建结果"""
        self.print_header("验证构建")
        
        if isinstance(build_path, Path):
            if build_path.is_file():  # 单文件
                if build_path.exists():
                    self.print_color(f"✅ 可执行文件存在: {build_path}", 'green')
                    
                    # 检查文件签名（如果有）
                    try:
                        import pefile
                        pe = pefile.PE(str(build_path))
                        self.print_color(f"✅ PE文件格式有效", 'green')
                        self.print_color(f"   架构: {'64位' if pe.FILE_HEADER.Machine == 0x8664 else '32位'}", 'cyan')
                    except:
                        self.print_color("⚠️  无法验证PE格式", 'yellow')
                    
                    return True
                else:
                    self.print_color(f"❌ 文件不存在: {build_path}", 'red')
                    return False
            else:  # 目录
                if build_path.exists():
                    exe_file = build_path / 'main.exe'
                    if exe_file.exists():
                        self.print_color(f"✅ 主程序存在: {exe_file}", 'green')
                        
                        # 检查关键文件
                        key_files = [
                            build_path / 'PySide6',
                            build_path / 'resources',
                            build_path / 'python312.dll'
                        ]
                        
                        for key_file in key_files:
                            if key_file.exists():
                                self.print_color(f"✅ 关键文件: {key_file.name}", 'green')
                            else:
                                self.print_color(f"⚠️  缺失文件: {key_file.name}", 'yellow')
                        
                        return True
                    else:
                        self.print_color(f"❌ 主程序不存在: {exe_file}", 'red')
                        return False
                else:
                    self.print_color(f"❌ 目录不存在: {build_path}", 'red')
                    return False
        return False
    
    def run(self, mode='onefile', clean=True, create_zip=False):
        """运行打包流程"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if mode == 'onefile':
            output_dir = self.project_root / f"build_onefile_{timestamp}"
            build_method = self.build_onefile
            verify_path = output_dir / 'main.exe'
        else:
            output_dir = self.project_root / f"build_standalone_{timestamp}"
            build_method = self.build_standalone
            verify_path = output_dir / 'main.dist'
        
        # 1. 检查前提条件
        if not self.check_prerequisites():
            self.print_color("❌ 前提条件检查失败，停止打包", 'red')
            return False
        
        # 2. 清理旧构建
        if clean:
            self.clean_old_builds(output_dir)
        
        # 3. 构建
        if not build_method(output_dir):
            return False
        
        # 4. 验证
        if not self.verify_build(verify_path):
            return False
        
        # 5. 创建ZIP包（可选）
        if create_zip:
            package_name = f"StardewTranslationTool_{mode}_{timestamp}"
            if mode == 'onefile':
                self.create_zip_package(output_dir, package_name)
            else:
                self.create_zip_package(verify_path, package_name)
        
        self.print_header("打包完成")
        self.print_color("🎉 所有步骤完成！", 'green')
        
        if mode == 'onefile':
            self.print_color(f"\n📦 单文件位置: {verify_path}", 'cyan')
            self.print_color("   直接双击运行即可", 'yellow')
        else:
            self.print_color(f"\n📁 独立目录位置: {verify_path}", 'cyan')
            self.print_color("   运行: 双击 main.dist/main.exe", 'yellow')
        
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='星露谷翻译工具打包脚本')
    parser.add_argument('--mode', choices=['onefile', 'standalone'], default='onefile',
                       help='打包模式: onefile(单文件) 或 standalone(独立目录)')
    parser.add_argument('--no-clean', action='store_true',
                       help='不清理旧构建文件')
    parser.add_argument('--zip', action='store_true',
                       help='创建ZIP发布包')
    parser.add_argument('--version', action='version', version='1.0.0')
    
    args = parser.parse_args()
    
    print("🌟 星露谷翻译工具 - 自动打包脚本")
    print("=" * 50)
    
    tool = BuildTool()
    
    success = tool.run(
        mode=args.mode,
        clean=not args.no_clean,
        create_zip=args.zip
    )
    
    if success:
        print("\n✅ 打包流程完成！")
        return 0
    else:
        print("\n❌ 打包流程失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())