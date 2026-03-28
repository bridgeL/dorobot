"""插件注册中心

管理所有插件的全局注册和配置。
"""
from typing import Dict, List, Optional
from loguru import logger

from dorobot.plugin import Plugin


class PluginManager:
    """插件注册中心

    管理所有可用插件的全局注册和配置。
    插件是全局单例实例，被多个 Session 共享。
    """

    def __init__(self):
        self._plugin_instances: Dict[str, Plugin] = {}  # name -> Plugin instance (singleton)

    def register(self, name: str, plugin_instance: Plugin) -> bool:
        """注册插件实例

        Args:
            name: 插件唯一名称
            plugin_instance: 插件实例

        Returns:
            bool: 是否注册成功
        """
        if name in self._plugin_instances:
            logger.warning(f"Plugin {name} already registered")
            return False

        self._plugin_instances[name] = plugin_instance
        logger.info(f"Registered plugin: {name} (layer={plugin_instance.layer}) - {plugin_instance.description}")
        return True

    def unregister(self, name: str) -> bool:
        """注销插件"""
        if name not in self._plugin_instances:
            return False
        del self._plugin_instances[name]
        logger.info(f"Unregistered plugin: {name}")
        return True

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
            return {"layer": plugin.layer, "description": plugin.description}
        return None

    def list_plugins(self) -> List[str]:
        """列出所有已注册的插件名称"""
        return list(self._plugin_instances.keys())

    def get_plugins_by_layer(self, layer: int) -> List[str]:
        """获取指定层的所有插件名称"""
        result = []
        for name, plugin in self._plugin_instances.items():
            if plugin.layer == layer:
                result.append(name)
        return result

    def clear(self):
        """清空所有注册信息"""
        self._plugin_instances.clear()
        logger.info("Plugin registry cleared")


# 全局注册中心实例
plugin_manager = PluginManager()


def register_plugin(name: str, layer: int = 0, description: str = ""):
    """装饰器：注册插件类

    使用示例：
        @register_plugin("echo", layer=0, description="回声插件")
        class EchoPlugin(Plugin):
            async def handle_message(self, message):
                await self.send_message(message.content)
                return True
    """
    def decorator(cls):
        # 立即创建插件实例并注册
        instance = cls(name=name, layer=layer, description=description)
        plugin_manager.register(name, instance)
        return cls
    return decorator
