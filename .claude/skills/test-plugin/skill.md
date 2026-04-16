---
name: test-plugin
description: 插件调试专用工具，通过 MCP 调用测试服务，一键模拟消息、查看日志、管理插件
---

# 测试插件调试指南

## 调试流程建议

1. 启动 MCP 服务：确保 MCP 服务正在运行，等待连接。
2. 阅读插件以了解该插件有哪些命令
3. 立刻获取最近100条日志，判断dorobot是否已成功启动，各个插件加载是否正常。
4. 发送测试消息：使用 `send_message` 方法模拟不同类型的消息，观察 dorobot 的响应和日志输出。

- 当你修改了代码后，应该重启dorobot来使改动生效
- 必须使用MCP调试插件，不得使用python脚本文件来调试

## MCP 提供的能力

`start_dorobot` 启动 dorobot
`stop_dorobot` 关闭 dorobot
`get_logs` 查看最新n条日志 
`send_message` 模拟dorobot系统收到来自于某个群聊某个用户的消息，或者来自于某个用户的私聊消息

## send_message 发送的消息格式

包含如下字段：
- session_type: 会话类型（"group" 或 "private"）
- target_id: 目标ID（群号或用户ID）（建议格式：group.12345, private.1001）
- sender_id: 发送者ID（建议格式：1001）
- sender_name: 发送者昵称（建议格式：玩家A）
- content: 消息内容

## 如何开启/关闭插件

dorobot内置有插件管理功能，当使用`send_message`发生的消息内容以`/meta 插件名`开头时，会被识别为插件管理指令，用于开启或关闭指定插件。

- `/meta hello`：开启/关闭名为hello插件
- `/meta echo`：开启/关闭名为echo插件
- `/meta`：列出所有插件及其状态
