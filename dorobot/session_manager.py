"""会话管理器 - 管理多个会话的创建、获取和销毁"""
from typing import Optional
from loguru import logger

from .session import Session
from .plugin_manager import plugin_manager
from . import context as ctx


def get_current_session() -> Optional[Session]:
    """获取当前上下文中的 Session

    在消息处理过程中，插件可以通过此函数获取当前会话对象，
    用于读写 session.data。

    Returns:
        Session | None: 当前会话对象，不在消息处理上下文中则返回 None
    """
    return ctx.current_session.get()


class SessionManager:
    """会话管理器

    管理所有会话的生命周期：
    - 创建新会话
    - 获取已有会话
    - 销毁会话
    - 管理每个会话的插件激活状态
    """

    def __init__(self):
        """初始化会话管理器"""
        self._sessions: dict[str, Session] = {}  # f"{bot_id}:{session_id}" -> Session

    def _make_key(self, bot_id: str, session_id: str) -> str:
        """生成会话存储键"""
        return f"{bot_id}:{session_id}"

    def get_session(self, bot_id: str, session_id: str) -> Optional[Session]:
        """获取会话（不创建）

        Args:
            bot_id: Bot 的唯一标识
            session_id: 会话ID

        Returns:
            Session | None: 会话对象，不存在则返回 None
        """
        key = self._make_key(bot_id, session_id)
        return self._sessions.get(key)

    async def get_or_create_session(self, bot_id: str, session_id: str) -> Session:
        """获取或创建会话

        新会话会自动激活0层、1层和3层的所有插件。

        Args:
            bot_id: Bot 的唯一标识
            session_id: 会话ID

        Returns:
            Session: 会话对象
        """
        key = self._make_key(bot_id, session_id)
        if key not in self._sessions:
            self._sessions[key] = Session(session_id, bot_id)
            logger.info(f"Created new session: {key}")
            # 自动激活 0层、1层、3层的所有插件
            await self._auto_activate_shared_plugins(self._sessions[key])
        return self._sessions[key]

    async def _auto_activate_shared_plugins(self, session: Session):
        """自动激活共享层（0、1、3层）的所有插件"""
        for layer_id in (0, 1, 3):
            plugin_names = plugin_manager.get_plugins_by_layer(layer_id)
            for name in plugin_names:
                if plugin_manager.get_plugin(name):  # 确保插件实例存在
                    await session.activate_plugin(name, layer_id, silent=True)

    def remove_session(self, bot_id: str, session_id: str) -> bool:
        """移除会话

        Args:
            bot_id: Bot 的唯一标识
            session_id: 会话ID

        Returns:
            bool: 是否成功移除
        """
        key = self._make_key(bot_id, session_id)
        if key not in self._sessions:
            return False

        session = self._sessions[key]
        session.deactivate_all_plugins()
        del self._sessions[key]
        logger.info(f"Removed session: {key}")
        return True

    def list_sessions(self, bot_id: Optional[str] = None) -> list[str]:
        """列出所有会话

        Args:
            bot_id: 如果指定，只返回该 bot 的会话

        Returns:
            list[str]: 会话 key 列表（格式：bot_id:session_id）
        """
        if bot_id:
            return [k for k in self._sessions.keys() if k.startswith(f"{bot_id}:")]
        return list(self._sessions.keys())

    async def activate_plugin(self, bot_id: str, session_id: str, plugin_name: str, layer_id: int) -> bool:
        """在指定会话中激活插件

        Args:
            bot_id: Bot 的唯一标识
            session_id: 会话ID
            plugin_name: 插件名称（需已注册到PluginManager）
            layer_id: 层ID

        Returns:
            bool: 是否成功激活
        """
        session = self.get_session(bot_id, session_id)
        if not session:
            logger.warning(f"Session {bot_id}:{session_id} not found")
            return False

        # 检查插件是否已注册
        if not plugin_manager.get_plugin(plugin_name):
            logger.warning(f"Plugin {plugin_name} not found in registry")
            return False

        return await session.activate_plugin(plugin_name, layer_id)

    def deactivate_plugin(self, bot_id: str, session_id: str, plugin_name: str, layer_id: int) -> bool:
        """在指定会话中关闭插件"""
        session = self.get_session(bot_id, session_id)
        if not session:
            return False
        return session.deactivate_plugin(plugin_name, layer_id)

    def get_active_plugins(self, bot_id: str, session_id: str) -> dict[int, list[str]]:
        """获取指定会话中激活的插件"""
        session = self.get_session(bot_id, session_id)
        if not session:
            return {}
        return session.get_active_plugins_info()

    def __repr__(self):
        return f"SessionManager(sessions={list(self._sessions.keys())})"


# 全局 SessionManager 实例（懒加载）
_session_manager_instance: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """获取全局 SessionManager 实例"""
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = SessionManager()
    return _session_manager_instance
