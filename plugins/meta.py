"""Meta 插件 - 用于管理其他插件的激活/关闭

位于 0 层，负责处理 /meta 插件名 格式的命令，用于激活或关闭 1 层及以上的插件。
"""

from dorobot import (
    ctx,
    Plugin,
    Message,
    register_plugin,
    plugin_manager,
    bot_manager,
    global_config,
)


@register_plugin("meta", layer=0, description="Meta插件：管理其他插件的激活/关闭")
class MetaPlugin(Plugin):
    """Meta 插件

    处理 /meta 插件名 格式的命令，用于激活或关闭 1 层及以上的插件。
    如果输入匹配到已注册的插件名，则切换其状态并终止消息传递。
    如果不匹配任何插件，则让消息继续传递到后续层级。
    """

    async def handle_message(self, message: Message) -> bool:
        """处理消息

        检查是否是 /插件名 格式的命令。
        - 是：切换对应插件状态，返回 False（终止传递）
        - 否：返回 True（继续传递）
        """
        session = self.get_session()
        if not session:
            return True

        content = message.content.strip()
        prefix = global_config.cmd_prefix

        # 检查是否以命令前缀开头
        if not content.startswith(prefix):
            return True

        # 提取命令
        cmd_base = content.split()[0].lower()

        # /help 命令：显示帮助信息
        if cmd_base == f"{prefix}help":
            # 检查是否是 /help 插件名
            help_parts = content.strip().split()
            if len(help_parts) >= 2:
                plugin_name = help_parts[1].lower()
                registered = plugin_manager.list_plugins()
                if plugin_name in registered:
                    meta = plugin_manager.get_plugin_metadata(plugin_name)
                    desc = meta.get("description", "") if meta else ""
                    await self.send_message(
                        f"📖 {plugin_name}：{desc if desc else '无描述'}"
                    )
                    return False
            await self._show_help()
            return False

        # 检查是否是 /meta 格式的命令
        stripped_lower = content.lower().strip()
        if not stripped_lower.startswith(f"{prefix}meta"):
            return True

        # 提取插件名
        parts = stripped_lower.split()
        if len(parts) < 2:
            # 无插件名，退化为 /plugins
            await self._show_plugins()
            return False
        plugin_name = parts[1]

        if not plugin_name:
            return True

        # 检查是否是已注册的插件
        registered_plugins = plugin_manager.list_plugins()
        if plugin_name not in registered_plugins:
            return True

        # 获取插件元数据
        meta = plugin_manager.get_plugin_metadata(plugin_name)
        layer_id = meta.get("layer", 0) if meta else 0
        bots = meta.get("bots") if meta else None

        # 检查插件是否允许当前 Bot 类型
        current_bot_id = ctx.get_bot_id()
        current_bot = bot_manager.get_bot(current_bot_id) if current_bot_id else None
        if bots is not None and current_bot is not None:
            if not any(isinstance(current_bot, bot_type) for bot_type in bots):
                await self.send_message(f"⚠️ 插件 {plugin_name} 不适用于当前 Bot 类型")
                return False

        # 0 层插件默认开启且无法关闭
        if layer_id == 0:
            await self.send_message(f"⚠️ 插件 {plugin_name} 是系统插件，无法关闭")
            return False

        # 获取该层
        layer = session.get_layer(layer_id)

        # 检查插件是否已激活
        is_active = layer.is_plugin_active(plugin_name) if layer else False

        # 切换插件状态
        if is_active:
            # 关闭插件
            try:
                await session.deactivate_plugin(plugin_name, layer_id)
                await self.send_message(f"🔴 插件 {plugin_name} 已关闭")
            except Exception as e:
                await self.send_message(f"❌ 关闭插件失败：{e}")
        else:
            # 激活插件
            try:
                await session.activate_plugin(plugin_name, layer_id)
                await self.send_message(f"🟢 插件 {plugin_name} 已激活")
            except Exception as e:
                await self.send_message(f"❌ 激活插件失败：{e}")

        # 终止消息传递
        return False

    async def _show_plugins(self):
        """展示层级插件列表"""
        session = self.get_session()
        if not session:
            return

        # 获取当前 Bot 实例
        current_bot_id = ctx.get_bot_id()
        current_bot = bot_manager.get_bot(current_bot_id) if current_bot_id else None

        # 获取所有已注册的插件
        all_plugins = plugin_manager.list_plugins()

        # 按层级分组
        layers = {}
        for name in all_plugins:
            meta = plugin_manager.get_plugin_metadata(name)
            layer = meta.get("layer", 0) if meta else 0
            desc = meta.get("description", "") if meta else ""
            bots = meta.get("bots") if meta else None
            scope = meta.get("scope") if meta else None

            # 检查插件是否匹配当前会话类型
            if scope is not None and scope != session.type:
                continue  # 跳过不适用于当前会话类型的插件

            # 检查插件是否允许当前 Bot 类型
            if bots is not None and current_bot is not None:
                if not any(isinstance(current_bot, bot_type) for bot_type in bots):
                    continue  # 跳过不适用于当前 Bot 的插件

            if layer not in layers:
                layers[layer] = []
            layers[layer].append((name, desc))

        # 构建输出
        lines = []
        lines.append("📋 插件层级列表")
        lines.append("=" * 40)

        for layer_id in sorted(layers.keys()):
            plugins = layers[layer_id]

            # 层类型说明
            if layer_id == 0:
                layer_type = "[系统层]"
            elif layer_id == 1:
                layer_type = "[共享层]"
            elif layer_id == 2:
                layer_type = "[应用层]"
            elif layer_id == 3:
                layer_type = "[共享层]"
            else:
                layer_type = "[其他]"

            lines.append(f"\n🔹 层 {layer_id} {layer_type}")

            for name, desc in plugins:
                # 检查是否激活
                layer_obj = session.get_layer(layer_id)
                is_active = layer_obj.is_plugin_active(name) if layer_obj else False
                status = "🟢" if is_active else "🔴"
                lines.append(f"  {status} {name} - {desc}")

        lines.append("\n" + "=" * 40)
        lines.append("🟢 激活  🔴 关闭")
        await self.send_message("\n".join(lines))

    async def _show_help(self):
        """显示帮助信息"""
        prefix = global_config.cmd_prefix
        lines = [
            "📖 DoroBot 帮助",
            "=" * 40,
            "",
            "【系统命令】",
            f"  {prefix}help     - 显示本帮助",
            "",
            "【插件管理】",
            f"  {prefix}meta 插件名   - 激活/关闭指定插件",
        ]

        lines.append("")
        lines.append("=" * 40)

        await self.send_message("\n".join(lines))
