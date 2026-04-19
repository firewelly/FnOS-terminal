# FnOS-terminal

## 简介 | Introduction

FnOS-terminal 是一个基于 GoTTY 的 Web 终端应用，允许用户通过浏览器访问系统命令行界面。

FnOS-terminal is a Web terminal application based on GoTTY, allowing users to access the system command line interface through a web browser.

## 功能特性 | Features

- **Web 终端访问** | Web Terminal Access：通过浏览器直接访问终端，无需 SSH 客户端
- **本地安全监听** | Local Secure Listening：仅监听 127.0.0.1:12701 端口，确保内网安全
- **灵活认证** | Flexible Authentication：支持用户名密码认证，可通过 key.txt 文件配置
- **无缝集成** | Seamless Integration：专为 FnOS 系统设计的应用包格式

## 安装说明 | Installation

### 方法一：FPK 安装包 | Method 1: FPK Package

1. 下载 `bash.fpk` 安装包
2. 在 FnOS 管理界面中导入并安装
3. 安装完成后在应用列表中找到 "FnOS-terminal" 并启动

1. Download the `bash.fpk` installation package
2. Import and install it in the FnOS management interface
3. After installation, find "FnOS-terminal" in the app list and start it

### 方法二：从源码打包 | Method 2: Build from Source

```bash
# 克隆仓库
git clone <repository_url>
cd FnOS-terminal

# 打包 FPK
cd bash_fpk
# 执行打包命令...
```

## 使用说明 | Usage

### 访问终端 | Access Terminal

1. 在 FnOS 应用列表中点击 "FnOS-terminal"
2. 浏览器将打开终端界面
3. 使用系统用户名密码登录

### 配置认证 | Configure Authentication

认证信息由安装向导写入应用数据目录中的 `key.txt`，运行时会优先使用哈希后的凭据格式。

Authentication data is stored in `key.txt` under the application data directory. The runtime prefers hashed credentials when they are available.

如需禁用认证，清空该文件内容；请勿将该文件提交到版本库或打包产物中。

To disable authentication, empty the file content. Do not commit this file into version control or package artifacts.

## 项目结构 | Project Structure

```
FnOS-terminal/
├── bash_fpk/                 # FPK 打包相关文件 | FPK packaging files
│   ├── cmd/                  # 安装/卸载脚本 | Install/Uninstall scripts
│   ├── config/               # 配置文件 | Configuration files
│   ├── wizard/               # 安装向导 | Installation wizard
│   ├── ICON.PNG              # 应用图标 | App icon
│   ├── app.tgz               # 应用压缩包 | Application archive
│   └── manifest              # 应用清单 | App manifest
├── bash_app/                 # 应用本体 | Application files
│   ├── bin/                  # 可执行文件 | Executables
│   │   └── gotty             # GoTTY 二进制文件 | GoTTY binary
│   ├── config/               # 应用配置 | App configuration
│   └── ui/                   # 用户界面 | User interface
│       └── images/           # 图标资源 | Icon resources
└── bash.fpk                  # 打包好的安装包 | Pre-built installation package
```

## 技术栈 | Tech Stack

- **GoTTY**：Web 终端服务器
- **Bash**：安装脚本
- **FnOS FPK**：应用打包格式

## 版本历史 | Changelog

### v1.1.0 (2025-01-31)

- 应用名称更新为 FnOS-terminal
- 更新应用图标
- 优化认证逻辑，支持空 key.txt 时禁用认证
- 调整端口监听为本地 127.0.0.1

### v1.0.9 (2025-01-31)

- 修复空 key.txt 仍需认证的问题
- 新增认证禁用功能

### v1.0.6 (2025-01-31)

- 调整为仅本机监听端口
- 通过系统路由转发实现外网访问

### v1.0.4 (2025-01-31)

- 修复 service-setup 脚本语法错误
- 优化证书生成逻辑

## 许可证 | License

本项目仅供学习和个人使用。

This project is for learning and personal use only.

## 作者 | Author

- **FnOS Community** - [FnOS 社区](https://club.fnnas.com/)
