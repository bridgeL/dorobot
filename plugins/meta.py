"""Meta 插件 - 用于管理其他插件的激活/关闭

位于 0 层，负责处理 /meta 插件名 格式的命令，用于激活或关闭 1 层及以上的插件。
"""

from dorobot import (
    Plugin,
    Message,
    global_config,
)
from dorobot.plugin_manager import plugin_manager


app = Plugin(name="meta", layer=0, description="Meta插件：管理其他插件的激活/关闭")


@app.on_message()
async def handle_message(msg: Message) -> bool:
    """处理消息"""
    session = app.get_session()
    if not session:
        return True

    content = msg.content.strip()
    prefix = global_config.cmd_prefix

    if not content.startswith(prefix):
        return True

    cmd_base = content.split()[0].lower()

    # /help 命令
    if cmd_base == f"{prefix}help":
        help_parts = content.strip().split()
        if len(help_parts) >= 2:
            plugin_name = help_parts[1].lower()
            registered = plugin_manager.list_plugins()  # type: ignore
            if plugin_name in registered:
                meta = plugin_manager.get_plugin_metadata(plugin_name)  # type: ignore
                desc = meta.get("description", "") if meta else ""
                await app.send_message(f"📖 {plugin_name}：{desc if desc else '无描述'}")
                return False
        await _show_help()
        return False

    # /meta 格式命令
    stripped_lower = content.lower().strip()
    if not stripped_lower.startswith(f"{prefix}meta"):
        return True

    parts = stripped_lower.split()
    if len(parts) < 2:
        await _show_plugins()
        return False
    plugin_name = parts[1]

    if not plugin_name:
        return True

    registered_plugins = plugin_manager.list_plugins()  # type: ignore
    if plugin_name not in registered_plugins:
        return True

    meta = plugin_manager.get_plugin_metadata(plugin_name)  # type: ignore
    layer_id = meta.get("layer", 0) if meta else 0
    bots = meta.get("bots") if meta else None

    current_bot = app.get_bot()
    if bots is not None and current_bot is not None:
        if not any(isinstance(current_bot, bot_type) for bot_type in bots):
            await app.send_message(f"⚠️ 插件 {plugin_name} 不适用于当前 Bot 类型")
            return False

    if layer_id == 0:
        await app.send_message(f"⚠️ 插件 {plugin_name} 是系统插件，无法关闭")
        return False

    layer = session.get_layer(layer_id)
    is_active = layer.is_plugin_active(plugin_name) if layer else False

    if is_active:
        try:
            await session.deactivate_plugin(plugin_name, layer_id)
            await app.send_message(f"🔴 插件 {plugin_name} 已关闭")
        except Exception as e:
            await app.send_message(f"❌ 关闭插件失败：{e}")
    else:
        try:
            await session.activate_plugin(plugin_name, layer_id)
            await app.send_message(f"🟢 插件 {plugin_name} 已激活")
        except Exception as e:
            await app.send_message(f"❌ 激活插件失败：{e}")

    return False


async def _show_plugins():
    """展示层级插件列表"""
    session = app.get_session()
    if not session:
        return

    current_bot = app.get_bot()

    all_plugins = plugin_manager.list_plugins()  # type: ignore

    layers = {}
    for name in all_plugins:
        meta = plugin_manager.get_plugin_metadata(name)  # type: ignore
        layer = meta.get("layer", 0) if meta else 0
        desc = meta.get("description", "") if meta else ""
        bots = meta.get("bots") if meta else None
        scope = meta.get("scope") if meta else None

        if scope is not None and scope != session.type:
            continue

        if bots is not None and current_bot is not None:
            if not any(isinstance(current_bot, bot_type) for bot_type in bots):
                continue

        if layer not in layers:
            layers[layer] = []
        layers[layer].append((name, desc))

    lines = []
    lines.append("📋 插件层级列表")
    lines.append("=" * 40)

    for layer_id in sorted(layers.keys()):
        plugins = layers[layer_id]

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
            layer_obj = session.get_layer(layer_id)
            is_active = layer_obj.is_plugin_active(name) if layer_obj else False
            status = "🟢" if is_active else "🔴"
            lines.append(f"  {status} {name} - {desc}")

    lines.append("\n" + "=" * 40)
    lines.append("🟢 激活  🔴 关闭")
    await app.send_message("\n".join(lines))


async def _show_help():
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
    await app.send_message("\n".join(lines))


app.register()
