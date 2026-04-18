"""碰撞层管理"""
from loguru import logger


class Layer:
    """碰撞层

    会话内的一层，记录该层激活了哪些插件（只存插件名称）。
    """

    # 层类型常量
    TYPE_META = "meta"            # meta层
    TYPE_EXCLUSIVE = "exclusive"  # 独占层
    TYPE_SHARED = "shared"        # 共享层

    def __init__(self, layer_id: int, layer_type: str, session_type: str):
        self.layer_id = layer_id
        self.layer_type = layer_type
        self._active_plugins: set[str] = set()  # 激活的插件名称集合
        self._deactive_plugins: set[str] = set()  # 被手动关闭的插件名称集合
        self._populate_plugins(session_type)

    def _populate_plugins(self, session_type: str):
        """根据 session 类型和插件的 default_active 预填充激活/关闭集合"""
        from .plugin_manager import plugin_manager
        for name in plugin_manager.list_plugins():
            plugin = plugin_manager.get_plugin(name)
            if plugin is None:
                continue
            # 检查 scope 是否匹配
            if plugin.scope is not None and plugin.scope != session_type:
                continue
            # 只把插件添加到它注册的对应层
            if plugin.layer != self.layer_id:
                continue
            # 根据 default_active 填充对应集合
            if plugin.default_active:
                self._active_plugins.add(name)
            else:
                self._deactive_plugins.add(name)

    def can_activate(self, plugin_name: str) -> bool:
        """检查是否可以激活指定插件

        - meta层：只允许 meta 插件
        - shared层：随时可以激活（除非被手动关闭）
        - exclusive层：只有当该层没有激活插件时才能激活
        """
        # meta层：只允许 meta 插件
        if self.layer_type == self.TYPE_META:
            return plugin_name == "meta"

        # 被手动关闭的插件不允许激活
        if plugin_name in self._deactive_plugins:
            return False

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
            Exception: 激活失败时抛出
        """
        # meta层：只允许 meta 插件
        if self.layer_type == self.TYPE_META and plugin_name != "meta":
            raise Exception(
                f"第 {self.layer_id} 层是系统保留层，只能激活 meta 插件"
            )

        if plugin_name in self._active_plugins:
            return True  # 已经激活

        # 独占层：如果有其他激活的插件，抛出异常
        if self.layer_type == self.TYPE_EXCLUSIVE and self._active_plugins:
            existing = list(self._active_plugins)[0]
            raise Exception(
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
            Exception: 关闭失败时抛出
        """
        if plugin_name not in self._active_plugins:
            raise Exception(
                f"插件 '{plugin_name}' 未在第 {self.layer_id} 层激活，无需关闭"
            )

        self._active_plugins.discard(plugin_name)
        self._deactive_plugins.add(plugin_name)
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

    def get_all_plugins(self) -> list[str]:
        """获取该层所有插件名称（包括激活和未激活）"""
        return list(self._active_plugins | self._deactive_plugins)

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

    def create_layers(self, session_type: str) -> dict[int, Layer]:
        """根据原型创建所有 layer 实例

        Args:
            session_type: 会话类型，"group" 或 "private"

        Returns:
            dict[int, Layer]: layer_id -> Layer 实例的字典
        """
        return {
            layer_id: Layer(layer_id, layer_type, session_type)
            for layer_id, layer_type in self._layers.items()
        }

    def get_layer_type(self, layer_id: int) -> str | None:
        """获取指定层 ID 的类型

        Args:
            layer_id: 层ID

        Returns:
            str: 层类型（TYPE_META/TYPE_EXCLUSIVE/TYPE_SHARED），不存在则返回 None
        """
        return self._layers.get(layer_id)


# 全局 Layer 原型实例
layer_prototype = LayerPrototype()
