"""Bot管理插件 - 提供查看bot和session信息的命令"""

from loguru import logger

from dorobot.plugin import Plugin, Message
from dorobot.plugin_manager import register_plugin
from dorobot.bot_manager import bot_manager
from dorobot.session_manager import session_manager
import dorobot.context as ctx


@register_plugin("bot_manager", layer=1, description="Bot管理插件：查看bot和session信息")
class BotManagerPlugin(Plugin):
    """1层插件 - Bot管理（命令层，共享）"""

    async def handle_message(self, message: Message) -> bool:
        bot_id = ctx.get_bot_id()

        if bot_id != "console":
            return True

        content = message.content.strip()

        if content == "/bots":
            await self._handle_bots_command()
            return False

        if content == "/sessions":
            await self._handle_sessions_command()
            return False

        return True

    async def _handle_bots_command(self):
        bots = bot_manager.get_all_bots()
        if not bots:
            await self.send_message("当前没有运行的Bot")
            return

        lines = ["当前运行的Bot:"]
        for bot_id, bot in bots.items():
            lines.append(f"  - {bot_id} (self_id: {bot.self_id})")

        await self.send_message("\n".join(lines))

    async def _handle_sessions_command(self):
        sessions = session_manager.list_sessions()
        if not sessions:
            await self.send_message("当前没有活跃的Session")
            return

        lines = ["当前活跃的Session:"]
        for session_key in sessions:
            lines.append(f"  - {session_key}")

        await self.send_message("\n".join(lines))
