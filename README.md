# DoroBot 插件开发指南

DoroBot 是一个基于分层架构的插件式聊天机器人框架。本指南介绍如何开发一个插件。

我们推荐使用Python3.10或者更高版本

![DoroBot](doro.png)

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

## 目录

- [基础结构](#基础结构)
- [Layer 层级系统](#layer-层级系统)
- [Plugin 插件](#plugin-插件)
- [Meta Plugin](#meta-plugin)
- [Space 持久化](#space-持久化)
- [NTQQ 适配器与 WebSocket 服务器](#ntqq-适配器与-websocket-服务器)
- [使用 ConsoleBot 调试](#使用-consolebot-调试)

---

## 基础结构

```
dorobot/
├── adapter.py      # 适配器基类
├── bot.py          # Bot 基类
├── bot_manager.py  # Bot 管理器
├── context.py      # 异步上下文
├── layer.py        # 层级系统
├── plugin.py       # 插件基类
├── plugin_manager.py  # 插件管理器
├── router.py       # 消息路由
├── session.py      # 会话
└── session_manager.py # 会话管理器
```

---

## Layer 层级系统

每个会话（Session）有 4 个预定义的碰撞层（Layer），消息按层级顺序传递：

### 消息流程

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
                                  │ Layer2 │ ──► exclusive 插件群（只能激活1个）
                                  └────────┘
                                    │
                                      ▼
                                  ┌────────┐
                                  │ Layer3 │ ──► shared 插件群
                                  └────────┘
```

消息传递规则：

1. 消息从 **Layer 0** 开始向下传递
2. 如果插件返回 `True`，消息继续传递到下一层
3. 如果插件返回 `False`，消息传递中断，不再传递给后续层级
4. meta 层（Layer 0）无法关闭，始终生效

### 层级一览

| 层ID | 类型 | 说明 | 独占性 |
|------|------|------|--------|
| 0 | `meta` | 系统保留层，只能激活 `meta` 插件 | - |
| 1 | `shared` | 共享层，可同时激活多个插件 | 否 |
| 2 | `exclusive` | 独占层，可注册多个插件，但同一时间只能激活一个 | 是 |
| 3 | `shared` | 共享层，可同时激活多个插件 | 否 |

### 分层建议

| 场景 | 推荐层级 |
|------|----------|
| 核心管理功能（meta） | Layer 0 |
| 基础工具插件（问候等） | Layer 1 |
| 复杂多人互动应用（游戏、投票、RPG等） | **Layer 2（独占层）** |
| 兜底插件（echo复读、统计等） | Layer 3 |

### 层级行为

- **Layer 0 (meta)**：系统预留，只有 `meta` 插件能使用
- **Layer 1 (shared)**：允许多个插件共存
- **Layer 2 (exclusive)**：同一时间只能激活一个插件
- **Layer 3 (shared)**：补漏层（fallback），适合 echo、统计等兜底插件

### 独占层设计理念

我们设计 `exclusive layer`（独占层）是为了解决**复杂多人互动的群组应用**中常见的指令冲突问题。

**问题场景**：当多个插件同时处理同一群组消息时，插件 A 可能截获了插件 B 期望响应的指令，导致功能不可用。

**解决方案**：将这类复杂应用插件放在独占层（Layer 2），同一时间同一群组只能激活一个应用插件，避免指令冲突。

### 补漏层设计理念

Layer 3 是一个**补漏层**（fallback shared layer）。

**设计目的**：对于需要接收所有消息、但又希望在前面的应用都没有命中时才处理的插件，放置在这一层。

**典型场景**：

- **Echo/复读插件**：作为兜底，所有前面的插件都不处理时，它来响应
- **统计插件**：记录所有未被处理的对话
- **监控插件**：记录异常情况

**消息流向**：

```
Layer 0 → Layer 1 → Layer 2 → Layer 3
  ↓         ↓         ↓         ↓
 meta    工具插件   独占应用   兜底插件
```

---

## Plugin 插件

### 插件单例模式

插件采用**单例模式**——全局有且仅有一个实例。当不同的 Bot 在不同的群聊中收到消息时，调用的都是同一个插件实例。

插件通过上下文获取当前请求的 Bot 和 Session：

```python
class MyPlugin(Plugin):
    async def handle_message(self, message: Message) -> bool:
        bot = self.get_bot()      # 当前 Bot（不同群聊可能不同）
        session = self.get_session()  # 当前 Session（不同群聊/私聊可能不同）
        # bot 和 session 均来自调用方，而非插件自身
        return True
```

插件自身不应保存与特定会话相关的状态，而应将状态存储在 `Space` 中（详见下文）。

### 基本结构

```python
from dorobot import Plugin, Message, register_plugin

@register_plugin("插件名称", layer=层ID, description="插件描述", bots=[Bot类型])
class MyPlugin(Plugin):
    async def handle_message(self, message: Message) -> bool:
        # 处理消息逻辑
        return True  # 返回 True 继续传递，False 中断传递

    async def on_activate(self):
        # 可选：插件激活时的初始化逻辑
        pass
```

### 装饰器参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | - | 插件唯一名称 |
| `layer` | `int` | `2` | 所在层级（0-3） |
| `description` | `str` | `""` | 插件描述，用于 `/plugins` 命令显示 |
| `bots` | `list[type]` | `None` | 允许使用该插件的 Bot 类型列表，`None` 表示所有 Bot，推荐使用默认值 |

### Message 对象

```python
@dataclass
class Message:
    content: str          # 消息内容
    sender_id: str       # 发送者 ID
    sender_name: str     # 发送者昵称
    msg_type: str = "text"  # 消息类型：text, image 等
    raw_data: dict = None  # 原始消息数据
```

### 插件基类方法

| 方法 | 说明 |
|------|------|
| `handle_message(message)` | **必须实现**。处理消息，返回 `True` 继续传递，`False` 中断 |
| `on_activate()` | 可选实现。插件激活时的初始化逻辑 |
| `send_message(content, session_id, bot_id)` | 已有实现。发送消息到会话 |
| `get_session()` | 已有实现。获取当前 Session 对象 |
| `get_bot()` | 已有实现。获取当前 Bot 对象 |
| `get_session_space()` | 已有实现。获取当前 Session 对应的 Space |

### handle_message 返回值

- 返回 `True`：消息继续传递给下一层级的插件
- 返回 `False`：中断传递，后续层级的插件不会收到此消息

### 快速创建插件

框架提供了一组装饰器，用于快速创建简单插件，无需继承 `Plugin` 类：

```python
from dorobot import on_command, on_keyword, on_pattern
```

#### on_command - 命令触发

以指定命令字符串触发，前缀默认为 `/`，可配置：

```python
from dorobot import on_command, Message

@on_command("echo")  # 匹配 /echo
async def echo(message: Message, plugin, args: str):
    """回声插件"""
    await plugin.send_message(args)
```

#### on_keyword - 关键词触发

消息包含关键词时触发（不区分大小写），description 默认为函数注释：

```python
from dorobot import on_keyword, Message

@on_keyword("天气")  # description 默认为 "查询天气示例"
async def weather(message: Message, plugin):
    """查询天气示例"""
    await plugin.send_message(f"{message.sender_name}，今天天气晴朗！")
```

#### on_pattern - 正则匹配触发

匹配正则表达式时触发，可通过 `match` 对象获取捕获组：

```python
from dorobot import on_pattern, Message

@on_pattern(r"^/echo (.+)$")  # description 默认为函数注释
async def echo(message: Message, plugin, match):
    """回声插件"""
    await plugin.send_message(match.group(1))
```

所有装饰器默认注册到 Layer 1（共享层），description 默认为函数注释的第一行。

---

## Meta Plugin

Meta 插件位于 0 层（系统保留层），是预置的管理插件。

### 功能

- `{prefix}help` - 显示帮助信息
- `{prefix}plugins` - 显示所有层级插件列表及激活状态
- `{prefix}meta 插件名` - 激活或关闭指定插件

### 使用示例

```
用户输入: {prefix}echo
结果: 切换 echo 插件的激活状态

用户输入: {prefix}plugins
结果: 显示所有插件的层级和状态
```

---

## Space 持久化

Space 是基于文件系统的持久化键值存储，适合存储插件的会话相关数据。

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

### 持久化

Space 数据会自动持久化到磁盘：
- `space_manager.init()` 在启动时加载已有数据
- `space_manager.start()` 启动后台扫描任务，每秒检查 dirty 的 Space
- `space_manager.stop()` 或程序退出时保存所有 dirty 的 Space

### 插件中使用

插件通过 `get_session_space()` 获取当前会话的 Space：

```python
class MyPlugin(Plugin):
    async def handle_message(self, message: Message) -> bool:
        space = self.get_session_space()
        space["visit_count"] = space.get("visit_count", 0) + 1
        return True
```

---

## NTQQAdapter

### Bot 概念

Bot 是与具体聊天平台通信的适配器实例。每个平台（如 QQ、Discord）有自己的 Bot 实现。

### NTQQ 适配器与 WebSocket 服务器

NTQQ 适配器（`NTQQAdapter`）监听 **8082** 端口，启动一个 WebSocket 服务器，等待 QQ 客户端/协议端连接。

```
┌─────────────┐         WebSocket (ws://0.0.0.0:8082)         ┌─────────────┐
│   NTQQ      │ ─────────────────────────────────────────────── │  DoroBot    │
│  客户端      │                  8082 端口                     │  适配器      │
└─────────────┘                                                  └─────────────┘
```

**工作流程：**

1. DoroBot 启动时，`NTQQAdapter` 在 8082 端口建立 WebSocket 服务器
2. 配置NTQQ 客户端连接到 `ws://你的服务器:8082`
3. 连接建立后，NTQQ 客户端会上报 `self_id` 完成注册
4. 此后所有消息、事件通过这个 WebSocket 双向通信

### 基础用法：发送消息

使用 `send_message` 发送消息（推荐）：

```python
class MyPlugin(Plugin):
    async def handle_message(self, message: Message) -> bool:
        await self.send_message("Hello!")  # 发送到当前会话
        await self.send_message("Hello!", session_id="ntqq.group.123456")  # 指定会话
```

或通过 Bot 实例发送：

```python
from dorobot.adapters.ntqq import NTQQBot
class MyPlugin(Plugin):
    async def handle_message(self, message: Message) -> bool:
        bot: NTQQBot = self.get_bot()
        await bot.send_group(group_id, "Hello!")    # 发送群消息
        await bot.send_private(user_id, "Hello!")    # 发送私聊消息
```

### 进阶用法：call_api

**示例**：调用平台原生 API 发送消息：

```python
from dorobot.adapters.ntqq import NTQQBot
class MyPlugin(Plugin):
    async def handle_message(self, message: Message) -> bool:
        bot: NTQQBot = self.get_bot()

        # 直接调用 send_group_msg API
        await bot.call_api("send_group_msg", {
            "group_id": "123456",
            "message": [{"type": "text", "data": {"text": "Hello!"}}]
        })
```

**适用场景**：调用平台提供的其他 API（如获取群成员信息、查询用户资料等）。

## 使用 ConsoleBot 调试

开发插件时，可以使用 ConsoleBot 在命令行中模拟消息，无需启动真实的 QQ 连接。

### 启用 ConsoleBot

在 `app.py` 中注册 ConsoleAdapter：

```python
from dorobot import init_logging, load_plugins, run, register_adapter
from dorobot.adapters.console import ConsoleAdapter

init_logging(level="DEBUG")
load_plugins()

# 启用 ConsoleBot
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

输入后会模拟收到消息，触发插件处理流程。输出的 `Bot -> session: content` 是调试日志。

### 特点

- 消息会经过完整的插件路由流程
- 支持所有层级和插件切换命令（如 `/plugins`）
- 适合快速测试插件逻辑，无需配置 NTQQ 客户端

