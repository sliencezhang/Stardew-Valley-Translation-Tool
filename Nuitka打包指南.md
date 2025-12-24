# Nuitka打包指南

## ✅ 安装状态确认
- **Visual Studio 2022 BuildTools**: 已安装到D盘 ✅
- **MSVC编译器**: 已就绪 ✅  
- **Nuitka打包**: 成功完成 ✅

## 📦 打包结果
- **可执行文件**: `dist_simple\main.dist\main.exe`
- **打包类型**: 独立应用程序（非单文件）
- **包含资源**: 图标、配置文件、Qt插件等

## 🚀 运行方式

### 方法1：直接运行
1. 打开文件资源管理器
2. 导航到 `dist_simple\main.dist\`
3. 双击 `main.exe`

### 方法2：命令行运行
```cmd
cd dist_simple\main.dist
main.exe
```

## 🔧 后续打包命令

### 基本命令（已测试成功）
```powershell
# 设置环境变量
$vsPath = "D:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"

# 运行打包
cmd.exe /c "call `"$vsPath`" x64 && nuitka --standalone --windows-console-mode=disable --enable-plugin=pyside6 --windows-icon-from-ico=`"resources/icons/logo.ico`" --include-data-dir=resources=resources --output-dir=dist_simple main.py"
```

### 单文件打包（需要更长时间）
```powershell
# 单文件版本（编译时间较长）
cmd.exe /c "call `"$vsPath`" x64 && nuitka --standalone --onefile --windows-console-mode=disable --enable-plugin=pyside6 --windows-icon-from-ico=`"resources/icons/logo.ico`" --include-data-dir=resources=resources --output-dir=dist_onefile main.py"
```

### 简化命令脚本
创建 `build.bat`：
```batch
@echo off
call "D:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64
nuitka --standalone --windows-console-mode=disable --enable-plugin=pyside6 --windows-icon-from-ico="resources/icons/logo.ico" --include-data-dir=resources=resources --output-dir=dist main.py
echo 打包完成！
pause
```

## 📁 目录结构说明
```
dist_simple/main.dist/
├── main.exe              # 主程序
├── PySide6/             # Qt库
├── resources/           # 资源文件
│   ├── icons/logo.ico
│   ├── default_prompts.json
│   └── terminology.json
├── certifi/            # SSL证书
├── shiboken6/          # PySide6依赖
└── ...其他依赖库
```

## ⚡ 性能优化选项

### 1. 启用UPX压缩（减小文件大小）
```powershell
nuitka --standalone --lto --enable-plugin=pyside6 ^
  --windows-console-mode=disable ^
  --windows-icon-from-ico="resources/icons/logo.ico" ^
  --include-data-dir=resources=resources ^
  main.py
```

### 2. 使用商业版优化（如果有许可证）
```powershell
nuitka --standalone --commercial ^
  --enable-plugin=pyside6 ^
  main.py
```

## 🔍 常见问题

### 1. 运行时报错缺少DLL
- 确保在 `dist_simple\main.dist\` 目录中运行
- 所有依赖DLL都已包含在该目录

### 2. 图标不显示
- 检查 `resources/icons/logo.ico` 是否存在
- 图标已嵌入到exe文件中

### 3. 打包时间太长
- 使用非单文件模式（`--standalone` 不带 `--onefile`）
- 后续打包会使用缓存，速度更快

### 4. 文件太大
- 使用UPX压缩
- 移除不必要的资源文件
- 使用商业版Nuitka进行更好优化

## 🎯 发布准备

### 1. 清理测试文件
```powershell
# 删除构建缓存
Remove-Item "dist_simple\main.build" -Recurse -Force -ErrorAction SilentlyContinue

# 删除临时文件
Remove-Item "*.pyc" -Force -ErrorAction SilentlyContinue
```

### 2. 创建发布包
```powershell
# 压缩为ZIP
Compress-Archive -Path "dist_simple\main.dist\*" -DestinationPath "StardewTranslationTool_v1.0.zip"
```

### 3. 验证发布包
1. 将ZIP文件复制到其他目录
2. 解压并运行 `main.exe`
3. 测试所有功能是否正常

## 📝 总结
你现在已经成功：
1. ✅ 安装了Visual Studio 2022 BuildTools到D盘
2. ✅ 配置了MSVC编译器环境
3. ✅ 使用Nuitka打包了Python应用程序
4. ✅ 生成了独立的可执行文件

可以随时使用上述命令重新打包或创建发布版本！