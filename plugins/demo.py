"""示例插件集合"""

from loguru import logger

from dorobot.plugin import Plugin, Message
from dorobot.plugin_manager import register_plugin


@register_plugin("echo", layer=1, description="回声插件：重复用户的消息")
class EchoPlugin(Plugin):
    """1层插件示例 - 回声（命令层，共享）"""

    async def on_activate(self):
        self.activation_count = 0

    async def handle_message(self, message: Message) -> bool:
        self.activation_count += 1
        await self.send_message(f"[Echo] {message.content}")
        return False # 停止传递，测试使用  
    

@register_plugin("game", layer=2, description="游戏插件：简单的猜数字游戏")
class GamePlugin(Plugin):
    """2层插件示例 - 游戏（应用层，独占）"""

    async def on_activate(self):
        self.target_number = 42
        self.guesses = []
        await self.send_message("游戏开始！请输入一个 0-99 的数字来猜数。")

    async def handle_message(self, message: Message) -> bool:
        # 处理猜数字
        try:
            guess = int(message.content)
            self.guesses.append(guess)

            if guess < self.target_number:
                await self.send_message(f"[Game] {guess} 太小了！")
            elif guess > self.target_number:
                await self.send_message(f"[Game] {guess} 太大了！")
            else:
                await self.send_message(
                    f"[Game] 恭喜你猜对了！答案是 {self.target_number}"
                )
                logger.info(
                    f"Number guessed! Answer was {self.target_number}, {len(self.guesses)} attempts"
                )
                self.target_number = (self.target_number + 13) % 100  # 换一个新数字

            return False  # 游戏处理完，中断传递

        except ValueError:
            # 不是数字，继续传递
            return True


@register_plugin("hello", layer=1, description="问候插件")
class HelloPlugin(Plugin):
    """1层插件示例 - 问候（命令层，共享）"""

    async def handle_message(self, message: Message) -> bool:
        if "你好" in message.content or "hello" in message.content.lower():
            await self.send_message(f"👋 你好，{message.sender_name}！")
        return True
