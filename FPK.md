# FPK 打包说明（FnOS-terminal）

本文描述本项目的 `bash.fpk` / `bash_v2.fpk` 如何生成，以及 FPK 包内部的基本格式与关键字段含义。

## FPK 文件是什么

本项目的 `*.fpk` 本质是一个 `tar.gz` 压缩包，内容来自 `bash_fpk/` 目录。

FPK 内部包含：
- `manifest`：套件元数据（名称、版本、端口、校验和等）
- `app.tgz`：应用本体压缩包（由 `bash_app/` 目录打包得到）
- `cmd/`：安装/卸载/升级及服务启动脚本
- `config/`：权限/资源限制等配置
- `wizard/`：安装向导表单（可选）
- 图标等资源文件

## 目录结构（打包前）

```
ver2/
├── bash_app/          # 应用本体（运行时文件）
├── bash_fpk/          # FPK 包内容（manifest/cmd/wizard/...）
├── build.sh           # 打包脚本
└── bash.fpk           # 打包输出（build.sh 生成）
```

## 打包流程（build.sh）

打包脚本位于项目根目录的 `build.sh`，核心步骤如下：

1. 读取 `bash_fpk/manifest` 里的 `version`
2. 自动把补丁号 `PATCH` + 1，并写回 `manifest`
3. 从 `bash_app/` 生成 `bash_fpk/app.tgz`
4. 计算 `app.tgz` 的 `sha256`，写入 `manifest` 的 `checksum` 字段
5. 将 `bash_fpk/` 目录整体打成 `bash.fpk`

## 如何生成 bash_v2.fpk

在项目根目录执行：

```bash
./build.sh
cp -f bash.fpk bash_v2.fpk
```

说明：
- `build.sh` 会更新 `bash_fpk/manifest` 的版本号与校验和（所以每次执行都会变更版本）
- `bash_v2.fpk` 只是输出文件名后缀，便于区分发布版本；实际包内容与 `bash.fpk` 相同

## manifest 关键字段

`bash_fpk/manifest` 是 INI 风格的键值对，常用字段：

- `appname`：应用内部标识（本仓库为 `bash`，与历史包兼容）
- `display_name` / `desktop_appname`：桌面入口相关信息
- `install_type = root`：以 root 安装/运行
- `service_port`：服务端口（本项目为 `12701`）
- `checksum`：`app.tgz` 的 sha256（由 `build.sh` 自动更新）

## app.tgz 是什么

`bash_fpk/app.tgz` 由 `bash_app/` 打包得到，包含：
- `bin/`：后端启动文件（如 `terminal_server.py`）
- `ui/`：桌面入口配置与静态资源（xterm.js 等）
- `config/`：权限/资源限制等

安装到 FnOS 后，`bash_app` 的内容会被解包到系统的应用目录中，并由 `bash_fpk/cmd/service-setup` 配置服务启动方式。
