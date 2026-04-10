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
2. 然后要读取插件代码确认它的结构和功能，注意，对于layer=2的插件，一般要先启动它才能测试它的功能
3. 确保用户已经启动test_server.py

## 健康检查
```bash
curl http://localhost:18765/health
```

## 模拟用户发送消息
```bash
curl -X POST http://localhost:18765/msg \
  --data-urlencode "session_id=group.test123" \
  --data-urlencode "sender_id=u1" \
  --data-urlencode "sender_name=小明" \
  --data-urlencode "content=消息内容"
```
- 必须用 `--data-urlencode` 避免中文参数乱码。
- content中的任何`/`都需要先转义为`//`，这是因为在Bash中直接使用`/`可能会被解析器误认为是路径。
- 发送消息后，接口会返回最近10条日志。如果你需要更多信息可以调用 `/log?count=N` 接口查看更多日志。

## 查看最近日志
```bash
curl http://localhost:18765/log?count=50
```

## 插件管理（/meta 命令）
```bash
# 查看插件状态
content=//meta

# 激活/关闭插件
content=//meta 插件名
```

## 模拟不同类型的会话
- 群聊测试用 `session_id=group.group1`
- 私聊测试用 `session_id=private.user1`
