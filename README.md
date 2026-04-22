# VoxCPM2 GUI

基于 **PyQt-Fluent-Widgets** 构建的 VoxCPM2 语音合成模型图形界面，提供现代化的 Windows 原生风格操作体验。

---

## 功能特性

- **语音合成**：文本到语音生成，支持 30+ 种语言及方言
- **音色库管理**：保存、加载、管理自定义音色预设
- **标签系统**：为历史记录和音色添加标签，支持分类筛选
- **生成历史**：查看和管理所有语音生成记录
- **实时预览**：内置音频播放器，支持播放/暂停/进度控制
- **服务器控制**：一键启动/停止后端推理服务
- **主题同步**：自动跟随 Windows 系统明暗主题切换

---

## 项目结构

```
voxcpm-fluent-gui/
├── app/
│   ├── common/          # 公共模块
│   │   ├── config.py    # 配置管理
│   │   ├── audio_manager.py    # 音频播放器管理
│   │   ├── signal_bus.py       # 全局信号总线
│   │   └── style_sheet.py      # 样式管理
│   ├── view/            # 界面模块
│   │   ├── main_window.py           # 主窗口
│   │   ├── synthesis_interface.py   # 语音合成界面
│   │   ├── voice_library_interface.py # 音色库管理
│   │   ├── history_interface.py     # 历史记录
│   │   ├── tag_manager_interface.py # 标签管理
│   │   ├── setting_interface.py     # 设置界面
│   │   └── about_interface.py       # 关于页面
│   └── core/            # 核心功能
├── assets/              # 资源文件（图标、字体等）
├── config/              # 配置文件
├── outputs/             # 输出文件目录
├── app.py               # 入口文件
└── inference_server.py  # FastAPI 推理服务器
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| **GUI 框架** | PyQt5 + PyQt-Fluent-Widgets |
| **后端服务** | FastAPI + Uvicorn |
| **音频处理** | PySide6.QtMultimedia |
| **模型推理** | PyTorch 2.5 + CUDA 12.1 |
| **打包工具** | PyInstaller / Nuitka |

---

## 快速开始

### 1. 安装依赖

```bash
cd voxcpm-fluent-gui
pip install -r requirements.txt
```

### 2. 运行 GUI

```bash
python app.py
```

### 3. 打包为 exe

```bash
pyinstaller VoxCPM2_GUI.spec
```

---

## 系统要求

- **操作系统**：Windows 10/11
- **显卡**：NVIDIA GPU（GTX 900 系列及以上，显存 ≥ 6GB）
- **驱动版本**：NVIDIA Driver ≥ 525.60
- **后端环境**：voxcpm2_env（Python 3.10 + PyTorch 2.5.1+cu121）

---

## 项目地址

- **VoxCPM2 模型**：https://github.com/OpenBMB/VoxCPM2
- **PyQt-Fluent-Widgets**：https://github.com/zhiyiYo/PyQt-Fluent-Widgets

---

## License

Apache-2.0
