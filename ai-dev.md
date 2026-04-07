# AI 开发调试指南

本文档说明如何使用 AITestAdapter 进行插件的 AI 自动化调试。

## 概述

AITestAdapter 是一个基于 FastAPI 的 HTTP 测试服务器，允许通过 curl 命令发送消息来测试插件，无需真实的聊天平台。

## 启动测试服务器

```bash
python test_server.py
```

服务器会在 `localhost:18765` 启动。

## HTTP 接口

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/health` | - | 健康检查 |
| GET | `/sessions` | - | 列出会话 |
| POST | `/activate` | session_id, plugin_name, layer | 激活插件 |
| POST | `/msg` | session_id, sender_id, sender_name, content | 发送消息 |

## 重要：中文编码

使用 `--data-urlencode` 处理中文参数：

```bash
# 正确方式
curl -X POST http://localhost:18765/msg \
  --data-urlencode "session_id=group.test123" \
  --data-urlencode "sender_id=user1" \
  --data-urlencode "sender_name=用户1" \
  --data-urlencode "content=创建房间"

# 错误方式 - 中文会乱码
curl -X POST http://localhost:18765/msg \
  -d "sender_id=user1&sender_name=用户1&content=创建房间"
```

## 插件调试流程

### 1. 启动服务器

```bash
python test_server.py
```

### 2. 激活插件

```bash
curl -X POST http://localhost:18765/activate \
  --data-urlencode "session_id=group.test123" \
  --data-urlencode "plugin_name=criminal_dance" \
  --data-urlencode "layer=2"
```

### 3. 发送消息测试

```bash
# 创建房间
curl -X POST http://localhost:18765/msg \
  --data-urlencode "session_id=group.test123" \
  --data-urlencode "sender_id=user1" \
  --data-urlencode "sender_name=用户1" \
  --data-urlencode "content=创建房间"

# 玩家加入
curl -X POST http://localhost:18765/msg \
  --data-urlencode "session_id=group.test123" \
  --data-urlencode "sender_id=user2" \
  --data-urlencode "sender_name=用户2" \
  --data-urlencode "content=加入"

curl -X POST http://localhost:18765/msg \
  --data-urlencode "session_id=group.test123" \
  --data-urlencode "sender_id=user3" \
  --data-urlencode "sender_name=用户3" \
  --data-urlencode "content=加入"

# 房主开始游戏
curl -X POST http://localhost:18765/msg \
  --data-urlencode "session_id=group.test123" \
  --data-urlencode "sender_id=user1" \
  --data-urlencode "sender_name=用户1" \
  --data-urlencode "content=开始"

# 查看状态
curl -X POST http://localhost:18765/msg \
  --data-urlencode "session_id=group.test123" \
  --data-urlencode "sender_id=user1" \
  --data-urlencode "sender_name=用户1" \
  --data-urlencode "content=状态"
```

## 查看日志

日志文件位于 `logs/bot.log`，可使用 tail 命令实时查看：

```bash
tail -f logs/bot.log
```

## 关键概念

### Session 和 Group

- `session_id` 格式：`group.xxx` 或 `private.xxx`
- `group_id` 是群号，从 session_id 中提取
- 不同 session_id 的房间数据互相隔离

### Layer 层级

- Layer 0: 系统级插件（如 meta）
- Layer 1: 普通插件（默认激活）
- Layer 2: 独占应用（需手动激活）

### Space 内存模式

使用 `Space(name, group_id, memory=True)` 可以实现：
- 按群隔离数据
- 重启后数据清除

## Python 测试脚本

如果需要更复杂的测试场景，可以写 Python 脚本：

```python
import requests

# 激活插件
requests.post('http://localhost:18765/activate', data={
    'session_id': 'group.test123',
    'plugin_name': 'criminal_dance',
    'layer': 2
})

# 发送消息
requests.post('http://localhost:18765/msg', data={
    'session_id': 'group.test123',
    'sender_id': 'user1',
    'sender_name': '用户1',
    'content': '创建房间'
})
```

## 关闭测试服务器

```bash
# 查找进程
netstat -ano | grep 18765

# 关闭
taskkill //F //PID <pid>
```

## 常见问题

### Q: 消息发送成功但没有响应？
A: 检查是否已激活插件，以及 session_id 是否正确。

### Q: 中文显示乱码？
A: 使用 `--data-urlencode` 而不是 `-d`。

### Q: 房间状态异常？
A: 不同 session_id 的房间数据互相独立，确保使用相同的 session_id。
