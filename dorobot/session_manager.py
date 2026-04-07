"""会话管理器 - 管理多个会话的创建、获取和销毁"""
from typing import Optional
from loguru import logger

from dorobot.session import Session


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
        self._sessions: dict[str, Session] = {}  # session_id -> Session

    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话（不创建）

        Args:
            session_id: 会话ID

        Returns:
            Session | None: 会话对象，不存在则返回 None
        """
        return self._sessions.get(session_id)

    async def get_or_create_session(self, session_id: str, type: str = "private", group_id: str = "", user_id: str = "") -> Session:
        """获取或创建会话

        新会话会自动激活0层、1层和3层的所有插件。

        Args:
            session_id: 会话ID
            type: 会话类型，"group" 或 "private"
            group_id: 群号（仅群聊有效）
            user_id: 用户 ID

        Returns:
            Session: 会话对象
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id, type, group_id, user_id)
            logger.debug(f"Created new session: {session_id} ({type})")
        return self._sessions[session_id]

    def remove_session(self, session_id: str) -> bool:
        """移除会话

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否成功移除
        """
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]
        session.deactivate_all_plugins()
        del self._sessions[session_id]
        logger.info(f"Removed session: {session_id}")
        return True

    def list_sessions(self) -> list[str]:
        """列出所有会话

        Returns:
            list[str]: 会话ID列表
        """
        return list(self._sessions.keys())

    def get_active_plugins(self, session_id: str) -> dict[int, list[str]]:
        """获取指定会话中激活的插件"""
        session = self.get_session(session_id)
        if not session:
            return {}
        return session.get_active_plugins_info()

    def __repr__(self):
        return f"SessionManager(sessions={list(self._sessions.keys())})"


# 全局 SessionManager 实例
session_manager = SessionManager()
