"""插件基类定义"""

from abc import ABC, abstractmethod
from loguru import logger

from .context import get_bot_id, get_session_id
from .message import Message
from .space import Space


class Plugin(ABC):
    """插件基类

    所有插件必须继承此类并实现相关方法。
    插件是全局独立实例，不绑定特定 session。
    哪个 session 激活了该插件，handle_message 就接收哪个 session。
    """

    def __init__(
        self,
        name: str,
        layer: int = 2,
        description: str = "",
        bots: list[type] | None = None,
        scope: str | None = None,
        default_active: bool = True,
    ):
        """初始化插件

        Args:
            name: 插件名称，唯一标识
            layer: 碰撞层，默认2层（应用层，独占）
            description: 插件描述
            bots: 允许使用该插件的 Bot 类型列表，None 表示允许所有 Bot
            scope: 生效范围，None=全部, "private"=仅私聊, "group"=仅群聊
            default_active: 是否默认激活，默认 True
        """
        self.name = name
        self.layer = layer
        self.description = description
        self.bots = bots
        self.scope = scope  # None=全部, "private"=仅私聊, "group"=仅群聊
        self.default_active = default_active

    @abstractmethod
    async def handle_message(self, message: Message) -> bool:
        """处理消息

        Args:
            message: 消息对象

        Returns:
            bool: True表示继续传递消息到下一层，False表示中断传递
        """
        pass

    async def on_activate(self):
        """插件被激活时调用

        子类可重写此方法，在插件被激活时执行初始化逻辑。
        例如：初始化状态、加载数据等。
        """
        pass

    def on_deactivate(self):
        """插件被关闭时调用

        子类可重写此方法，在插件被关闭时执行清理逻辑。
        例如：保存状态、释放资源等。
        """
        pass

    def get_session(self):
        """获取当前 Session 对象

        插件可以通过此方法获取当前会话，读写 session.data。
        不在消息处理上下文中时返回 None。
        """
        from .session_manager import session_manager

        return session_manager.get_session(get_session_id())

    def get_bot(self):
        """获取当前 Bot 对象

        插件可以通过此方法获取当前 Bot 实例。
        不在消息处理上下文中时返回 None。
        """
        from .bot_manager import bot_manager

        return bot_manager.get_bot(get_bot_id())

    def get_space(self, memory: bool = True):
        """获取当前插件在当前会话的 Space

        每个插件在每个会话都有独立的 Space，可用于存储该会话的数据。
        不在消息处理上下文中时返回 None。

        Args:
            memory: 是否使用内存模式，默认 True。False 则持久化到磁盘。
        """
        session_id = get_session_id()
        if not session_id:
            return None
        return Space(self.name, session_id, memory=memory)

    def matches_context(self, bot, session_type: str) -> bool:
        """检查插件是否应该在当前上下文中处理消息

        Args:
            bot: 当前 Bot 实例，None 表示无 Bot 上下文
            session_type: 会话类型，"group" 或 "private"

        Returns:
            bool: True 表示插件应该处理此消息，False 表示跳过
        """
        # 检查 Bot 类型
        if self.bots is not None and bot is not None:
            if not any(isinstance(bot, bot_type) for bot_type in self.bots):
                return False
        # 检查会话类型
        if self.scope is not None and self.scope != session_type:
            return False
        return True

    async def send_message(
        self, content: str, session_id: str | None = None, bot_id: str | None = None
    ):
        """发送消息到当前会话

        通过 MessageRouter 发送消息。

        Args:
            content: 消息内容
            session_id: 目标会话ID，None 则使用当前上下文中的 session_id
            bot_id: Bot 的唯一标识，None 则从上下文获取
        """
        from .bot_manager import bot_manager

        if bot_id is None:
            bot_id = get_bot_id()

        if not bot_id:
            logger.warning(
                f"Plugin {self.name} has no bot context, cannot send message"
            )
            return

        if session_id is None:
            session_id = get_session_id()

        if not session_id:
            logger.warning(
                f"Plugin {self.name} has no session context, cannot send message"
            )
            return

        # 从 bot_manager 获取 bot 并发送消息
        bot = bot_manager.get_bot(bot_id)
        if bot:
            await bot.send(session_id, content)
        else:
            logger.warning(f"Plugin {self.name}: bot '{bot_id}' not found")
