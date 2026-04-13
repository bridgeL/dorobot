# DoroBot 插件开发指南

DoroBot 是一个基于分层架构的插件式聊天机器人框架。

我们推荐使用 Python 3.10 或更高版本。

![DoroBot](doro.png)

---

# 快速入门

## 快速开始

**前置准备：**

在开始之前，推荐先阅读 [NTQQ 协议端安装指南](https://napneko.github.io/)，了解如何部署 NTQQ 协议端。部署好协议端是运行本框架的前提。

**安装依赖：**
```bash
pip install -r requirements.txt
```

**配置：**
```bash
cp .env.example .env
```

**启动机器人：**
```bash
python app.py
```

---

## 消息流向

```
┌──────────┐      ┌──────────┐      ┌─────────┐
│   NTQQ   │ ───► │  Router  │ ───► │ Plugin  │
│  客户端   │      │  消息路由 │      └─────────┘
└──────────┘      └──────────┘        
```

消息从 NTQQ 客户端发出，经 Router 路由到各层级的插件处理。

---

## 快速创建插件

插件开发流程：实例化 → 注册处理器 → 注册到管理器。

```python
from dorobot import Plugin, Message

app = Plugin(name="my_plugin", layer=1, description="我的插件")
app.register()
```

### on_message - 消息处理

每次收到消息都会触发：

```python
@app.on_message()
async def handle(msg: Message) -> bool:
    await app.send_message(f"收到：{msg.content}")
    return True  # 返回 True 继续传递，False 中断
```

### on_command - 命令触发

以命令字符串触发，前缀默认为 `/`：

```python
@app.on_command("echo")
async def handle(msg: Message, arg: str) -> bool:
    await app.send_message(arg)
    return False  # 命令已处理，中断传递
```

### on_regex - 正则匹配触发

匹配正则表达式时触发，可通过 `match` 对象获取捕获组：

```python
@app.on_regex(r"^@(.+?)\s+(.+)$")
async def handle(msg: Message, match) -> bool:
    await app.send_message(f"已转告 {match.group(1)}：{match.group(2)}")
    return False
```

### on_open / on_close - 生命周期

```python
@app.on_open()
async def on_open():
    print("插件激活")

@app.on_close()
async def on_close():
    print("插件关闭")
```

### 发送消息

使用 `app.send_message()` 发送消息到当前会话：

```python
await app.send_message("Hello!")
await app.send_message(f"@{msg.sender_name}", session_id="ntqq.group.123456")  # 指定会话
```

### 完整示例

```python
from dorobot import Plugin, Message

app = Plugin(name="echo", layer=1, description="回声插件")

@app.on_command("echo")
async def handle(msg: Message, arg: str) -> bool:
    await app.send_message(arg)
    return False

app.register()
```

### 跨 Session 挂载

scope=group 的插件可以挂载到私聊 session：

```python
app.mount_to("private_session_id")      # 挂载
app.unmount_from("private_session_id")  # 卸载
app.unmount_from_all()                  # 卸载全部
```

主 session 关闭插件时，所有挂载自动清除。

---

## Meta Plugin

Meta Plugin 位于 Layer 0（系统保留层），提供基础管理功能：

| 命令 | 功能 |
|------|------|
| `/help` | 显示帮助信息 |
| `/meta` | 显示所有层级插件列表及激活状态 |
| `/meta 插件名` | 激活或关闭指定插件 |

---

# 深入

## 插件的层级结构

每个会话（Session）有 4 个预定义的碰撞层（Layer）：

```
┌──────────┐      ┌──────────┐      ┌────────┐
│   NTQQ   │ ───► │  Router  │ ───► │ Layer0 │ ──► meta 插件
│  客户端   │      │  消息路由 │      └────────┘
└──────────┘      └──────────┘        │
                                      ▼
                                  ┌────────┐
                                  │ Layer1 │ ──► shared 插件群
                                  └────────┘
                                    │
                                      ▼
                                  ┌────────┐
                                  │ Layer2 │ ──► exclusive 插件群
                                  └────────┘
                                    │
                                      ▼
                                  ┌────────┐
                                  │ Layer3 │ ──► shared 插件群
                                  └────────┘
```

| 层ID | 类型 | 说明 | 独占性 |
|------|------|------|--------|
| 0 | `meta` | 系统保留层，只能激活 `meta` 插件 | - |
| 1 | `shared` | 共享层，可同时激活多个插件 | 否 |
| 2 | `exclusive` | 独占层，可注册多个插件，但同一时间只能激活一个 | 是 |
| 3 | `shared` | 共享层，可同时激活多个插件 | 否 |

### 消息在层内流动

同一层级的多个插件**同时**收到消息：

```
Layer 1:
Plugin1 ─┬─→ (并行处理)
Plugin2 ─┤
Plugin3 ─┘
         ↓
      Layer2
```

所有插件同时处理，任何一个返回 `False` 都会中断向下的传递。

### 消息在层间流动

1. 消息从 **Layer 0** 开始向下传递
2. 如果插件返回 `True`，消息继续传递到下一层
3. 如果插件返回 `False`，消息传递中断，不再传递给后续层级
4. meta 层（Layer 0）无法关闭，始终生效

### 独占层和共享层的区别

**共享层（Layer 1, Layer 3）**：多个插件可以同时激活，都能收到消息。

**独占层（Layer 2）**：同一时间同一会话只能激活一个插件。适用于复杂多人互动应用（如游戏、投票、RPG），避免指令冲突。

**分层建议：**

| 场景 | 推荐层级 |
|------|----------|
| 核心管理功能（meta） | Layer 0 |
| 基础工具插件（问候等） | Layer 1 |
| 复杂多人互动应用（游戏、投票、RPG等） | **Layer 2（独占层）** |
| 兜底插件（echo复读、统计等） | Layer 3 |

---

## 配置 Prefix

Prefix 是命令的前缀符号，默认 `/`。可以通过 `.env` 修改：

```bash
CMD_PREFIX=.
```

修改后，`{prefix}help` 变为 `.help`。

---

## Space 持久化

Space 是基于文件系统的持久化键值存储，适合存储插件的会话相关数据。Space是单例模式。相同names创建出的Space指向同一对象。

### 基本用法

```python
from dorobot import Space

# 存储数据
space = Space("my_plugin", session_id)
space["key"] = "value"
print(space["key"])  # value
```

### 路径映射

`Space(a, b, c)` 对应文件 `space/a/b/c.json`。

| 示例 | 文件路径 |
|------|----------|
| `Space("data")` | `space/data.json` |
| `Space("user", "123")` | `space/user/123.json` |
| `Space("char_freq", session_id)` | `space/char_freq/{session_id}.json` |

### 持久化模式

Space 支持两种持久化模式：

**持久化模式（默认）**：数据自动保存到 `space/` 目录

**内存模式**：设置 `Space(..., memory=True)`，数据仅存储在内存中

```python
# 内存模式示例
space = Space("temp_data", session_id, memory=True)
```

### 插件中使用

```python
app = Plugin(name="my_plugin", layer=1)

@app.on_message()
async def handle(msg: Message) -> bool:
    # 通过 get_space() 获取（自动绑定插件名和会话ID）
    space = app.get_space(memory=False)
    space["visit_count"] = space.get("visit_count", 0) + 1
    return True
```

---

## 使用 NTQQ 自定义 Call API

通过 `bot.call_api()` 调用平台原生 API：

```python
from dorobot import Plugin, Message
from dorobot.adapters.ntqq import NTQQBot

app = Plugin(name="my_plugin", layer=1)

@app.on_message()
async def handle(msg: Message) -> bool:
    bot: NTQQBot = app.get_bot()

    # 发送群消息
    await bot.call_api("send_group_msg", {
        "group_id": "123456",
        "message": [{"type": "text", "data": {"text": "Hello!"}}]
    })

    # 获取群成员信息
    members = await bot.call_api("get_group_member_list", {
        "group_id": "123456"
    })
```

适用场景：调用平台提供的其他 API（如获取群成员信息、查询用户资料等）。

[NapCat提供的API](https://napcat.apifox.cn/)

---

## 使用 ConsoleBot 手动调试

ConsoleBot 可以在命令行中模拟消息，无需启动真实的 QQ 连接。

### 启用 ConsoleBot

```python
"""多插件聊天机器人 - 启动入口"""

from dorobot import init_logging, load_plugins, run, register_adapter, init_space

init_logging(level="DEBUG")
init_space()
load_plugins()

# 命令行调试
from dorobot.adapters.console import ConsoleAdapter
register_adapter(ConsoleAdapter())

run()
```

### 输入格式

```
session_id user_id content
```

- `session_id`：会话标识，如 `group.123456`
- `user_id`：用户标识，如 `10001`
- `content`：消息内容

### 示例

```
> group.123456 张三 你好
> group.123456 李四 /plugins
> private.10001 王五 随机内容
```

特点：
- 消息会经过完整的插件路由流程
- 支持所有层级和插件切换命令
- 适合快速测试插件逻辑

---

## 使用 AITestAdapter 自动调试

AITestAdapter 是基于 FastAPI 的 HTTP 测试服务器，支持通过 curl 命令模拟发送消息，适合 AI 自动化调试。

AI 可以自主完成插件开发和调试闭环：

```
用户：帮我调试插件demo.py，我已经启动了服务器
AI：正在使用 AITestAdapter 测试 demo.py 插件...
   $ curl -X POST http://localhost:18765/activate ...
   $ curl -X POST http://localhost:18765/msg ...
   插件响应正常，功能验证通过。
```

详见 [Skill: 插件调试](.claude/skills/test-plugin/skill.md)

# 添加mcp server

claude mcp add --transport stdio dorobot --scope project python server.py
