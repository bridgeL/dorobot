"""AI 测试适配器 - 方便 AI 调试的聊天机器人适配器

使用方法:
1. 在 test.py 中注册此适配器: adapter_manager.register(AITestAdapter())
2. 适配器启动后会自动运行 FastAPI 服务器在 localhost:18765
3. 通过 HTTP 请求发送命令来测试插件

HTTP 接口:
  GET  /health                        - 健康检查
  GET  /sessions                      - 列出会话
  POST /activate                      - 激活插件
  POST /msg                           - 发送消息

示例:
  curl http://localhost:18765/msg -d "sender_id=user1&sender_name=用户1&content=创建房间"
  curl http://localhost:18765/activate -d "session_id=group.test123&plugin_name=criminal_dance&layer=2"
"""

import asyncio
import threading
from typing import Optional
from loguru import logger

from fastapi import FastAPI, Form
import uvicorn

from dorobot.bot import Bot
from dorobot.adapter import Adapter
from dorobot.bot_manager import bot_manager


class AITestAdapter(Adapter):
    """AI 测试适配器"""

    name = "aitest"

    def __init__(self, port: int = 18765):
        super().__init__()
        self.port = port
        self._bot: Optional[AITestBot] = None
        self._server_thread: Optional[threading.Thread] = None
        self._app: Optional[FastAPI] = None

    async def start(self):
        bot = AITestBot()
        self._bot = bot
        bot_manager.add_bot(bot)

        # 创建 FastAPI 应用
        app = FastAPI(title="AITest Server")
        self._app = app

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        @app.get("/sessions")
        async def sessions():
            from dorobot.session_manager import session_manager
            return {"sessions": session_manager.list_sessions()}

        @app.post("/activate")
        async def activate(
            session_id: str = Form("group.test123"),
            plugin_name: str = Form(...),
            layer: int = Form(2)
        ):
            from dorobot.session_manager import session_manager
            session_type = "group" if session_id.startswith("group.") else "private"
            group_id = session_id.split(".")[1] if "." in session_id else ""
            session = await session_manager.get_or_create_session(
                session_id, type=session_type, group_id=group_id, user_id=""
            )
            await session.activate_plugin(plugin_name, layer_id=layer)
            return {"status": "ok", "activated": plugin_name}

        @app.post("/msg")
        async def send_msg(
            session_id: str = Form("group.test123"),
            sender_id: str = Form("user1"),
            sender_name: str = Form("用户1"),
            content: str = Form(...)
        ):
            await self._bot.send_test(session_id, sender_id, sender_name, content)
            await asyncio.sleep(0.05)
            return {"status": "ok"}

        # 在线程中启动 uvicorn 服务器
        def run_server():
            uvicorn.run(app, host="localhost", port=self.port, log_level="warning")

        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()

        # 等待服务器启动
        await asyncio.sleep(1)

        logger.info(f"AITestAdapter started - HTTP server on localhost:{self.port}")
        print(f"AITestAdapter started - HTTP server on http://localhost:{self.port}")

    async def stop(self):
        pass  # daemon thread will stop when main process exits


class AITestBot(Bot):
    """AI 测试机器人"""

    def __init__(self):
        super().__init__(self_id="aitest")
        self._running = False

    async def send(self, session_id: str, content: str):
        """发送消息到会话"""
        logger.info(f"[Bot->{session_id}] {content}")

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
