"""
测试服务器启动脚本

这个脚本启动 AITestAdapter，它包含内置的 HTTP 测试服务器。
通过 HTTP 请求发送命令来测试插件。

HTTP 接口:
  GET  /health                        - 健康检查
  GET  /sessions                      - 列出会话
  POST /activate                      - 激活插件
  POST /msg                          - 发送消息

示例:
  curl http://localhost:18765/health
  curl -X POST http://localhost:18765/activate -d "session_id=group.test123&plugin_name=criminal_dance&layer=2"
  curl -X POST http://localhost:18765/msg -d "sender_id=user1&sender_name=用户1&content=创建房间"
"""

import asyncio

from dorobot import init_logging, load_plugins, init_space
from dorobot.adapters.ai_test import AITestAdapter
from dorobot.adapter_manager import adapter_manager


async def main():
    # 初始化
    init_logging(level="INFO")
    init_space()
    load_plugins()

    # 注册适配器
    adapter_manager.register(AITestAdapter())

    # 启动所有适配器
    await adapter_manager.start_all()
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("\nStopping...")


if __name__ == "__main__":
    asyncio.run(main())
