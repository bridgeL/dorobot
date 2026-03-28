"""Console Bot 实现

命令行交互的 Bot 实现，用于本地测试和开发。
- 输入格式: "session_id user_id content"
- 将系统输出打印到命令行
"""
import asyncio
from typing import Callable
from loguru import logger

from dorobot.bot import Bot


class ConsoleBot(Bot):
    """控制台 Bot

    通过命令行与用户交互：
    - 输入格式: "session_id user_id content"
    - 系统回复打印到控制台

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

    def __init__(self):
        """初始化 Console Bot"""
        super().__init__(self_id="console")
        self._running = False
        self._input_task = None

    async def send(self, session_id: str, content: str):
        """发送消息到控制台

        Args:
            session_id: 消息来源的会话ID
            content: 消息内容
        """
        print(f"\n[Bot@{session_id}] {content}\n", flush=True)
        logger.info(f"Bot -> {session_id}: {content}")

    def _on_handler_error(self, event_name: str, handler: Callable, error: Exception):
        """处理回调错误"""
        logger.error(f"Handler error for event '{event_name}': {error}")
        print(f"\n[Error] 处理消息时出错: {error}\n")

    def _build_message(self, content: str, session_id: str, sender_name: str) -> dict:
        """构建消息对象

        Args:
            content: 消息内容
            session_id: 会话ID
            sender_name: 发送者名称

        Returns:
            标准消息格式字典
        """
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

    def _parse_input(self, line: str) -> tuple[str, str, str] | None:
        """解析输入行

        格式: "session_id user_id content"

        Returns:
            (session_id, user_id, content) 或 None（解析失败）
        """
        parts = line.split(maxsplit=2)
        if len(parts) < 3:
            return None
        return parts[0], parts[1], parts[2]

    async def _input_loop(self):
        """输入循环"""
        loop = asyncio.get_event_loop()

        while self._running:
            try:
                # 显示简洁提示符
                content = await loop.run_in_executor(None, lambda: input("> "))

                content = content.strip()
                if not content:
                    continue

                # 解析输入
                parsed = self._parse_input(content)
                if parsed is None:
                    print("\n[Error] 格式错误。正确格式: session_id user_id content")
                    print("示例: group1 Alice 你好\n")
                    continue

                session_id, user_id, message_content = parsed

                # 构建消息并触发回调
                message = self._build_message(message_content, session_id, user_id)
                logger.debug(f"Console input [{session_id}/{user_id}]: {message_content}")

                # 触发 msg 事件，传递 (session_id, message)
                await self.emit("msg", session_id, message)

            except asyncio.CancelledError:
                break
            except EOFError:
                print("\n[Bot] 输入结束")
                self._running = False
                break
            except Exception as e:
                logger.error(f"Input error: {e}")
                print(f"\n[Error] 读取输入失败: {e}\n")

    async def start(self):
        """启动 Console Bot"""
        self._running = True
        print(f"\n{'=' * 50}")
        print("Console Bot 已启动")
        print("输入格式: session_id user_id content")
        print("示例: group1 Alice 你好")
        print(f"{'=' * 50}\n")

        self._input_task = asyncio.create_task(self._input_loop())

        try:
            await self._input_task
        except asyncio.CancelledError:
            pass

    async def stop(self):
        """停止 Console Bot"""
        self._running = False
        if self._input_task:
            self._input_task.cancel()
            try:
                await self._input_task
            except asyncio.CancelledError:
                pass
        print("\n[Bot] 已停止")
        logger.info("ConsoleBot stopped")

    async def run(self):
        """运行 Bot（阻塞直到停止）"""
        try:
            await self.start()
        except KeyboardInterrupt:
            print("\n")
            logger.info("Received KeyboardInterrupt")
        finally:
            await self.stop()
