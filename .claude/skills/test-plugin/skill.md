---
name: test-plugin
description: 插件调试专用工具，通过 MCP 调用测试服务，一键模拟消息、查看日志、管理插件
---

# 测试插件调试指南

## MCP 提供的能力

### 启动/关闭 dorobot

启动 `start_dorobot`

关闭 `stop_dorobot`

当你修改了代码后，应该重启dorobot来使改动生效

### 查看日志

查看最新n条日志 `get_logs`

### 发送模拟消息

模拟dorobot系统收到来自于某个群聊某个用户的消息，或者来自于某个用户的私聊消息

`send_message` 方法接受一个消息对象，包含以下字段：

- session_type: 会话类型，"group" 或 "private"
- target_id: 目标ID（群号或用户ID）
- sender_id: 发送者ID
- sender_name: 发送者昵称
- content: 消息内容

#### content消息格式

dorobot内置有插件管理功能，当消息内容以`/meta 插件名`开头时，会被识别为插件管理指令，用于开启或关闭指定插件。例如：

- `/meta hello`：开启/关闭名为hello插件
- `/meta`：列出所有插件及其状态

## 调试流程建议

1. 启动 MCP 服务：确保 MCP 服务正在运行，等待连接。
2. 立刻获取最近100条日志，判断dorobot是否已成功启动，各个插件加载是否正常。
3. 发送测试消息：使用 `send_message` 方法模拟不同类型的消息，观察 dorobot 的响应和日志输出。

