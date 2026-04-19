#!/usr/bin/env python3
import asyncio
import json
import os
import pty
import select
import signal
import struct
import sys
import termios
import base64
import hashlib

# 获取静态文件根目录
STATIC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../ui/static'))

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FnOS-terminal</title>
    <link rel="stylesheet" href="/static/css/xterm.css" />
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { width: 100%; height: 100%; overflow: hidden; background: #1e1e1e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        #app { display: flex; flex-direction: column; width: 100%; height: 100%; }
        .tab-bar { display: flex; align-items: center; background: #252526; border-bottom: 1px solid #3c3c3c; height: 36px; flex-shrink: 0; user-select: none; }
        .tabs { display: flex; flex: 1; overflow-x: auto; overflow-y: hidden; scrollbar-width: none; }
        .tabs::-webkit-scrollbar { display: none; }
        .tab { display: flex; align-items: center; padding: 0 12px; height: 36px; background: #2d2d2d; border-right: 1px solid #1e1e1e; color: #cccccc; cursor: pointer; font-size: 13px; min-width: 100px; max-width: 180px; transition: background 0.15s; position: relative; }
        .tab:hover { background: #383838; }
        .tab.active { background: #1e1e1e; color: #ffffff; border-bottom: 2px solid #007acc; }
        .tab-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .tab-close { width: 16px; height: 16px; margin-left: 4px; border-radius: 3px; display: flex; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.15s, background 0.15s; font-size: 14px; line-height: 1; color: #999; }
        .tab:hover .tab-close { opacity: 0.6; }
        .tab-close:hover { opacity: 1; background: #5a5a5a; color: #fff; }
        .new-tab-btn { width: 36px; height: 36px; background: transparent; border: none; color: #cccccc; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.15s; flex-shrink: 0; }
        .new-tab-btn:hover { background: #383838; }
        .terminal-container { flex: 1; overflow: hidden; background: #1e1e1e; position: relative; }
        .terminal-wrapper { width: 100%; height: 100%; padding: 4px 0 0 4px; } /* xterm container */
        
        .login-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; }
        .login-box { background: #2d2d2d; padding: 30px; border-radius: 8px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); width: 360px; max-width: 90%; }
        .login-box h2 { color: #ffffff; margin-bottom: 24px; font-size: 20px; text-align: center; }
        .login-input-group { margin-bottom: 16px; }
        .login-input-group label { display: block; color: #cccccc; margin-bottom: 6px; font-size: 14px; }
        .login-input-group input { width: 100%; padding: 10px 12px; border: 1px solid #3c3c3c; border-radius: 4px; background: #1e1e1e; color: #ffffff; font-size: 14px; outline: none; transition: border-color 0.2s; }
        .login-input-group input:focus { border-color: #007acc; }
        .login-btn { width: 100%; padding: 12px; background: #007acc; color: #ffffff; border: none; border-radius: 4px; font-size: 15px; cursor: pointer; transition: background 0.2s; margin-top: 8px; }
        .login-btn:hover { background: #005a9e; }
        .login-error { color: #f14c4c; font-size: 13px; margin-top: 12px; text-align: center; min-height: 20px; }
    </style>
    <script src="/static/js/xterm.js"></script>
    <script src="/static/js/xterm-addon-fit.js"></script>
    <script src="/static/js/xterm-addon-web-links.js"></script>
</head>
<body>
    <div id="app">
        <div class="tab-bar" id="tabBar">
            <div class="tabs" id="tabsContainer"></div>
            <button class="new-tab-btn" id="newTabBtn" title="新建标签页">+</button>
        </div>
        <div class="terminal-container" id="terminalContainer"></div>
    </div>
    <div class="login-overlay" id="loginOverlay">
        <div class="login-box">
            <h2>登录终端</h2>
            <div class="login-input-group">
                <label>用户名</label>
                <input type="text" id="username" placeholder="请输入用户名">
            </div>
            <div class="login-input-group">
                <label>密码</label>
                <input type="password" id="password" placeholder="请输入密码">
            </div>
            <button class="login-btn" id="loginBtn">登录</button>
            <p class="login-error" id="loginError"></p>
        </div>
    </div>
    <script>
    (function() {
        const AUTH_REQUIRED = __AUTH_REQUIRED__;

        class TerminalApp {
            constructor() {
                this.tabs = [];
                this.activeTabId = null;
                this.ws = null;
                this.authenticated = false;
                this.authRequired = AUTH_REQUIRED;
                this.init();
            }
            
            init() {
                document.getElementById('loginBtn').onclick = () => this.login();
                const usernameInput = document.getElementById('username');
                const passwordInput = document.getElementById('password');
                usernameInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        passwordInput.focus();
                    }
                });
                passwordInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        this.login();
                    }
                });
                document.getElementById('newTabBtn').onclick = () => this.createTab();
                window.addEventListener('resize', () => this.handleResize());
                if (this.authRequired) {
                    setTimeout(() => usernameInput.focus(), 100);
                } else {
                    this.hideLoginOverlay();
                    this.connectAndAuth('', '');
                }
            }
            
            login() {
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                this.connectAndAuth(username, password);
            }

            connectAndAuth(username, password) {
                if (this.ws) {
                    try { this.ws.close(); } catch (e) {}
                }
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                this.ws = new WebSocket(protocol + '//' + window.location.host + '/ws');
                this.ws.onopen = () => this.ws.send(JSON.stringify({type: 'auth', username: username, password: password}));
                this.ws.onmessage = (e) => {
                    const m = JSON.parse(e.data);
                    if (m.type === 'auth_success') {
                        this.authenticated = true;
                        this.hideLoginOverlay();
                        if (this.tabs.length === 0) {
                            this.createTab();
                        }
                    } else if (m.type === 'auth_failed') {
                        document.getElementById('loginError').textContent = m.error;
                    } else if (m.type === 'session_created') {
                        const targetTabId = m.client_id || this.activeTabId;
                        const tab = this.tabs.find(t => t.id === targetTabId);
                        if (tab) {
                            tab.sessionId = m.session_id;
                            if (tab.fitAddon) {
                                tab.fitAddon.fit();
                                const dims = tab.fitAddon.proposeDimensions();
                                if (dims) {
                                    this.ws.send(JSON.stringify({
                                        type: 'resize', 
                                        session_id: tab.sessionId, 
                                        cols: dims.cols, 
                                        rows: dims.rows
                                    }));
                                }
                            }
                        }
                    } else if (m.type === 'output') {
                        const tab = this.tabs.find(t => t.sessionId === m.session_id);
                        if (tab && tab.term) {
                            tab.term.write(m.data);
                        }
                    }
                };
                this.ws.onerror = () => document.getElementById('loginError').textContent = '连接失败';
            }

            hideLoginOverlay() {
                const overlay = document.getElementById('loginOverlay');
                overlay.style.display = 'none';
                document.getElementById('loginError').textContent = '';
            }
            
            createTab() {
                const id = 'tab_' + Date.now();
                const tab = { 
                    id: id, 
                    title: '终端 ' + (this.tabs.length + 1), 
                    term: null, 
                    fitAddon: null,
                    sessionId: null,
                    element: null
                };
                this.tabs.push(tab);
                this.renderTabs();
                this.switchToTab(id);
            }
            
            renderTabs() {
                const c = document.getElementById('tabsContainer');
                c.innerHTML = '';
                this.tabs.forEach(t => {
                    const el = document.createElement('div');
                    el.className = 'tab ' + (t.id === this.activeTabId ? 'active' : '');
                    el.innerHTML = '<span class="tab-title">' + t.title + '</span><span class="tab-close">x</span>';
                    el.querySelector('.tab-close').onclick = (e) => { e.stopPropagation(); this.closeTab(t.id); };
                    el.onclick = () => this.switchToTab(t.id);
                    c.appendChild(el);
                });
            }
            
            switchToTab(id) {
                this.activeTabId = id;
                const tab = this.tabs.find(t => t.id === id);
                if (tab) {
                    const container = document.getElementById('terminalContainer');
                    this.tabs.forEach(t => {
                        if (t.element) t.element.style.display = t.id === id ? 'block' : 'none';
                    });

                    if (!tab.element) {
                        const wrapper = document.createElement('div');
                        wrapper.className = 'terminal-wrapper';
                        container.appendChild(wrapper);
                        tab.element = wrapper;
                        
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
                        
                        tab.term = term;
                        tab.fitAddon = fitAddon;
                        
                        term.onData(data => {
                            if (this.ws && tab.sessionId) {
                                this.ws.send(JSON.stringify({
                                    type: 'input', 
                                    session_id: tab.sessionId, 
                                    data: data
                                }));
                            }
                        });
                        
                        term.onResize(size => {
                            if (this.ws && tab.sessionId) {
                                this.ws.send(JSON.stringify({
                                    type: 'resize', 
                                    session_id: tab.sessionId, 
                                    cols: size.cols, 
                                    rows: size.rows
                                }));
                            }
                        });

                        if (this.ws && this.authenticated && !tab.sessionId) {
                            const dims = fitAddon.proposeDimensions();
                            this.ws.send(JSON.stringify({
                                type: 'create_session', 
                                client_id: tab.id,
                                cols: dims ? dims.cols : 80, 
                                rows: dims ? dims.rows : 24
                            }));
                        }
                    } else {
                        if (tab.fitAddon) {
                            requestAnimationFrame(() => {
                                tab.fitAddon.fit();
                                tab.term.focus();
                            });
                        }
                    }
                    this.renderTabs();
                }
            }
            
            closeTab(id) {
                const idx = this.tabs.findIndex(t => t.id === id);
                if (idx !== -1) {
                    const tab = this.tabs[idx];
                    if (this.ws && tab.sessionId) {
                        this.ws.send(JSON.stringify({type: 'close_session', session_id: tab.sessionId}));
                    }
                    if (tab.term) tab.term.dispose();
                    if (tab.element) tab.element.remove();
                    
                    this.tabs.splice(idx, 1);
                    if (this.tabs.length === 0) {
                        this.createTab();
                    } else if (!this.tabs.find(t => t.id === this.activeTabId)) {
                        this.switchToTab(this.tabs[Math.min(idx, this.tabs.length - 1)]?.id);
                    } else {
                        this.renderTabs();
                    }
                }
            }
            
            handleResize() {
                const tab = this.tabs.find(t => t.id === this.activeTabId);
                if (tab && tab.fitAddon) {
                    tab.fitAddon.fit();
                    const dims = tab.fitAddon.proposeDimensions();
                    if (dims && tab.sessionId && this.ws) {
                         this.ws.send(JSON.stringify({
                            type: 'resize', 
                            session_id: tab.sessionId, 
                            cols: dims.cols, 
                            rows: dims.rows
                        }));
                    }
                }
            }
        }
        
        window.onload = function() {
            if (window.Terminal) {
                new TerminalApp();
            } else {
                console.error('xterm.js failed to load');
                document.getElementById('loginError').textContent = '终端组件加载失败，请刷新页面';
            }
        };
    })();
    </script>
</body>
</html>"""

sessions = {}
session_map = {}

def get_key_file():
    for path in ['/var/packages/bash/var/key.txt', '/vol1/@appdata/bash/key.txt', '/volume1/@appdata/bash/key.txt']:
        if os.path.exists(path):
            return path
    return None

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def parse_auth_content(content):
    if not content:
        return '', '', ''

    if content.startswith('sha256:'):
        parts = content.split(':', 2)
        if len(parts) == 3 and parts[1] and parts[2]:
            return parts[1], parts[2], 'sha256'
        return '', '', ''

    user, sep, secret = content.partition(':')
    if sep and user and secret:
        return user, secret, 'plain'
    return '', '', ''

def read_auth():
    key_file = get_key_file()
    if key_file:
        try:
            with open(key_file, 'r') as f:
                content = f.read().strip()
                return parse_auth_content(content)
        except:
            pass
    return '', '', ''

async def handle_client(reader, writer):
    try:
        # Read initial request (headers)
        # 4KB should be enough for headers
        data = await reader.read(4096)
        if not data:
            writer.close()
            return
            
        request_text = data.decode('utf-8', errors='ignore')
        if '\r\n\r\n' in request_text:
            headers_part, body_part = request_text.split('\r\n\r\n', 1)
        else:
            headers_part = request_text
            body_part = ''
            
        lines = headers_part.split('\r\n')
        if not lines:
            writer.close()
            return
            
        request_line = lines[0].split()
        if len(request_line) < 2:
            writer.close()
            return
            
        method, path = request_line[0], request_line[1]
        headers = {}
        for line in lines[1:]:
            if ':' in line:
                k, v = line.split(':', 1)
                headers[k.strip().lower()] = v.strip()
                
        # Check WebSocket Upgrade
        if headers.get('upgrade', '').lower() == 'websocket' and \
           headers.get('connection', '').lower().find('upgrade') != -1:
            key = headers.get('sec-websocket-key')
            if key:
                await handle_websocket(reader, writer, key)
            else:
                writer.write(b'HTTP/1.1 400 Bad Request\r\n\r\n')
                writer.close()
        else:
            await handle_http(writer, path)
            
    except Exception as e:
        print(f"Connection error: {e}")
        try:
            writer.close()
        except:
            pass

async def handle_http(writer, path):
    try:
        if path == '/' or path == '/index.html':
            key_user, key_secret, _ = read_auth()
            auth_required = bool(key_user and key_secret)
            html = HTML_TEMPLATE.replace('__AUTH_REQUIRED__', 'true' if auth_required else 'false')
            response = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n' + html
            writer.write(response.encode())
        elif path.startswith('/static/'):
            rel_path = path[8:]
            if '..' in rel_path:
                 writer.write(b'HTTP/1.1 403 Forbidden\r\nContent-Type: text/plain\r\n\r\nForbidden')
            else:
                file_path = os.path.join(STATIC_ROOT, rel_path)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    ext = os.path.splitext(file_path)[1]
                    content_type = 'application/octet-stream'
                    if ext == '.css': content_type = 'text/css'
                    elif ext == '.js': content_type = 'application/javascript'
                    elif ext == '.png': content_type = 'image/png'
                    
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read()
                            header = f'HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(content)}\r\nConnection: close\r\n\r\n'
                            writer.write(header.encode() + content)
                    except:
                         writer.write(b'HTTP/1.1 500 Internal Server Error\r\n\r\n')
                else:
                    writer.write(b'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nNot Found')
        else:
            writer.write(b'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nNot Found')
    except:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except:
            pass

async def send_ws_frame(writer, data, opcode=1):
    # opcode 1 = text
    # FIN=1, Opcode=opcode
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

async def read_ws_frame(reader):
    try:
        head1 = await reader.read(2)
        if len(head1) < 2: return None
        
        b1, b2 = head1[0], head1[1]
        fin = b1 & 0x80
        opcode = b1 & 0x0f
        masked = b2 & 0x80
        payload_len = b2 & 0x7f
        
        if payload_len == 126:
            data = await reader.read(2)
            if len(data) < 2: return None
            payload_len = struct.unpack('!H', data)[0]
        elif payload_len == 127:
            data = await reader.read(8)
            if len(data) < 8: return None
            payload_len = struct.unpack('!Q', data)[0]
            
        mask_key = None
        if masked:
            mask_key = await reader.read(4)
            if len(mask_key) < 4: return None
            
        payload = await reader.read(payload_len)
        if len(payload) < payload_len: return None
        
        if masked:
            unmasked = bytearray(payload_len)
            for i in range(payload_len):
                unmasked[i] = payload[i] ^ mask_key[i % 4]
            payload = unmasked
            
        return opcode, payload
    except:
        return None

async def handle_websocket(reader, writer, key):
    # Handshake
    magic = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    accept_key = base64.b64encode(hashlib.sha1(key.encode() + magic).digest()).decode()
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
    )
    writer.write(response.encode())
    await writer.drain()
    
    authenticated = False
    session_ids = set()
    
    try:
        while True:
            frame = await read_ws_frame(reader)
            if not frame: break
            
            opcode, payload = frame
            if opcode == 8: # Close
                break
            
            if opcode == 1: # Text
                try:
                    msg = json.loads(payload.decode('utf-8'))
                    msg_type = msg.get('type')
                    
                    if msg_type == 'auth':
                        key_user, key_secret, auth_mode = read_auth()
                        username = msg.get('username', '')
                        password = msg.get('password', '')

                        auth_valid = not key_user and not key_secret
                        if key_user and key_secret:
                            if auth_mode == 'sha256':
                                auth_valid = username == key_user and hash_password(password) == key_secret
                            else:
                                auth_valid = username == key_user and password == key_secret

                        if auth_valid:
                            authenticated = True
                            await send_ws_frame(writer, json.dumps({'type': 'auth_success'}))
                        else:
                            await send_ws_frame(writer, json.dumps({'type': 'auth_failed', 'error': '认证失败'}))
                            
                    elif msg_type == 'create_session' and authenticated:
                        import uuid
                        session_id = str(uuid.uuid4())
                        cols = msg.get('cols', 80)
                        rows = msg.get('rows', 24)
                        client_id = msg.get('client_id')
                        
                        try:
                            pid, master_fd = pty.fork()
                            if pid == 0:
                                env = os.environ.copy()
                                env['TERM'] = 'xterm-256color'
                                os.execvp('login', ['login'])
                            else:
                                session = {'pid': pid, 'fd': master_fd}
                                try:
                                    import fcntl
                                    ws = struct.pack('HHHH', rows, cols, 0, 0)
                                    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, ws)
                                except:
                                    pass
                                sessions[session_id] = session
                                session_ids.add(session_id)
                                
                                if session_id not in session_map:
                                     session_map[session_id] = []
                                session_map[session_id].append(writer)
                                
                                payload = {'type': 'session_created', 'session_id': session_id}
                                if client_id:
                                    payload['client_id'] = client_id
                                await send_ws_frame(writer, json.dumps(payload))
                        except Exception as e:
                            await send_ws_frame(writer, json.dumps({'type': 'session_error', 'error': str(e)}))
                            
                    elif msg_type == 'input' and authenticated:
                        session_id = msg.get('session_id')
                        if session_id and session_id in sessions:
                            data_str = msg.get('data', '')
                            try:
                                data_bytes = data_str.encode('utf-8') if isinstance(data_str, str) else data_str
                                os.write(sessions[session_id]['fd'], data_bytes)
                            except:
                                pass
                                
                    elif msg_type == 'resize' and authenticated:
                        session_id = msg.get('session_id')
                        if session_id and session_id in sessions:
                            cols = msg.get('cols', 80)
                            rows = msg.get('rows', 24)
                            try:
                                import fcntl
                                fcntl.ioctl(sessions[session_id]['fd'], termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
                            except:
                                pass
                                
                    elif msg_type == 'close_session' and authenticated:
                        session_id = msg.get('session_id')
                        if session_id and session_id in sessions:
                            s = sessions.pop(session_id, None)
                            session_ids.discard(session_id)
                            if session_id in session_map:
                                if writer in session_map[session_id]:
                                    session_map[session_id].remove(writer)
                                if not session_map[session_id]:
                                    del session_map[session_id]
                            if s:
                                try:
                                    os.close(s['fd'])
                                    os.kill(s['pid'], signal.SIGTERM)
                                except:
                                    pass

                except Exception as e:
                    print(f"Msg error: {e}")
                    
    except Exception as e:
        print(f"WS Handler error: {e}")
    finally:
        for sid in list(session_ids):
            s = sessions.pop(sid, None)
            if sid in session_map:
                if writer in session_map[sid]:
                    session_map[sid].remove(writer)
                if not session_map[sid]:
                    del session_map[sid]
            
            if s:
                try:
                    os.close(s['fd'])
                    os.kill(s['pid'], signal.SIGTERM)
                except:
                    pass
        try:
            writer.close()
            await writer.wait_closed()
        except:
            pass

async def broadcast_output():
    while True:
        dead_sessions = []
        for sid, s in list(sessions.items()):
            try:
                readable, _, _ = select.select([s['fd']], [], [], 0.02)
                if readable:
                    data = os.read(s['fd'], 8192)
                    if data:
                        if sid in session_map:
                            writers = session_map[sid]
                            for writer in writers:
                                try:
                                    await send_ws_frame(writer, json.dumps({'type': 'output', 'session_id': sid, 'data': data.decode('utf-8', errors='replace')}))
                                except:
                                    pass
                        else:
                            pass
            except OSError:
                dead_sessions.append(sid)
            except Exception as e:
                print(f"Broadcast error for {sid}: {e}")
        
        for sid in dead_sessions:
            s = sessions.pop(sid, None)
            if sid in session_map:
                del session_map[sid]
            if s:
                try:
                    os.close(s['fd'])
                    os.kill(s['pid'], signal.SIGTERM)
                except:
                    pass
        
        await asyncio.sleep(0.01)

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--address', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=12701)
    args = parser.parse_args()
    
    asyncio.create_task(broadcast_output())
    
    # Single server for both HTTP and WS
    server = await asyncio.start_server(handle_client, args.address, args.port)
    
    print(f'FnOS Terminal Server running on http://{args.address}:{args.port}')
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
