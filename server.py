from mcp.server.fastmcp import FastMCP

from dorobot import Dorobot
from dorobot.adapters.ai_test import AITestAdapter

mcp = FastMCP("dorobot")

_dorobot: Dorobot | None = None
_ai_adapter: AITestAdapter | None = None


@mcp.tool()
def start_dorobot() -> str:
    """启动 dorobot"""
    global _dorobot, _ai_adapter

    _dorobot = Dorobot.get_instance()
    _dorobot.init()

    _ai_adapter = AITestAdapter()
    _dorobot.add_adapter(_ai_adapter)
    _dorobot.start()

    return "dorobot 已启动"


@mcp.tool()
async def stop_dorobot() -> str:
    """关闭 dorobot"""
    global _dorobot, _ai_adapter

    if _dorobot:
        await _dorobot.stop()
    _ai_adapter = None

    return "dorobot 已关闭"


@mcp.tool()
async def send_message(
    session_type: str,
    target_id: str,
    sender_id: str,
    sender_name: str,
    content: str,
) -> str:
    """发送群聊或私聊消息，并返回发送后0.5秒内新增的系统日志

    Args:
        session_type: 会话类型，"group" 或 "private"
        target_id: 目标ID（群号或用户ID）
        sender_id: 发送者ID
        sender_name: 发送者昵称
        content: 消息内容
    """
    if _ai_adapter is None:
        return "错误: dorobot 未启动，请先调用 start_dorobot()"

    session_id = f"{session_type}.{target_id}"
    result = await _ai_adapter.send_test(session_id, sender_id, sender_name, content)
    logs = result.get("logs", [])

    if not logs:
        return f"[{result['time']}] 无新增日志"

    return "\n".join(logs)


if __name__ == "__main__":
    mcp.run()
