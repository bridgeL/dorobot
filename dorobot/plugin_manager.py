"""插件注册中心

管理所有插件的全局注册和配置。
"""
from typing import Optional
from loguru import logger

from .plugin import Plugin


class PluginManager:
    """插件注册中心

    管理所有可用插件的全局注册和配置。
    插件是全局单例实例，被多个 Session 共享。
    """

    def __init__(self):
        self._plugin_instances: dict[str, Plugin] = {}  # name -> Plugin instance (singleton)

    def register(self, name: str, plugin_instance: Plugin, active: bool = True) -> bool:
        """注册插件实例

        Args:
            name: 插件唯一名称
            plugin_instance: 插件实例
            active: 是否自动激活，默认 True

        Returns:
            bool: 是否注册成功
        """
        if name in self._plugin_instances:
            logger.warning(f"Plugin {name} already registered")
            return False

        self._plugin_instances[name] = plugin_instance
        logger.info(f"Registered Plugin: {name}")

        # 自动激活
        if active:
            self._activate_all(name, plugin_instance.layer)

        return True

    def _activate_all(self, plugin_name: str, layer_id: int):
        """在所有已有 session 中激活插件"""
        from .session_manager import session_manager
        for session_id in session_manager.list_sessions():
            session = session_manager.get_session(session_id)
            if session:
                layer = session.get_layer(layer_id)
                if layer and layer.can_activate(plugin_name):
                    layer.activate_plugin(plugin_name, session.session_id, silent=True)

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取插件实例（单例）

        Args:
            name: 插件名称

        Returns:
            Plugin实例或None
        """
        return self._plugin_instances.get(name)

    def get_plugin_metadata(self, name: str) -> Optional[dict]:
        """获取插件元数据"""
        plugin = self._plugin_instances.get(name)
        if plugin:
            return {"layer": plugin.layer, "description": plugin.description, "bots": plugin.bots, "scope": plugin.scope}
        return None

    def list_plugins(self) -> list[str]:
        """列出所有已注册的插件名称"""
        return list(self._plugin_instances.keys())

    def get_plugins_by_layer(self, layer: int) -> list[str]:
        """获取指定层的所有插件名称"""
        result = []
        for name, plugin in self._plugin_instances.items():
            if plugin.layer == layer:
                result.append(name)
        return result



# 全局注册中心实例
plugin_manager = PluginManager()


def register_plugin(name: str, layer: int = 0, description: str = "", bots: list[type] | None = None, scope: str | None = None, active: bool = False):
    """装饰器：注册插件类

    使用示例：
        @register_plugin("echo", layer=0, description="回声插件")
        class EchoPlugin(Plugin):
            async def handle_message(self, message):
                await self.send_message(message.content)
                return True

    Args:
        name: 插件唯一名称
        layer: 碰撞层，默认0层
        description: 插件描述
        bots: 允许使用该插件的 Bot 类型列表
        scope: 生效范围，None=全部, "private"=仅私聊, "group"=仅群聊
        active: 是否默认激活，默认 False
    """
    def decorator(cls: type[Plugin]):
        # 立即创建插件实例并注册
        instance = cls(name=name, layer=layer, description=description, bots=bots, scope=scope, default_active=active)
        plugin_manager.register(name, instance, active=active)
        return cls
    return decorator
