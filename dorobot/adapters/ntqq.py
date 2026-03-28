import asyncio
import json
import uuid
from typing import Dict
from loguru import logger

import websockets
from websockets import ServerConnection

from dorobot.bot import Bot
from dorobot.adapter import Adapter


class NTQQAdapter(Adapter):
    name = "ntqq"

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self._server = None
        self._running = False
        self._client_counter = 0

    def get_bot(self):
        return None

    def _register_bot(self, bot: Bot):
        from dorobot.bot_manager import bot_manager
        bot_manager.add_bot(bot)

    def _unregister_bot(self, bot_id: str):
        from dorobot.bot_manager import bot_manager
        bot_manager.remove_bot(bot_id)

    async def _handle_client(self, websocket: ServerConnection):
        self._client_counter += 1
        client_id = f"ntqq_{self._client_counter}"

        bot = NTQQBot(self_id=client_id)
        bot._websocket = websocket
        self._register_bot(bot)

        logger.info(f"[NTQQ] Client connected: {client_id} ({websocket.remote_address})")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await bot.handle_message(data)
                except json.JSONDecodeError:
                    logger.error(f"[NTQQ] Invalid JSON received: {message[:200]}")
                except Exception as e:
                    logger.error(f"[NTQQ] Error handling message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"[NTQQ] Connection closed: {client_id}")
        finally:
            self._unregister_bot(client_id)
            await bot.stop()
            logger.info(f"[NTQQ] Client disconnected: {client_id}")

    async def start(self):
        self._running = True
        self._server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
        )
        logger.info(f"[NTQQ] Server started, listening on: ws://{self.host}:{self.port}")
        logger.info("[NTQQ] Waiting for connections...")

    async def stop(self):
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        logger.info("[NTQQ] Server stopped")


class NTQQBot(Bot):
    def __init__(self, self_id: str = ""):
        super().__init__(self_id=self_id)
        self._websocket: ServerConnection | None = None
        self._pending_requests: Dict[str, asyncio.Future] = {}

    async def send_ws(self, action: str, params: dict | None = None, timeout: float = 5.0) -> dict | None:
        if not self._websocket:
            logger.error(f"[Bot]{self.self_id} 未连接，无法发送消息")
            return None

        request_id = str(uuid.uuid4())
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        message = {
            "action": action,
            "params": params or {},
            "echo": request_id,
        }

        try:
            await self._websocket.send(json.dumps(message))
            logger.debug(f"[Bot]{self.self_id} sent {action}: {request_id}")
            result = await asyncio.wait_for(future, timeout=timeout)
            logger.debug(f"[Bot]{self.self_id} received response for {request_id}: {result}")
            return result
        except asyncio.TimeoutError:
            logger.warning(f"[Bot]{self.self_id} request {request_id} timeout")
        except Exception as e:
            logger.error(f"[Bot]{self.self_id} failed to send message: {e}")
        finally:
            self._pending_requests.pop(request_id, None)
        return None

    async def send(self, session_id: str, content: str):
        result = await self.send_ws("send_msg", {"session_id": session_id, "content": content})
        logger.info(f"[Bot]{self.self_id} -> {session_id}: {content}")

    async def handle_message(self, data: dict):
        echo = data.get("echo")
        if echo and echo in self._pending_requests:
            future = self._pending_requests.get(echo)
            if future and not future.done():
                future.set_result(data)
            return

        post_type = data.get("post_type")
        if post_type == "message":
            await self._handle_message_notification(data)

    async def _handle_message_notification(self, data: dict):
        message_type = data.get("message_type", "unknown")
        user_id = str(data.get("user_id", ""))
        group_id = data.get("group_id")

        if message_type == "group" and group_id:
            session_id = f"group_{group_id}"
        else:
            session_id = f"private_{user_id}"

        message_content = self._extract_message_content(data.get("message", []))

        message = {
            "content": message_content,
            "sender_id": user_id,
            "sender_name": data.get("sender", {}).get("nickname", user_id),
            "session_id": session_id,
            "msg_type": message_type,
            "raw_data": data,
        }

        logger.debug(f"NTQQ message [{session_id}/{user_id}]: {message_content[:50]}")
        await self.on_message(session_id, message)

    def _extract_message_content(self, message: list | str) -> str:
        if isinstance(message, str):
            return message
        if isinstance(message, list):
            texts = []
            for segment in message:
                if isinstance(segment, dict):
                    if segment.get("type") == "text":
                        texts.append(segment.get("data", {}).get("text", ""))
                    elif segment.get("type") == "at":
                        qq = segment.get("data", {}).get("qq", "")
                        texts.append(f"@{qq}")
                    elif segment.get("type") == "image":
                        texts.append("[图片]")
            return "".join(texts)
        return str(message)

    async def start(self):
        pass

    async def stop(self):
        if self._pending_requests:
            for future in self._pending_requests.values():
                if not future.done():
                    future.cancel()
            self._pending_requests.clear()