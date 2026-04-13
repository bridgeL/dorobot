# 架构理解

## 核心概念

- **Plugin** — 普通类，非全局单例。实例化时传入 name、layer、scope 等静态参数。
- **PluginManager** — 全局单例。管理所有插件的注册表（`name → Plugin 实例`）。注册时检测重名，冲突则失败。
- **Session** — 由 session_id 区分。同一插件类在不同 session 中复用同一个实例。
- **SessionManager** — 全局单例。管理所有 Session 实例（`session_id → Session 实例`）。
- **Layer** — 依附于 Session，不是全局单例。每个 Session 有自己独立的 Layer 结构，记录该 session 内各插件的激活状态。
- **Message** — 在 Session 内部流转。按 Layer 顺序传递给各 Plugin，任一 Plugin 返回 `False` 就中断传递。

## 插件开发流程

```python
# 1. 实例化插件，传入静态参数
app = Plugin(name="my_plugin", layer=1, scope="group")

# 2. 注册到插件管理器
app.register()  # 重名时注册失败
```

## 消息路由流程

```
MessageRouter.handle_message(bot_id, message)
  → 设置 context.bot_id、context.session_id
  → session_manager.get_or_create_session(session_id)
  → session.handle_message(message)
      → 按 Layer 0→1→2→3 顺序
      → 每层获取 active_plugins
      → 插件返回 False 则中断传递
```

## Layer 分层规则

| Layer ID | 类型 | 说明 |
|----------|------|------|
| 0 | TYPE_META | 系统保留 |
| 1 | TYPE_SHARED | 共享层，多个插件可同时处理 |
| 2 | TYPE_EXCLUSIVE | 独占层，同一时刻只有一个插件能处理 |
| 3 | TYPE_SHARED | 共享层 |

## 跨 Session 插件挂载

目标：把 Session A 的某个插件 P（scope=group），挂载到私聊 Session B 的 Layer 1 上。

**前提条件：**
- 仅 `scope=group` 的插件可以发起挂载
- 目标必须是私聊 session

**挂载方式：**
- 插件内部方法主动挂载到指定私聊 session_id

**挂载范围：**
- 一个插件可以挂载到多个不同的私聊 session

**激活状态：**
- 挂载后，P 在 Session A 和各私聊 Session 各有一份独立的激活状态
- 挂载本身即在各目标 Session 的 Layer 1 建立路由

**共存规则：**
- P 在 Session B 的 Layer 1，与该层其他插件共存，不互斥

**解除挂载：**
- 方式一：插件内部方法主动调用 `unmount_from_session(session_id)` 解除指定挂载
- 方式二：插件内部方法主动调用 `unmount_from_all()` 一键取消所有挂载
- 方式三：Session A 关闭插件 P 时，自动删除所有私聊 Session 里的路由
- 不需要持久化，纯内存管理
