"""插件注册中心

管理所有插件的全局注册和配置。
"""
from typing import Optional
from loguru import logger

from .plugin import Plugin
from .layer import Layer, layer_prototype


class PluginManager:
    """插件注册中心

    管理所有可用插件的全局注册和配置。
    插件是全局单例实例，被多个 Session 共享。
    """

    def __init__(self):
        self._plugin_instances: dict[str, Plugin] = {}  # name -> Plugin instance (singleton)

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

        # 通过 layer_prototype 获取该层的类型
        layer_type = layer_prototype.get_layer_type(plugin_instance.layer)

        # meta层 最多只允许注册一个插件
        if layer_type == Layer.TYPE_META:
            for p in self._plugin_instances.values():
                if layer_prototype.get_layer_type(p.layer) == Layer.TYPE_META:
                    logger.warning(f"Plugin {name}: meta layer already has plugin '{p.name}', cannot register second")
                    return False

        # 独占层 注册插件的 default_active 必须为 False
        if layer_type == Layer.TYPE_EXCLUSIVE and plugin_instance.default_active:
            logger.warning(f"Plugin {name}: exclusive layer cannot have default_active=True")
            return False

        self._plugin_instances[name] = plugin_instance
        logger.info(f"Registered Plugin: {name}")
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
            return {"layer": plugin.layer, "description": plugin.description, "bots": plugin.bots, "scope": plugin.scope}
        return None

    def list_plugins(self) -> list[str]:
        """列出所有已注册的插件名称"""
        return list(self._plugin_instances.keys())


# 全局单例
plugin_manager = PluginManager()
