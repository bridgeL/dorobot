"""AI 测试适配器 - 方便 AI 调试的聊天机器人适配器

使用方法:
1. 在 test.py 中注册此适配器: adapter_manager.register(AITestAdapter())
2. 适配器启动后会自动运行 FastAPI 服务器在 localhost:18765
3. 通过 HTTP 请求发送命令来测试插件

HTTP 接口:
  GET  /health                        - 健康检查
  GET  /log?count=N                  - 获取最近 N 条日志
  POST /msg                           - 发送消息（返回最近10条日志和当前时间）

示例:
  curl http://localhost:18765/msg -d "sender_id=user1&sender_name=用户1&content=创建房间"
  curl http://localhost:18765/log?count=20
"""

import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from fastapi import FastAPI, Form
import uvicorn

from dorobot.bot import Bot
from dorobot.adapter import Adapter
from dorobot.bot_manager import bot_manager


class AITestAdapter(Adapter):
    """AI 测试适配器"""

    name = "ai_test"

    def __init__(self, port: int = 18765):
        super().__init__()
        self.port = port
        self._bot: Optional[AITestBot] = None
        self._server_thread: Optional[threading.Thread] = None
        self._app: Optional[FastAPI] = None

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
            mode="w"
        )

    async def start(self):
        bot = AITestBot()
        self._bot = bot
        bot_manager.add_bot(bot)

        # 创建 FastAPI 应用
        app = FastAPI(title="AITest Server")
        self._app = app

        def get_recent_logs(count: int = 10) -> list[str]:
            """获取最近指定数量的日志"""
            logs_dir = Path.cwd() / "logs"
            ai_test_log = logs_dir / "ai_test.log"
            if not ai_test_log.exists():
                return []
            lines = ai_test_log.read_text(encoding="utf-8").splitlines()
            return lines[-count:] if len(lines) > count else lines

        def get_logs_since(start_line: int) -> list[str]:
            """获取从指定行偏移之后的所有日志"""
            logs_dir = Path.cwd() / "logs"
            ai_test_log = logs_dir / "ai_test.log"
            if not ai_test_log.exists():
                return []
            lines = ai_test_log.read_text(encoding="utf-8").splitlines()
            return lines[start_line:] if start_line < len(lines) else []

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        @app.get("/log")
        async def get_log(count: int = 10):
            """获取最近指定数量的 ai_test 日志

            Args:
                count: 要获取的日志数量，默认10条，最多100条

            Returns:
                日志列表
            """
            count = min(count, 100)
            recent_lines = get_recent_logs(count)
            return {"logs": recent_lines, "count": len(recent_lines)}

        @app.post("/msg")
        async def send_msg(
            session_id: str = Form("group.test123"),
            sender_id: str = Form("user1"),
            sender_name: str = Form("用户1"),
            content: str = Form(...)
        ):
            logger.debug(f"[AITest Msg] session={session_id}, sender={sender_name}({sender_id}), content={content}")
            # 记录当前日志行数，send_test 后获取增量日志
            logs_dir = Path.cwd() / "logs"
            ai_test_log = logs_dir / "ai_test.log"
            start_line = ai_test_log.read_text(encoding="utf-8").splitlines().__len__() if ai_test_log.exists() else 0
            await self._bot.send_test(session_id, sender_id, sender_name, content)
            await asyncio.sleep(0.2)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            return {"logs": get_logs_since(start_line), "time": timestamp}

        # 在线程中启动 uvicorn 服务器
        def run_server():
            uvicorn.run(app, host="localhost", port=self.port, log_level="warning")

        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()

        # 等待服务器启动
        await asyncio.sleep(1)

        logger.info(f"AITestAdapter started - HTTP server on localhost:{self.port}")

    async def stop(self):
        pass  # daemon thread will stop when main process exits


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

    def _build_message(self, content: str, session_id: str, sender_id: str, sender_name: str) -> dict:
        """构建消息字典"""
        if session_id.startswith("group."):
            session_type = "group"
            group_id = session_id[6:]
        else:
            session_type = "private"
            group_id = ""

        return {
            "content": content,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "session_id": session_id,
            "msg_type": "text",
            "type": session_type,
            "group_id": group_id,
            "user_id": sender_id,
            "raw_data": {"source": "aitest", "input": content}
        }

    async def send_test(self, session_id: str, sender_id: str, sender_name: str, content: str):
        """发送测试消息"""
        message = self._build_message(content, session_id, sender_id, sender_name)
        await self.on_message(session_id, message)

    async def start(self):
        self._running = True
        logger.info("AITestBot started")

    async def stop(self):
        self._running = False
        logger.info("AITestBot stopped")


# 全局访问
_aitest_bot: Optional[AITestBot] = None


def get_aitest_bot() -> AITestBot:
    """获取 AI 测试机器人实例（单例）"""
    global _aitest_bot
    if _aitest_bot is None:
        _aitest_bot = AITestBot()
        bot_manager.add_bot(_aitest_bot)
    return _aitest_bot
