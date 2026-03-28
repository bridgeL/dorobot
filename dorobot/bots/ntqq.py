"""NTQQ Bot 实现

通过 WebSocket 与 ntqq 通信的 Bot 实现。
- 启动反向 WebSocket 服务端，等待 ntqq 主动连接
- 支持请求-响应模式（send 方法等待返回）
- 支持消息通知模式（emit 事件）
"""
import asyncio
import json
import uuid
from typing import Callable, Dict, Any
from loguru import logger

import websockets
from websockets.legacy.server import WebSocketServerProtocol

from dorobot.bot import Bot


class NTQQBot(Bot):
    """NTQQ Bot

    通过反向 WebSocket 与 ntqq 通信：
    - 启动 ws 服务端，等待 ntqq 连接
    - send 方法发送请求并等待响应
    - 收到消息时区分响应和通知

    消息格式:
    {
        "content": str,      # 消息内容
        "sender_id": str,    # 发送者ID
        "sender_name": str,  # 发送者名称
        "session_id": str,   # 会话ID
        "msg_type": str,     # 消息类型
        "raw_data": dict     # 原始数据
    }
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        """初始化 NTQQ Bot

        Args:
            host: WebSocket 服务端监听地址
            port: WebSocket 服务端监听端口
        """
        super().__init__(self_id="ntqq")
        self.host = host
        self.port = port
        self._websocket: WebSocketServerProtocol | None = None
        self._server = None
        self._running = False
        # 等待响应的请求: request_id -> asyncio.Future
        self._pending_requests: Dict[str, asyncio.Future] = {}

    async def send(self, session_id: str, content: str):
        """发送消息到 ntqq

        发送请求并等待响应结果。

        Args:
            session_id: 目标会话ID（群号或QQ号）
            content: 消息内容
        """
        if not self._websocket:
            logger.error("NTQQ 未连接，无法发送消息")
            return

        # 生成请求ID
        request_id = str(uuid.uuid4())

        # 创建 Future 等待响应
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        # 构造发送消息
        message = {
            "action": "send_msg",
            "params": {
                "session_id": session_id,
                "content": content,
            },
            "echo": request_id,  # 用于匹配响应
        }

        try:
            await self._websocket.send(json.dumps(message))
            logger.debug(f"Sent message to ntqq: {request_id}")

            # 等待响应（带超时）
            result = await asyncio.wait_for(future, timeout=30.0)
            logger.debug(f"Received response for {request_id}: {result}")
        except asyncio.TimeoutError:
            logger.error(f"Request {request_id} timeout")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
        finally:
            self._pending_requests.pop(request_id, None)

    def _on_handler_error(self, event_name: str, handler: Callable, error: Exception):
        """处理回调错误"""
        logger.error(f"Handler error for event '{event_name}': {error}")

    async def handle_ntqq_connection(self, websocket: WebSocketServerProtocol, path: str):
        """处理 ntqq WebSocket 连接

        Args:
            websocket: WebSocket 连接对象
            path: 连接路径
        """
        if self._websocket is not None:
            logger.warning("已有 ntqq 连接，拒绝新连接")
            await websocket.close(1008, "Already connected")
            return

        self._websocket = websocket
        logger.success(f"NTQQ 已连接: {websocket.remote_address}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message[:200]}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("NTQQ 连接已关闭")
        finally:
            self._websocket = None
            logger.warning("NTQQ 已断开连接")

    async def _handle_message(self, data: Dict[str, Any]):
        """处理收到的消息

        区分响应和通知：
        - 有 echo 字段且匹配 pending_requests -> 是响应
        - 否则是消息通知
        """
        echo = data.get("echo")

        # 检查是否是响应
        if echo and echo in self._pending_requests:
            future = self._pending_requests.get(echo)
            if future and not future.done():
                future.set_result(data)
            return

        # 检查是否是消息通知
        post_type = data.get("post_type")
        if post_type == "message":
            await self._handle_message_notification(data)

    async def _handle_message_notification(self, data: Dict[str, Any]):
        """处理消息通知

        将 ntqq 消息格式转换为标准格式，并触发 msg 事件。
        """
        # 解析 ntqq 消息格式
        message_type = data.get("message_type", "unknown")
        user_id = str(data.get("user_id", ""))
        group_id = data.get("group_id")

        # 构造 session_id
        if message_type == "group" and group_id:
            session_id = f"group_{group_id}"
        else:
            session_id = f"private_{user_id}"

        # 提取消息内容
        message_content = self._extract_message_content(data.get("message", []))

        # 构造标准消息格式
        message = {
            "content": message_content,
            "sender_id": user_id,
            "sender_name": data.get("sender", {}).get("nickname", user_id),
            "session_id": session_id,
            "msg_type": message_type,
            "raw_data": data,
        }

        logger.debug(f"NTQQ message [{session_id}/{user_id}]: {message_content[:50]}")

        # 触发 msg 事件
        await self.emit("msg", session_id, message)

    def _extract_message_content(self, message: list | str) -> str:
        """提取消息内容

        ntqq 消息可能是数组格式或字符串格式。
        """
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
        """启动 NTQQ Bot

        启动反向 WebSocket 服务端，等待 ntqq 连接。
        """
        self._running = True

        self._server = await websockets.serve(
            self.handle_ntqq_connection,
            self.host,
            self.port,
        )

        logger.success(f"NTQQ Bot 反向 WebSocket 服务端已启动")
        logger.info(f"监听地址: ws://{self.host}:{self.port}")
        logger.info("等待 ntqq 主动连接...\n")

        await self._server.wait_closed()

    async def stop(self):
        """停止 NTQQ Bot"""
        self._running = False

        # 关闭 WebSocket 连接
        if self._websocket:
            await self._websocket.close()
            self._websocket = None

        # 关闭服务端
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        # 清理 pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

        logger.info("NTQQ Bot 已停止")

    async def run(self):
        """运行 Bot（阻塞直到停止）"""
        try:
            await self.start()
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt")
        finally:
            await self.stop()
