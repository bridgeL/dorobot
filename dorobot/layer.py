"""碰撞层管理"""
from loguru import logger


class LayerError(Exception):
    """Layer 操作异常基类"""
    pass


class PluginActivationError(LayerError):
    """插件激活失败异常"""
    pass


class PluginDeactivationError(LayerError):
    """插件关闭失败异常"""
    pass


class Layer:
    """碰撞层

    会话内的一层，记录该层激活了哪些插件（只存插件名称）。
    """

    # 层类型常量
    TYPE_META = "meta"            # meta层
    TYPE_EXCLUSIVE = "exclusive"  # 独占层
    TYPE_SHARED = "shared"        # 共享层

    def __init__(self, layer_id: int, layer_type: str):
        self.layer_id = layer_id
        self.layer_type = layer_type
        self._active_plugins: set[str] = set()  # 激活的插件名称集合

    def can_activate(self, plugin_name: str) -> bool:
        """检查是否可以激活指定插件

        - meta层：只允许 meta 插件
        - shared层：随时可以激活
        - exclusive层：只有当该层没有激活插件时才能激活
        """
        # meta层：只允许 meta 插件
        if self.layer_type == self.TYPE_META:
            return plugin_name == "meta"

        # shared层：允许多个
        if self.layer_type == self.TYPE_SHARED:
            return True

        # exclusive层：只能激活一个
        return len(self._active_plugins) == 0

    def activate_plugin(self, plugin_name: str, session_id: str = "", silent: bool = False) -> bool:
        """激活指定插件

        对于独占层（exclusive），如果该层已有其他激活的插件，抛出异常

        Args:
            plugin_name: 要激活的插件名称
            session_id: 会话ID，用于日志
            silent: 是否静默（不输出日志），用于自动激活

        Returns:
            bool: 是否成功激活（True表示成功，已激活也返回True）

        Raises:
            PluginActivationError: 激活失败时抛出
        """
        # meta层：只允许 meta 插件
        if self.layer_type == self.TYPE_META and plugin_name != "meta":
            raise PluginActivationError(
                f"第 {self.layer_id} 层是系统保留层，只能激活 meta 插件"
            )

        if plugin_name in self._active_plugins:
            return True  # 已经激活

        # 独占层：如果有其他激活的插件，抛出异常
        if self.layer_type == self.TYPE_EXCLUSIVE and self._active_plugins:
            existing = list(self._active_plugins)[0]
            raise PluginActivationError(
                f"第 {self.layer_id} 层已被插件 '{existing}' 占用，请先关闭它再激活 '{plugin_name}'"
            )

        self._active_plugins.add(plugin_name)
        if not silent:
            logger.debug(f"[Layer] Plugin({plugin_name}) activated in layer {self.layer_id}, session {session_id}")
        return True

    def deactivate_plugin(self, plugin_name: str, session_id: str = "") -> bool:
        """关闭指定插件

        Returns:
            bool: 是否成功关闭

        Raises:
            PluginDeactivationError: 关闭失败时抛出
        """
        if plugin_name not in self._active_plugins:
            raise PluginDeactivationError(
                f"插件 '{plugin_name}' 未在第 {self.layer_id} 层激活，无需关闭"
            )

        self._active_plugins.discard(plugin_name)
        logger.debug(f"[Layer] Plugin({plugin_name}) deactivated in layer {self.layer_id}, session {session_id}")
        return True

    def deactivate_all(self):
        """关闭该层所有插件（meta层除外）"""
        if self.layer_type == self.TYPE_META:
            return  # meta层无法关闭

        for name in list(self._active_plugins):
            self.deactivate_plugin(name)
        logger.debug(f"Layer {self.layer_id}: all plugins deactivated")

    def get_active_plugins(self) -> list[str]:
        """获取该层所有激活的插件名称"""
        return list(self._active_plugins)

    def is_plugin_active(self, plugin_name: str) -> bool:
        """检查指定插件是否在该层激活"""
        return plugin_name in self._active_plugins

    def __repr__(self):
        return f"Layer({self.layer_id}, active={list(self._active_plugins)})"


class LayerPrototype:
    """Layer 原型管理

    预定义 layer 结构原型，新 Session 创建时从此原型复制 layer。
    默认包含 4 层：
    - 0: meta
    - 1: shared
    - 2: exclusive
    - 3: shared
    """

    def __init__(self):
        # 层ID -> 层类型 的映射
        self._layers: dict[int, str] = {
            0: Layer.TYPE_META,       # meta层
            1: Layer.TYPE_SHARED,     # 共享层
            2: Layer.TYPE_EXCLUSIVE,  # 独占层
            3: Layer.TYPE_SHARED,     # 共享层
        }

    def create_layers(self) -> dict[int, Layer]:
        """根据原型创建所有 layer 实例

        Returns:
            dict[int, Layer]: layer_id -> Layer 实例的字典
        """
        return {
            layer_id: Layer(layer_id, layer_type)
            for layer_id, layer_type in self._layers.items()
        }


# 全局 Layer 原型实例
layer_prototype = LayerPrototype()
