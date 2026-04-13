"""异步上下文管理

使用 contextvars 保存当前请求上下文（bot_id, session_id等），
使插件在处理消息时可以方便地获取这些信息。
"""
from contextvars import ContextVar

# 当前 Bot ID
bot_id: ContextVar[str] = ContextVar("bot_id", default="")

# 当前 Session ID
session_id: ContextVar[str] = ContextVar("session_id", default="")

# 当前 Dorobot 实例
_dorobot: ContextVar["Dorobot"] = ContextVar("dorobot", default=None)


def get_bot_id() -> str:
    """获取当前 Bot ID"""
    return bot_id.get()


def get_session_id() -> str:
    """获取当前 Session ID"""
    return session_id.get()


def set_dorobot(dorobot: "Dorobot"):
    """设置当前 Dorobot 实例"""
    _dorobot.set(dorobot)


def get_dorobot() -> "Dorobot":
    """获取当前 Dorobot 实例"""
    return _dorobot.get()
