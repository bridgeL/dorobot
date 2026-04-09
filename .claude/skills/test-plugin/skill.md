---
name: test-plugin
description: 当你开发插件时，需要测试插件效果，给予你调试插件的能力。AITestAdapter 是一个专门用于测试的适配器，提供了一个 HTTP 接口，你可以通过 curl 发送 HTTP 请求来模拟用户消息，查看插件处理效果。
---

# test-plugin 使用指南

## 启动服务
请用户自行启动服务
```bash
python test_server.py
```
服务监听地址：`localhost:18765`

## 调试准备
1. 首先要确认插件的名字
2. 然后要读取插件代码确认它的结构和功能
3. 确保用户已经启动test_server.py

## 常用接口
```bash
# 健康检查
curl http://localhost:18765/health

# 查看会话
curl http://localhost:18765/sessions
```

## 发送消息
```bash
curl -X POST http://localhost:18765/msg \
  --data-urlencode "session_id=group.test123" \
  --data-urlencode "sender_id=u1" \
  --data-urlencode "sender_name=小明" \
  --data-urlencode "content=消息内容"
```
- 必须用 `--data-urlencode` 避免中文参数乱码。
- content中的任何`/`都需要先转义为`//`，这是因为在Bash中直接使用`/`可能会被解析器误认为是路径。

## 插件管理（/meta 命令）
```bash
# 查看插件状态
content=//meta

# 激活/关闭插件
content=//meta 插件名
```

## 查看最近日志
- `/log?count=10` 查看最近10条日志

各个接口会返回status: ok，但是这只意味着接口调用成功，并不代表插件处理成功。请务必使用/log 查看日志，确认插件是否正确处理了消息。

## 测试私聊
- 私聊测试用 `session_id=private.user1`
