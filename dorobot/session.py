"""会话 - 单个会话的数据和状态管理"""

from typing import Optional
import asyncio
from loguru import logger

import dorobot.context as ctx
from dorobot.plugin import Plugin, Message
from dorobot.layer import (
    Layer,
    layer_prototype,
    PluginActivationError,
    PluginDeactivationError,
)
from dorobot.plugin_manager import plugin_manager
from dorobot.bot_manager import bot_manager


class Session:
    """会话

    每个会话对应一个 Session 实例。
    会话内有多层结构，每层可以激活多个插件。
    - 0层（meta层）：只有 meta plugin，无法关闭
    - 1层（命令层）：共享层，可激活多个插件
    - 2层（应用层）：独占层，只能激活1个插件
    - 3层（共享层）：共享层，可激活多个插件

    Session 只记录哪些插件被激活（激活记录），不拥有插件实例。
    插件实例是全局共享的，通过 PluginManager 获取。
    """

    def __init__(self, session_id: str):
        """
        Args:
            session_id: 会话唯一标识（如群聊ID、频道ID）
        """
        self.session_id = session_id
        # 从原型复制 layer 结构
        self._layers: dict[int, Layer] = layer_prototype.create_layers()
        self.data: dict = {}  # 会话数据存储，插件可读写

    def _get_layer(self, layer_id: int) -> Layer | None:
        """获取指定层（如果不存在返回 None）"""
        return self._layers.get(layer_id)

    async def activate_plugin(
        self, plugin_name: str, layer_id: int, silent: bool = False
    ) -> bool:
        """激活指定插件

        Args:
            plugin_name: 插件名称
            layer_id: 层ID
            silent: 是否静默（不输出日志），用于自动激活

        Returns:
            bool: 是否成功激活

        Raises:
            PluginActivationError: 激活失败时抛出
        """
        layer = self._get_layer(layer_id)
        if layer is None:
            raise PluginActivationError(
                f"会话中不存在第 {layer_id} 层"
            )
        result = layer.activate_plugin(plugin_name, self.session_id, silent=silent)
        if result:
            # 调用插件的 on_activate 方法
            plugin = plugin_manager.get_plugin(plugin_name)
            if plugin:
                try:
                    await plugin.on_activate()
                except Exception as e:
                    logger.error(f"Plugin {plugin_name} on_activate failed: {e}")
        return result

    def deactivate_plugin(self, plugin_name: str, layer_id: int) -> bool:
        """关闭指定插件

        Args:
            plugin_name: 插件名称
            layer_id: 层ID

        Returns:
            bool: 是否成功关闭

        Raises:
            PluginDeactivationError: 关闭失败时抛出
        """
        layer = self._layers.get(layer_id)
        if not layer:
            raise PluginDeactivationError(
                f"会话中不存在第 {layer_id} 层"
            )
        result = layer.deactivate_plugin(plugin_name, self.session_id)
        return result

    def deactivate_all_plugins(self):
        """关闭所有插件"""
        for layer in self._layers.values():
            layer.deactivate_all()
        logger.info(f"All plugins deactivated in session {self.session_id}")

    async def handle_message(self, message: Message) -> bool:
        """处理消息

        从0层开始，依次向后传递消息给激活的插件。
        同一层的激活插件会同时收到消息并处理。
        如果任一插件返回False，则中断消息传递。

        Args:
            message: 消息对象

        Returns:
            bool: 消息是否被完全处理（True=没有被拦截，False=被某层拦截）
        """
        sorted_layers = self.get_all_layers()

        for layer in sorted_layers:
            active_plugin_names = set(layer.get_active_plugins())
            # 获取该层所有插件
            all_plugin_names = set(
                plugin_manager.get_plugins_by_layer(layer.layer_id)
            )
            inactive_plugin_names = all_plugin_names - active_plugin_names

            logger.debug(
                f"[Session] Layer {layer.layer_id}: 激活={list(active_plugin_names)}, 未激活={list(inactive_plugin_names)}"
            )

            if not active_plugin_names:
                continue

            # 获取插件实例（从全局注册中心）
            active_plugins: list[Plugin] = []
            for name in active_plugin_names:
                plugin = plugin_manager.get_plugin(name)
                if plugin:
                    # 检查插件是否允许当前 Bot 类型
                    if plugin.bots is not None:
                        current_bot_id = ctx.get_bot_id()
                        current_bot = bot_manager.get_bot(current_bot_id) if current_bot_id else None
                        if current_bot:
                            # 检查当前 Bot 实例是否属于插件允许的类型
                            if not any(isinstance(current_bot, bot_type) for bot_type in plugin.bots):
                                logger.debug(f"[Session] Plugin({name}) skipped for bot type {type(current_bot).__name__}")
                                continue
                    active_plugins.append(plugin)
                else:
                    logger.warning(
                        f"[Session] Plugin({name}) is activated but not found in registry"
                    )

            if not active_plugins:
                continue

            # 同一层的激活插件同时处理消息
            tasks = [plugin.handle_message(message) for plugin in active_plugins]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 检查是否有插件要求中断
            for i, result in enumerate(results):
                plugin_name = list(active_plugin_names)[i]
                if isinstance(result, Exception):
                    logger.error(
                        f"[Session] Plugin({plugin_name}) raised exception: {result}"
                    )
                    continue
                if result is False:
                    logger.debug(
                        f"[Session] Plugin({plugin_name}) blocked message at layer {layer.layer_id}"
                    )
                    return False

        logger.debug(
            f"[Session] Message passed through all layers in session {self.session_id}"
        )
        return True

    def get_layer(self, layer_id: int) -> Optional[Layer]:
        """获取指定层"""
        return self._layers.get(layer_id)

    def get_all_layers(self) -> list[Layer]:
        """获取所有层（按层ID排序）"""
        return [self._layers[k] for k in sorted(self._layers.keys())]

    def get_active_plugins_info(self) -> dict[int, list[str]]:
        """获取当前激活的插件信息"""
        result = {}
        for layer_id, layer in self._layers.items():
            active = layer.get_active_plugins()
            if active:
                result[layer_id] = active
        return result

    def __repr__(self):
        return f"Session({self.session_id}, layers={list(self._layers.keys())})"
