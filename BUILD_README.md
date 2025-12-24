# 星露谷翻译工具 - 打包使用指南

## 📦 打包脚本说明

已创建自动打包脚本 `build_tool.py`，你可以使用它轻松打包项目。

## 🚀 快速开始

### 1. 单文件打包（推荐）
```bash
python build_tool.py --mode onefile
```
生成：`build_onefile_时间戳/main.exe`（约24MB）

### 2. 独立目录打包
```bash
python build_tool.py --mode standalone
```
生成：`build_standalone_时间戳/main.dist/`（约81MB）

### 3. 创建ZIP发布包
```bash
python build_tool.py --mode onefile --zip
```
生成：`StardewTranslationTool_onefile_时间戳.zip`

## 🔧 完整参数

```bash
# 查看帮助
python build_tool.py --help

# 参数说明
--mode {onefile,standalone}  打包模式（默认：onefile）
--no-clean                   不清理旧构建文件
--zip                        创建ZIP发布包
--version                    显示版本
```

## 📊 模式对比

### 单文件模式 (`--mode onefile`)
- **大小**: ~24MB
- **文件**: 单个 `main.exe`
- **优点**: 分发方便、保护性好、外观专业
- **缺点**: 启动稍慢、临时文件多

### 独立目录模式 (`--mode standalone`)
- **大小**: ~81MB
- **文件**: `main.dist/` 目录包含所有DLL
- **优点**: 启动快、调试方便、更新灵活
- **缺点**: 文件分散、容易被修改

## 🛠️ 手动打包命令

如果你需要手动控制，可以使用以下命令：

### 单文件打包
```powershell
$vsPath = "D:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
cmd.exe /c "call `"$vsPath`" x64 && nuitka --standalone --onefile --windows-console-mode=disable --enable-plugin=pyside6 --windows-icon-from-ico=`"resources/icons/logo.ico`" --include-data-dir=resources=resources --output-dir=dist main.py"
```

### 独立目录打包
```powershell
$vsPath = "D:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
cmd.exe /c "call `"$vsPath`" x64 && nuitka --standalone --windows-console-mode=disable --enable-plugin=pyside6 --windows-icon-from-ico=`"resources/icons/logo.ico`" --include-data-dir=resources=resources --output-dir=dist main.py"
```

## 📁 项目结构要求

打包前确保项目结构完整：
```
项目根目录/
├── main.py                    # 主程序
├── build_tool.py             # 打包脚本
├── core/                     # 核心模块
├── ui/                       # 用户界面
├── resources/                # 资源文件
│   ├── icons/logo.ico       # 程序图标
│   ├── default_prompts.json # 默认提示
│   └── terminology.json     # 术语表
└── requirements.txt         # Python依赖
```

## ⚙️ 系统要求

### 必须安装：
1. **Python 3.8+**（已在.venv中）
2. **Visual Studio 2022 BuildTools**（已安装到D盘）
3. **Nuitka**（已安装：`pip install nuitka`）

### 环境变量：
- Visual Studio路径：`D:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\`
- 脚本会自动设置MSVC环境变量

## 🔍 常见问题

### 1. 打包失败
```bash
# 检查前提条件
python build_tool.py --mode onefile --no-clean
```

### 2. 文件太大
- 单文件模式已自动压缩
- 可以尝试移除不必要的资源文件

### 3. 启动报错
- 确保所有资源文件存在
- 检查图标文件路径
- 在独立目录模式下运行测试

### 4. 防病毒软件误报
- 单文件模式可能被误报
- 可以添加数字签名（如有）
- 或使用独立目录模式

## 🎯 发布流程

### 步骤1：测试打包
```bash
python build_tool.py --mode onefile
```

### 步骤2：验证运行
1. 打开 `build_onefile_时间戳/`
2. 双击 `main.exe`
3. 测试所有功能

### 步骤3：创建发布包
```bash
python build_tool.py --mode onefile --zip
```

### 步骤4：分发
- 发送 `StardewTranslationTool_onefile_时间戳.zip` 给用户
- 用户解压后双击 `main.exe` 即可运行

## 📝 脚本功能

`build_tool.py` 自动完成：
1. ✅ 检查Visual Studio安装
2. ✅ 检查Nuitka和依赖
3. ✅ 清理旧构建文件
4. ✅ 设置MSVC环境变量
5. ✅ 执行Nuitka打包
6. ✅ 验证打包结果
7. ✅ 创建ZIP发布包（可选）
8. ✅ 彩色输出和错误处理

## 🔄 更新维护

### 添加新资源文件
1. 将文件放入 `resources/` 目录
2. 打包时会自动包含

### 修改图标
1. 替换 `resources/icons/logo.ico`
2. 重新打包即可

### 更新依赖
1. 修改 `requirements.txt`
2. 重新安装依赖：`pip install -r requirements.txt`
3. 重新打包

## 📞 技术支持

如果遇到问题：
1. 运行 `python build_tool.py --mode onefile --no-clean`
2. 查看错误输出
3. 确保Visual Studio路径正确
4. 检查资源文件是否存在

## 🎉 完成！

现在你可以轻松打包星露谷翻译工具了。建议使用单文件模式分发给用户。

**打包命令总结：**
```bash
# 给用户的版本（推荐）
python build_tool.py --mode onefile --zip

# 开发测试版本
python build_tool.py --mode standalone
```

生成的文件可以直接分发给用户，无需安装Python或任何依赖！