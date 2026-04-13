"""会话管理器 - 管理多个会话的创建、获取和销毁"""
from typing import Optional
from loguru import logger

from .session import Session


class SessionManager:
    """会话管理器

    管理所有会话的生命周期：
    - 创建新会话
    - 获取已有会话
    - 销毁会话
    - 管理每个会话的插件激活状态
    - 跨 session 插件挂载
    """

    def __init__(self, dorobot: "Dorobot"):
        """初始化会话管理器"""
        self._dorobot = dorobot
        self._sessions: dict[str, Session] = {}  # session_id -> Session
        # 跨 session 挂载记录：plugin_name -> set of target session_id
        self._mounts: dict[str, set[str]] = {}

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
            self._sessions[session_id] = Session(session_id, type, group_id, user_id, self._dorobot)
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

    # === 跨 session 插件挂载 ===

    async def mount_plugin(self, plugin_name: str, target_session_id: str, parent_session_id: str | None = None) -> bool:
        """将插件挂载到目标 session 的 Layer 1（自动创建不存在的 session）

        Args:
            plugin_name: 插件名称
            target_session_id: 目标私聊 session_id
            parent_session_id: 父 session ID（调用 mount 时所在的 session）

        Returns:
            bool: 是否挂载成功
        """
        # 获取或创建目标 session
        target_session = await self.get_or_create_session(target_session_id, type="private")

        # 在目标 session 的 Layer 1 激活插件
        try:
            layer = target_session.get_layer(1)
            if not layer:
                logger.warning(f"[SessionManager] mount_plugin: layer 1 not found in session {target_session_id}")
                return False
            layer.activate_plugin(plugin_name, target_session_id, silent=True)
        except Exception as e:
            logger.warning(f"[SessionManager] mount_plugin failed: {e}")
            return False

        # 记录挂载关系
        if plugin_name not in self._mounts:
            self._mounts[plugin_name] = set()
        self._mounts[plugin_name].add(target_session_id)

        # 将父 session ID 写入子 session 的 space（让 mounted 插件能访问主 session 数据）
        if parent_session_id:
            from .plugin import Space
            child_space = Space(plugin_name, target_session_id, memory=True)
            child_space[f"_parent_space_{plugin_name}_"] = parent_session_id

        logger.debug(f"[SessionManager] Plugin({plugin_name}) mounted to session {target_session_id}")
        return True

    def unmount_plugin(self, plugin_name: str, target_session_id: str) -> bool:
        """将插件从目标 session 卸载

        Args:
            plugin_name: 插件名称
            target_session_id: 目标 session_id

        Returns:
            bool: 是否卸载成功
        """
        target_session = self._sessions.get(target_session_id)
        if not target_session:
            return False

        try:
            layer = target_session.get_layer(1)
            if layer:
                layer.deactivate_plugin(plugin_name, target_session_id)
        except Exception as e:
            logger.warning(f"[SessionManager] unmount_plugin failed: {e}")
            return False

        # 移除挂载记录
        if plugin_name in self._mounts:
            self._mounts[plugin_name].discard(target_session_id)
            if not self._mounts[plugin_name]:
                del self._mounts[plugin_name]

        logger.debug(f"[SessionManager] Plugin({plugin_name}) unmounted from session {target_session_id}")
        return True

    def unmount_plugin_all(self, plugin_name: str):
        """取消插件的所有挂载

        Args:
            plugin_name: 插件名称
        """
        if plugin_name not in self._mounts:
            return

        for target_session_id in list(self._mounts[plugin_name]):
            self.unmount_plugin(plugin_name, target_session_id)

    def __repr__(self):
        return f"SessionManager(sessions={list(self._sessions.keys())})"
