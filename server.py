import asyncio
import subprocess
from pathlib import Path
from mcp.server.fastmcp import FastMCP

import aiohttp

mcp = FastMCP("dorobot")

_process: subprocess.Popen | None = None
_BASE_URL = "http://localhost:8765"

# 获取项目根目录
_PROJECT_ROOT = Path(__file__).parent.resolve()


@mcp.tool()
async def start_dorobot() -> str:
    """启动 dorobot (子进程 python test_ai.py)"""
    global _process

    if _process is not None:
        # 检查进程是否已死
        if _process.poll() is not None:
            _process = None  # 进程已结束，清除引用
        else:
            return "dorobot 已在运行"

    _process = subprocess.Popen(
        ["python", "test_ai.py"],
        cwd=str(_PROJECT_ROOT),
        creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0,
    )

    # 等待服务启动
    await asyncio.sleep(0.5)

    return "dorobot 已启动"


@mcp.tool()
async def stop_dorobot() -> str:
    """关闭 dorobot (终止子进程)"""
    global _process

    if _process is None:
        return "dorobot 未运行"

    _process.terminate()
    try:
        _process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _process.kill()
    _process = None

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
    payload = {
        "session_type": session_type,
        "target_id": target_id,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "content": content,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{_BASE_URL}/send", json=payload) as resp:
            result = await resp.json()

    logs = result.get("logs", [])
    if not logs:
        return f"[{result.get('time', '')}] 无新增日志"

    return "\n".join(logs)


@mcp.tool()
async def get_logs(count: int = 50) -> str:
    """获取最近的日志

    Args:
        count: 日志条数上限 (默认50，最多200)
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{_BASE_URL}/logs", params={"count": count}) as resp:
            result = await resp.json()

    logs = result.get("logs", [])
    if not logs:
        return "无日志"

    return "\n".join(logs)


if __name__ == "__main__":
    mcp.run()
