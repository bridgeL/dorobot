"""AI 测试适配器 - 方便 AI 调试的聊天机器人适配器

提供异步方法供 MCP server 调用，不再启动 HTTP 服务器。

使用方法:
1. 注册适配器: dorobot.add_adapter(AITestAdapter())
2. 调用异步方法发送测试消息和获取日志

异步方法:
  - send_test(session_id, sender_id, sender_name, content): 发送测试消息
  - get_logs(count): 获取最近 N 条日志
  - get_logs_since(start_line): 获取从指定偏移之后的所有日志
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from dorobot.bot import Bot
from dorobot.adapter import Adapter
from dorobot.message import Message


class AITestAdapter(Adapter):
    """AI 测试适配器"""

    name = "ai_test"

    def __init__(self):
        super().__init__()
        self._bot: Optional[AITestBot] = None
        self._start_line: int = 0

        # 添加 ai_test 专用日志文件，DEBUG 级别
        logs_dir = Path.cwd() / "logs"
        logs_dir.mkdir(exist_ok=True)
        logger.add(
            logs_dir / "ai_test.log",
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>",
            level="DEBUG",
            mode="w",
        )

    async def start(self):
        bot = AITestBot()
        self._bot = bot
        self._dorobot.bot_manager.add_bot(bot)
        logger.info("AITestAdapter started")

    async def stop(self):
        if self._bot:
            await self._bot.stop()

    def _get_log_start_line(self) -> int:
        """获取当前日志文件的行数"""
        logs_dir = Path.cwd() / "logs"
        ai_test_log = logs_dir / "ai_test.log"
        if not ai_test_log.exists():
            return 0
        return len(ai_test_log.read_text(encoding="utf-8").splitlines())

    async def send_test(
        self, session_id: str, sender_id: str, sender_name: str, content: str
    ) -> dict:
        """发送测试消息并返回增量日志

        Args:
            session_id: 会话ID（如 "group.test123" 或 "private.user1"）
            sender_id: 发送者ID
            sender_name: 发送者昵称
            content: 消息内容

        Returns:
            包含 logs 和 time 的字典
        """
        # 记录发送前的日志行数
        self._start_line = self._get_log_start_line()

        logger.debug(
            f"[AITest Msg] session={session_id}, sender={sender_name}({sender_id}), content={content}"
        )

        await self._bot.send_test(session_id, sender_id, sender_name, content)
        await asyncio.sleep(0.5)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        logs = self._get_logs_since(self._start_line)

        return {"logs": logs, "time": timestamp}

    async def send_group_msg(
        self, group_id: str, sender_id: str, sender_name: str, content: str
    ) -> dict:
        """发送群聊测试消息

        Args:
            group_id: 群ID（如 "test123"）
            sender_id: 发送者ID
            sender_name: 发送者昵称
            content: 消息内容

        Returns:
            包含 logs 和 time 的字典
        """
        session_id = f"group.{group_id}"
        return await self.send_test(session_id, sender_id, sender_name, content)

    async def send_private_msg(
        self, user_id: str, sender_id: str, sender_name: str, content: str
    ) -> dict:
        """发送私聊测试消息

        Args:
            user_id: 用户ID（如 "user1"）
            sender_id: 发送者ID
            sender_name: 发送者昵称
            content: 消息内容

        Returns:
            包含 logs 和 time 的字典
        """
        session_id = f"private.{user_id}"
        return await self.send_test(session_id, sender_id, sender_name, content)

    def _get_recent_logs(self, count: int = 10) -> list[str]:
        """获取最近指定数量的日志"""
        logs_dir = Path.cwd() / "logs"
        ai_test_log = logs_dir / "ai_test.log"
        if not ai_test_log.exists():
            return []
        lines = ai_test_log.read_text(encoding="utf-8").splitlines()
        return lines[-count:] if len(lines) > count else lines

    def _get_logs_since(self, start_line: int) -> list[str]:
        """获取从指定行偏移之后的所有日志"""
        logs_dir = Path.cwd() / "logs"
        ai_test_log = logs_dir / "ai_test.log"
        if not ai_test_log.exists():
            return []
        lines = ai_test_log.read_text(encoding="utf-8").splitlines()
        return lines[start_line:] if start_line < len(lines) else []

    async def get_logs(self, count: int = 10) -> dict:
        """获取最近指定数量的日志

        Args:
            count: 要获取的日志数量，默认10条，最多100条

        Returns:
            包含 logs 和 count 的字典
        """
        count = min(count, 100)
        recent_lines = self._get_recent_logs(count)
        return {"logs": recent_lines, "count": len(recent_lines)}


class AITestBot(Bot):
    """AI 测试机器人"""

    def __init__(self):
        super().__init__(self_id="ai_test")
        self._running = False

    async def send(self, session_id: str, content: str):
        """发送消息到会话"""
        logger.info(f"[Bot->{session_id}] {content}")

    async def send_group(self, group_id: str, content: str):
        """发送群消息"""
        logger.info(f"[Bot->group.{group_id}] {content}")

    async def send_private(self, user_id: str, content: str):
        """发送私聊消息"""
        logger.info(f"[Bot->private.{user_id}] {content}")

    def _build_message(
        self, content: str, session_id: str, sender_id: str, sender_name: str
    ):
        """构建消息对象"""
        if session_id.startswith("group."):
            session_type = "group"
            group_id = session_id[6:]
        else:
            session_type = "private"
            group_id = ""

        return Message(
            content=content,
            sender_id=sender_id,
            sender_name=sender_name,
            session_id=session_id,
            session_type=session_type,
            group_id=group_id,
            user_id=sender_id,
            raw_data={"source": self.self_id, "input": content},
        )

    async def send_test(
        self, session_id: str, sender_id: str, sender_name: str, content: str
    ):
        """发送测试消息"""
        message = self._build_message(content, session_id, sender_id, sender_name)
        await self.on_message(message)

    async def start(self):
        self._running = True
        logger.info("AITestBot started")

    async def stop(self):
        self._running = False
        logger.info("AITestBot stopped")
