"""
多插件聊天机器人 - 启动入口

功能：
1. 创建并配置 MessageRouter
2. 手动实例化 Bot 并注册给 Router
3. 加载插件并启动 Bot

流程：
- 当 Bot 收到消息时，Router 会自动通过 SessionManager 获取或创建 Session
- Session 只跟踪插件激活状态，不拥有插件实例
- 插件是全局独立的，通过 PluginManager 管理
"""
import asyncio
from loguru import logger

from dorobot import (
    get_router,
    init_logging,
    load_plugins,
)
from dorobot.bots.console_bot import ConsoleBot

# 初始化日志
init_logging(level="DEBUG")


async def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("DoroBot Starting...")
    logger.info("=" * 50)

    # 加载插件（注册到全局 PluginManager）
    load_plugins()

    # 创建消息路由器（内部使用 SessionManager）
    router = get_router()

    # 手动实例化 ConsoleBot
    console_bot = ConsoleBot()

    # 注册 Bot 到 Router（指定 bot_id）
    # 当 Bot 收到消息时，Router 会自动创建/获取 Session
    router.register_bot(console_bot, "console")

    # 启动 Bot
    # 不需要手动创建 "default" session，当用户输入消息时会自动创建
    try:
        await console_bot.run()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt")
    finally:
        await console_bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
