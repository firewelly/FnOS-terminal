# FnOS-terminal 开发文档

## 项目概述

**项目名称**: FnOS-terminal
**项目类型**: DSM 套件 (Synology NAS)
**功能描述**: Web 端终端模拟器，支持多标签页、多个并发会话
**技术栈**:
- 前端: HTML + CSS + JavaScript + xterm.js
- 后端: Python 3 + asyncio + WebSocket + PTY

---

## 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| 1.1.0 | 初始提交 | 基础版本，使用简化终端 |
| 2.0.0 | 升级 | 集成 xterm.js，完整终端支持 |
| 2.2.5 | 最新 | 修复密码输入问题，优化用户体验 |

---

## 需求变更记录

### 原始需求 (v1.1.0)
- 简单的 Web 终端
- 单会话支持
- 基础身份验证

### 完整终端需求 (v2.0.0)
1. **完整终端功能**: 支持 ANSI 颜色转义序列
2. **鼠标交互**: 支持鼠标点击和选择
3. **自动调整大小**: 窗口大小变化时自动调整终端尺寸
4. **多标签页**: 支持创建和管理多个终端会话
5. **可点击链接**: 识别并支持点击网页链接
6. **单端口服务**: HTTP 和 WebSocket 共用同一端口 (12701)
7. **自定义 WebSocket 服务器**: 不依赖第三方库 (websockets/aiohttp/tornado)

---

## 技术实现

### 前端架构

#### 核心组件
- **xterm.js**: 终端模拟器核心库
- **xterm-addon-fit**: 自动调整终端尺寸
- **xterm-addon-web-links**: 支持可点击链接

#### 静态文件结构
```
bash_app/ui/static/
├── css/
│   └── xterm.css          # xterm.js 样式
└── js/
    ├── xterm.js           # 终端模拟器核心
    ├── xterm-addon-fit.js # 尺寸自适应
    └── xterm-addon-web-links.js # 链接支持
```

#### HTML/CSS 样式
- 标签栏 (Tab Bar): 深色主题，支持多标签切换
- 终端容器: 全屏显示，黑色背景 (#1e1e1e)
- 登录弹窗: 居中显示，模态对话框

#### JavaScript 类结构
```javascript
class TerminalApp {
    constructor()       // 初始化
    init()              // 设置事件监听
    login()             // 用户认证
    createTab()         // 创建新标签页
    switchToTab(id)     // 切换标签页
    closeTab(id)        // 关闭标签页
    handleResize()      // 处理窗口调整
}
```

### 后端架构

#### 核心模块 (terminal_server.py)

**导入依赖**:
```python
asyncio      # 异步 I/O
json         # JSON 序列化
os           # 系统操作
pty          # 伪终端
select       # I/O 多路复用
signal       # 信号处理
struct       # 二进制打包
sys          # 系统操作
termios      # 终端控制
base64       # Base64 编码
hashlib      # 哈希计算
```

**功能模块**:

1. **静态文件服务**
   - 路径: `/static/`
   - 支持文件类型: .css, .js, .png
   - 安全防护: 防止目录遍历攻击

2. **WebSocket 服务器**
   - 单端口: 12701
   - 自定义协议实现 (无第三方依赖)
   - 帧处理: 握手、发送、接收

3. **会话管理**
   - 会话 ID: UUID v4
   - 会话存储: 字典结构
   - PTY 绑定: 进程 ID + 文件描述符

4. **认证系统**
   - 密钥文件: `/var/packages/bash/var/key.txt`
   - 推荐格式: `sha256:<username>:<password_hash>`
   - 兼容旧格式: 明文 `username + password`
   - 认证方式: WebSocket 消息

5. **消息类型**
   | 类型 | 方向 | 描述 |
   |------|------|------|
   | auth | C→S | 认证请求 |
   | auth_success | S→C | 认证成功 |
   | auth_failed | S→C | 认证失败 |
   | create_session | C→S | 创建会话 |
   | session_created | S→C | 会话创建成功 |
   | session_error | S→C | 会话创建失败 |
   | input | C→S | 终端输入 |
   | output | S→C | 终端输出 |
   | resize | C→S | 调整大小 |
   | close_session | C→S | 关闭会话 |

#### 服务配置

**启动命令**:
```bash
python3 terminal_server.py --address 127.0.0.1 --port 12701
```

**工作目录**: `/var/packages/bash/var`
**日志文件**: `/var/log/apps/bash.log`

### 套件配置 (FPK)

#### 清单文件 (manifest)
```ini
appname         = bash
version         = 2.2.5
desc            = FnOS-terminal：Web 端终端，支持多标签页、多个并发会话。
arch            = x86_64
install_type    = root
service_port    = 12701
desktop_appname = bash.Application
```

#### 权限配置 (config/privilege)
```json
{
    "defaults": {
        "run-as": "root"
    },
    "username": "root",
    "groupname": "root"
}
```

#### 安装向导 (wizard/install)
```json
{
    "stepTitle": "初始化账号密码",
    "items": [
        {
            "type": "text",
            "field": "term_auth_username",
            "label": "输入用户名",
            "rules": {
                "required": false,
                "min": 3,
                "max": 32
            }
        },
        {
            "type": "text",
            "field": "term_auth_password",
            "label": "输入8-32位非纯数字密码",
            "rules": {
                "required": false,
                "min": 8,
                "max": 32,
                "pattern": "^[0-9]*[^0-9]+[0-9]*$"
            }
        }
    ]
}
```

#### 服务安装脚本 (cmd/service-setup)
```bash
SERVICE_COMMAND="python3 ${TRIM_APPDEST}/bin/terminal_server.py --address 127.0.0.1 --port 12701"
```

---

## 关键代码段

### 前端: xterm.js 初始化
```javascript
const term = new Terminal({
    cursorBlink: true,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    fontSize: 14,
    theme: {
        background: '#1e1e1e',
        foreground: '#cccccc',
        selection: '#264f78'
    }
});

const fitAddon = new FitAddon.FitAddon();
term.loadAddon(fitAddon);
term.loadAddon(new WebLinksAddon.WebLinksAddon());

term.open(wrapper);
fitAddon.fit();
```

### 后端: WebSocket 帧发送
```python
async def send_ws_frame(writer, data, opcode=1):
    header = bytearray()
    header.append(0x80 | opcode)
    payload = data.encode('utf-8') if isinstance(data, str) else data
    length = len(payload)
    
    if length < 126:
        header.append(length)
    elif length < 65536:
        header.append(126)
        header.extend(struct.pack('!H', length))
    else:
        header.append(127)
        header.extend(struct.pack('!Q', length))
    
    writer.write(header + payload)
    await writer.drain()
```

### 后端: PTY 会话创建
```python
pid, master_fd = pty.fork()
if pid == 0:
    env = os.environ.copy()
    env['TERM'] = 'xterm-256color'
    os.execvp('login', ['login'])
else:
    session = {'pid': pid, 'fd': master_fd}
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
    sessions[session_id] = session
```

---

## 文件清单

### 项目结构
```
FnOS-terminal/
├── build.sh                    # 打包脚本
├── bash.fpk                    # 生成的套件包
├── bash_app/
│   ├── bin/
│   │   └── terminal_server.py  # 主服务器
│   └── ui/
│       ├── config              # UI 配置
│       ├── images/             # 图标文件
│       │   ├── icon.png
│       │   ├── icon-32.png
│       │   ├── icon-64.png
│       │   └── icon-128.png
│       └── static/             # 静态资源
│           ├── css/xterm.css
│           └── js/
│               ├── xterm.js
│               ├── xterm-addon-fit.js
│               └── xterm-addon-web-links.js
└── bash_fpk/
    ├── manifest                # 套件清单
    ├── cmd/
    │   ├── common              # 通用函数
    │   ├── installer           # 安装脚本
    │   ├── service-setup       # 服务配置
    │   └── ...
    ├── config/
    │   ├── privilege           # 权限配置
    │   └── resource            # 资源限制
    └── wizard/
        └── install             # 安装向导
```

---

## 已知问题与解决方案

### 问题 1: 密码输入框无法输入
**状态**: 已修复
**原因**: 页面加载时密码输入框没有获得焦点
**解决方案**: 添加 `setTimeout(() => passwordInput.focus(), 100)` 自动聚焦

### 问题 2: "本地用户已经存在" 错误
**状态**: 待解决
**描述**: 安装向导输入用户名时 DSM 报错
**可能原因**:
1. DSM 套件中心对认证类字段有特殊解释
2. 字段名可能与 DSM 系统用户创建冲突
**建议**:
- 尝试使用不常见的用户名 (如 `fnbash_admin_xxx`)
- 避免使用 `admin`、`root` 等系统保留用户名

---

## 待办事项

### 高优先级
- [ ] 解决"本地用户已经存在"安装错误
- [ ] 验证图标显示是否正确 (左上角像素应为透明/白色)
- [ ] 测试多标签页功能

### 中优先级
- [ ] 优化终端启动速度
- [ ] 添加会话恢复功能
- [ ] 支持复制粘贴

### 低优先级
- [ ] 添加自定义主题支持
- [ ] 优化移动端体验
- [ ] 添加快捷键配置

---

## 构建与发布

### 打包命令
```bash
./build.sh
```

### 打包流程
1. 读取当前版本 (从 manifest)
2. 增加补丁版本号
3. 更新 manifest 中的版本和校验和
4. 打包 app.tgz (bash_app 目录)
5. 生成最终的 bash.fpk

### 输出文件
- **位置**: `<project-root>/bash.fpk`
- **大小**: ~3.7 MB
- **版本**: 2.2.5

---

## 安装说明

1. 在 DSM 套件中心手动安装
2. 填写安装向导 (用户名 + 密码)
3. 启动套件
4. 访问 `http://<NAS_IP>:12701/`
5. 使用安装时设置的用户名密码登录

---

## 调试技巧

### 查看日志
```bash
cat /var/log/apps/bash.log
```

### 手动启动服务
```bash
python3 /var/packages/bash/bin/terminal_server.py --address 127.0.0.1 --port 12701
```

### 检查密钥文件
```bash
ls -l /var/packages/bash/var/key.txt
```
