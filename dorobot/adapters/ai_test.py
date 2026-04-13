"""AI 测试适配器 - HTTP 服务端

提供 HTTP 接口供测试调用:
  - POST /send  发送测试消息
  - GET /logs  获取日志

使用方法:
1. 注册适配器: dorobot.add_adapter(AITestAdapter())
2. 启动服务后访问 http://localhost:8765/send 和 /logs
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from aiohttp import web
from loguru import logger

from dorobot.bot import Bot
from dorobot.adapter import Adapter
from dorobot.message import Message


class AITestAdapter(Adapter):
    """AI 测试适配器 - HTTP 服务端"""

    name = "ai_test"

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        super().__init__()
        self._bot: Optional[AITestBot] = None
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._host = host
        self._port = port
        self._start_line: int = 0

        # 日志文件
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

        self._app = web.Application()
        self._app.router.add_post("/send", self._handle_send)
        self._app.router.add_get("/logs", self._handle_logs)
        self._app.router.add_get("/health", self._handle_health)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()

        logger.info(f"AITestAdapter started on http://{self._host}:{self._port}")
        logger.info(f"  POST /send  - 发送测试消息")
        logger.info(f"  GET  /logs  - 获取日志")

    async def stop(self):
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        if self._bot:
            await self._bot.stop()
        logger.info("AITestAdapter stopped")

    def _get_log_start_line(self) -> int:
        """获取当前日志文件的行数"""
        logs_dir = Path.cwd() / "logs"
        ai_test_log = logs_dir / "ai_test.log"
        if not ai_test_log.exists():
            return 0
        return len(ai_test_log.read_text(encoding="utf-8").splitlines())

    def _get_logs_since(self, start_line: int) -> list[str]:
        """获取从指定行偏移之后的所有日志"""
        logs_dir = Path.cwd() / "logs"
        ai_test_log = logs_dir / "ai_test.log"
        if not ai_test_log.exists():
            return []
        lines = ai_test_log.read_text(encoding="utf-8").splitlines()
        return lines[start_line:] if start_line < len(lines) else []

    async def _handle_send(self, request: web.Request) -> web.Response:
        """处理 /send 请求"""
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        session_type = data.get("session_type", "private")
        target_id = data.get("target_id", "")
        sender_id = data.get("sender_id", "")
        sender_name = data.get("sender_name", "Unknown")
        content = data.get("content", "")

        if not target_id or not content:
            return web.json_response({"error": "Missing target_id or content"}, status=400)

        session_id = f"{session_type}.{target_id}"

        # 记录发送前的日志行数
        self._start_line = self._get_log_start_line()

        logger.debug(
            f"[AITest Msg] session={session_id}, sender={sender_name}({sender_id}), content={content}"
        )

        await self._bot.send_test(session_id, sender_id, sender_name, content)
        await asyncio.sleep(0.5)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        logs = self._get_logs_since(self._start_line)

        return web.json_response({
            "logs": logs,
            "time": timestamp,
            "session_id": session_id,
        })

    async def _handle_logs(self, request: web.Request) -> web.Response:
        """处理 /logs 请求"""
        count = min(int(request.query.get("count", 50)), 200)

        logs_dir = Path.cwd() / "logs"
        ai_test_log = logs_dir / "ai_test.log"
        if not ai_test_log.exists():
            return web.json_response({"logs": [], "count": 0})

        lines = ai_test_log.read_text(encoding="utf-8").splitlines()
        recent = lines[-count:] if len(lines) > count else lines

        return web.json_response({
            "logs": recent,
            "count": len(recent),
        })

    async def _handle_health(self, _request: web.Request) -> web.Response:
        """健康检查"""
        return web.json_response({"status": "ok"})


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
