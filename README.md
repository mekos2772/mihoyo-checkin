# 米哈游签到工具

一款支持原神、崩坏：星穹铁道、绝区零每日自动签到的工具，采用现代化 WinUI3 风格界面。
由claude 4.5编写

## ✨ 功能特性

- 🎮 **多游戏支持** - 原神、星穹铁道、绝区零一键签到
- 👥 **多账户管理** - 支持多个米游社账户切换
- ⏰ **定时签到** - 设置每日自动签到时间
- 🚀 **开机自启** - 支持 Windows 开机自动运行
- 🎨 **现代界面** - WinUI3 风格，支持亮色/暗色主题
- 📱 **扫码登录** - 使用米游社 APP 扫码安全登录

## 📸 界面预览

程序采用现代化设计，包含以下页面：
- 账户管理 - 添加/删除/切换账户
- 手动签到 - 一键签到所有游戏
- 签到日志 - 查看历史签到记录
- 定时设置 - 配置自动签到时间
- 系统设置 - 主题切换、开机自启等

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Windows 10/11

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行程序

```bash
python main.py
```

## 📦 依赖说明

- **flet** - 现代化 GUI 框架（WinUI3 风格）
- **requests** - HTTP 请求库
- **qrcode** - 二维码生成
- **Pillow** - 图像处理

## 📁 项目结构

```
├── main.py                 # 程序入口
├── requirements.txt        # 依赖列表
└── src/
    ├── core/               # 核心逻辑
    │   ├── checkin.py      # 签到功能
    │   ├── account_manager.py  # 账户管理
    │   └── scheduler.py    # 定时任务
    └── ui/
        └── app.py          # 用户界面
```

## 🔐 安全说明

- 账户信息仅保存在本地
- 使用官方 API，安全可靠
- 开源代码，可自行审查

## 📄 许可证

MIT License

## 🙏 致谢

- [Flet](https://flet.dev/) - 优秀的 Python GUI 框架
- [米游社](https://www.miyoushe.com/) - 官方社区
