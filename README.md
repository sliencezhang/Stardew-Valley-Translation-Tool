# 星露谷翻译工具 v1.0

专业的星露谷游戏文本翻译工具，支持智能翻译、增量翻译、质量检查等功能。

使用教程：https://www.bilibili.com/video/BV15NqbBAEQN

## 🌟 功能特点

- 🤖 **智能翻译**：支持多种翻译API，自动识别和保护游戏变量
- 📚 **增量翻译**：智能跳过已翻译内容，提高效率
- 🔍 **质量检查**：检查中英混杂、变量一致性等问题
- ⚙️ **配置菜单翻译**：专门处理模组配置文件
- ✏️ **手动翻译**：提供友好的手动翻译界面
- 📋 **术语管理**：支持自定义术语表，保证翻译一致性
- 💾 **缓存机制**：自动缓存翻译结果，避免重复翻译
- 🎨 **现代化界面**：基于PySide6的现代化GUI界面
- 🌙 **主题切换**：支持日间/夜间主题切换
- 📊 **进度显示**：实时显示翻译进度和统计信息

## 📦 安装方法

### 方法1：使用可执行文件（推荐）

1. 下载最新版本的 `Stardew Valley Translation Tool.exe`（约25MB）
2. 双击运行即可使用，无需安装Python环境

### 方法2：从源码安装

1. 确保已安装 Python 3.8 或更高版本
2. 克隆或下载本项目
3. 创建虚拟环境（推荐）：
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
4. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
5. 运行程序：
   ```bash
   python main.py
   ```

## 🚀 快速开始

1. **创建项目**：点击"新建项目"，选择项目文件夹
2. **配置API**：在设置中配置翻译API密钥
3. **开始翻译**：选择相应的翻译功能开始翻译
4. **准备文件**：将需要翻译的文件放入软件界面对应的拖选框
5. **质量检查**：翻译完成后使用质量检查功能
6. **导出结果**：翻译结果保存在output文件夹中


## 📁 项目结构

```
项目文件夹/
├── en/          # 英文原文文件
│   └── default.json
├── zh/          # 中文参考文件
│   └── zh.json
├── output/      # 翻译输出文件
│   └── zh.json
├── cache/       # 翻译缓存
│   └── translation_cache.json
├── manifest/    # 模组清单文件
└── project_config.json  # 项目配置文件
```

## 🎯 使用技巧

### 智能翻译
- 自动识别游戏变量格式
- 支持术语表，确保关键术语翻译一致
- 可配置翻译提示词，提高翻译质量

### 质量检查
- 检查中英混杂问题
- 检查未翻译问题
- 验证变量一致性
- 提供一键修复功能以及手动编辑功能

### 手动翻译
- 高亮显示需要翻译的内容
- 支持原文和译文对照显示

## ⚙️ 高级配置

### 翻译API配置
在设置中可以配置：
- API密钥
- 每批翻译数量
- 翻译温度参数

### 术语管理
- 支持导入/导出术语表
- 采用AC自动机，毫秒级匹配万条数据

### 缓存设置
- 支持清理缓存

## 🔨 开发指南

### 环境要求
- Python 3.8+
- PySide6
- requests
- pandas

### 构建可执行文件
- 需要安装Microsoft Visual Studio c++ 2022
- 或使用pyinstall打包，文件体积大一倍

使用 Nuitka 打包为单文件：
```bash
nuitka --standalone --onefile --windows-console-mode=disable --windows-disable-console --enable-plugin=pyside6 --windows-icon-from-ico="resources/icons/logo.ico" --include-data-dir=resources=resources --output-dir=dist_onefile main.py
```

或使用自动打包脚本：
```bash
python build_tool.py --mode onefile
```

### 项目结构
```
Stardew Valley Translation Tool/
├── main.py              # 主程序入口
├── core/                # 核心功能模块
│   ├── api_client.py    # API客户端
│   ├── translation_engine.py  # 翻译引擎
│   ├── quality_checker.py     # 质量检查
│   └── ...
├── ui/                  # 用户界面
│   ├── main_window.py   # 主窗口
│   ├── widgets.py       # 自定义控件
│   └── tabs/            # 功能页面
├── resources/           # 资源文件
│   ├── icons/           # 图标
│   ├── img/             # 图片
│   ├── default_prompts.json  # 默认提示词
│   └── terminology.json     # 默认术语表
└── requirements.txt     # 依赖列表
```

## 🐛 常见问题

### Q: 翻译API调用失败怎么办？
A: 检查API密钥是否正确，网络连接是否正常。

### Q: 程序启动失败？
A: 确保Python版本符合要求，所有依赖已正确安装。

### Q: 翻译结果不理想？
A: 清理缓存，尝试调整翻译提示词（一般不需要调整），添加更多术语，或切换到其他翻译API。

### Q: 如何备份项目？
A: 直接复制整个项目文件夹即可，所有配置和缓存都在其中。

## 📝 更新日志

### v1.0
- 全新的现代化界面
- 支持单文件打包，无需安装Python
- 优化翻译引擎，提高翻译质量
- 新增主题切换功能
- 改进质量检查算法


## 🙏 致谢

- 感谢星露谷社区的支持
- 感谢所有翻译API提供商

---

**如果这个工具对你有帮助，请给个⭐️支持一下！**
