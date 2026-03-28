import asyncio
from loguru import logger

from dorobot.bot import Bot
from dorobot.adapter import Adapter


class ConsoleAdapter(Adapter):
    name = "console"

    def __init__(self):
        self._bot = None

    async def start(self):
        bot = ConsoleBot()
        self._bot = bot
        from dorobot.bot_manager import bot_manager
        bot_manager.add_bot(bot)
        asyncio.create_task(bot.start())

    async def stop(self):
        if self._bot:
            await self._bot.stop()


class ConsoleBot(Bot):
    def __init__(self):
        super().__init__(self_id="console")
        self._running = False
        self._input_task = None

    async def send(self, session_id: str, content: str):
        logger.info(f"[Bot] {self.self_id} -> {session_id}: {content}")

    def _build_message(self, content: str, session_id: str, sender_name: str) -> dict:
        return {
            "content": content,
            "sender_id": f"{session_id}_{sender_name}",
            "sender_name": sender_name,
            "session_id": session_id,
            "msg_type": "text",
            "raw_data": {
                "source": "console",
                "input": content
            }
        }

    def _parse_input(self, line: str):
        parts = line.split(maxsplit=2)
        if len(parts) < 3:
            return None
        return parts[0], parts[1], parts[2]

    async def _input_loop(self):
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                content = await loop.run_in_executor(None, lambda: input("> "))
                content = content.strip()
                if not content:
                    continue

                parsed = self._parse_input(content)
                if parsed is None:
                    logger.warning("格式错误。正确格式: session_id user_id content")
                    continue

                session_id, user_id, message_content = parsed
                message = self._build_message(message_content, session_id, user_id)
                await self.on_message(session_id, message)

            except asyncio.CancelledError:
                break
            except EOFError:
                logger.info("Console input ended")
                self._running = False
                break
            except Exception as e:
                logger.error(f"Input error: {e}")

    async def start(self):
        self._running = True
        logger.info("Console Bot started. Input format: session_id user_id content")
        self._input_task = asyncio.create_task(self._input_loop())
        try:
            await self._input_task
        except asyncio.CancelledError:
            pass

    async def stop(self):
        self._running = False
        if self._input_task:
            self._input_task.cancel()
            try:
                await self._input_task
            except asyncio.CancelledError:
                pass
        logger.info("ConsoleBot stopped")

    async def run(self):
        try:
            await self.start()
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt")
        finally:
            await self.stop()