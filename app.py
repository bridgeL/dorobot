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
    router,
    bot_manager,
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

    # 注册 ConsoleBot 到 BotManager（会自动创建实例）
    bot_manager.register("console", ConsoleBot, auto_start=False)

    # 注册 Bot 到 Router（设置消息回调）
    router.register_bot("console")

    # 获取 bot 实例并运行
    console_bot = bot_manager.get_bot("console")
    if not console_bot:
        logger.error("Failed to create console bot")
        return

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
