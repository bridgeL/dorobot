"""插件注册中心

管理所有插件的全局注册和配置。
"""
from typing import Dict, List, Optional, Type
from loguru import logger

from dorobot.plugin import Plugin


class PluginManager:
    """插件注册中心

    管理所有可用插件的全局注册和配置。
    插件是全局单例实例，被多个 Session 共享。
    """

    _instance = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._plugin_classes: Dict[str, Type[Plugin]] = {}  # name -> PluginClass
        self._plugin_metadata: Dict[str, dict] = {}  # name -> {layer, description, ...}
        self._plugin_instances: Dict[str, Plugin] = {}  # name -> Plugin instance (singleton)
        self._initialized = True

    def register(self, name: str, plugin_class: Type[Plugin], layer: int = 0,
                 description: str = "", **metadata) -> bool:
        """注册插件类

        Args:
            name: 插件唯一名称
            plugin_class: 插件类（必须继承Plugin）
            layer: 默认碰撞层
            description: 插件描述
            **metadata: 其他元数据

        Returns:
            bool: 是否注册成功
        """
        if name in self._plugin_classes:
            logger.warning(f"Plugin {name} already registered")
            return False

        if not issubclass(plugin_class, Plugin):
            logger.error(f"Plugin class {plugin_class.__name__} must inherit from Plugin")
            return False

        self._plugin_classes[name] = plugin_class
        self._plugin_metadata[name] = {
            "layer": layer,
            "description": description,
            **metadata
        }
        logger.success(f"Registered plugin: {name} (layer={layer}) - {description}")
        return True

    def unregister(self, name: str) -> bool:
        """注销插件"""
        if name not in self._plugin_classes:
            return False
        del self._plugin_classes[name]
        del self._plugin_metadata[name]
        logger.info(f"Unregistered plugin: {name}")
        return True

    def create_plugin(self, name: str, **kwargs) -> Optional[Plugin]:
        """创建插件实例

        Args:
            name: 插件名称
            **kwargs: 传递给插件构造函数的参数

        Returns:
            Plugin实例或None
        """
        plugin_class = self._plugin_classes.get(name)
        if not plugin_class:
            logger.warning(f"Plugin {name} not found in registry")
            return None

        metadata = self._plugin_metadata.get(name, {})
        layer = kwargs.pop("layer", metadata.get("layer", 0))

        # 使用name参数（如果提供）或默认name
        instance_name = kwargs.pop("name", name)

        return plugin_class(name=instance_name, layer=layer, **kwargs)

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取插件实例（单例）

        如果实例不存在，会自动创建并缓存。

        Args:
            name: 插件名称

        Returns:
            Plugin实例或None
        """
        # 如果已存在实例，直接返回
        if name in self._plugin_instances:
            return self._plugin_instances[name]

        # 创建新实例并缓存
        plugin = self.create_plugin(name)
        if plugin:
            self._plugin_instances[name] = plugin
        return plugin

    def init_all_plugins(self):
        """初始化所有已注册插件的单例实例"""
        for name in self._plugin_classes:
            if name not in self._plugin_instances:
                self.get_plugin(name)

    def get_plugin_class(self, name: str) -> Optional[Type[Plugin]]:
        """获取插件类"""
        return self._plugin_classes.get(name)

    def get_plugin_metadata(self, name: str) -> Optional[dict]:
        """获取插件元数据"""
        return self._plugin_metadata.get(name)

    def list_plugins(self) -> List[str]:
        """列出所有已注册的插件名称"""
        return list(self._plugin_classes.keys())

    def get_plugins_by_layer(self, layer: int) -> List[str]:
        """获取指定层的所有插件名称"""
        result = []
        for name, metadata in self._plugin_metadata.items():
            if metadata.get("layer") == layer:
                result.append(name)
        return result

    def clear(self):
        """清空所有注册信息"""
        self._plugin_classes.clear()
        self._plugin_metadata.clear()
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
        plugin_manager.register(name, cls, layer=layer, description=description)
        return cls
    return decorator
