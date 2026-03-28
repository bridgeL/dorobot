"""示例插件集合"""
from loguru import logger

from dorobot.plugin import Plugin, Message
from dorobot.plugin_manager import register_plugin


@register_plugin("echo", layer=1, description="回声插件：重复用户的消息")
class EchoPlugin(Plugin):
    """1层插件示例 - 回声（命令层，共享）"""

    async def handle_message(self, message: Message) -> bool:
        await self.send_message(f"[Echo] {message.content}")
        return True  # 继续传递


@register_plugin("filter", layer=1, description="过滤插件：拦截敏感词")
class FilterPlugin(Plugin):
    """1层插件示例 - 消息过滤（命令层，共享）"""

    SENSITIVE_WORDS = ["脏话", "spam", "badword"]

    async def handle_message(self, message: Message) -> bool:
        for word in self.SENSITIVE_WORDS:
            if word in message.content:
                await self.send_message(f"[Filter] 消息包含敏感词 '{word}'，已被拦截")
                logger.warning(f"Message blocked by filter: contains '{word}'")
                return False  # 中断传递
        return True  # 继续传递


@register_plugin("gpt", layer=2, description="GPT插件：AI对话")
class GPTPlugin(Plugin):
    """2层插件示例 - AI对话（应用层，独占）"""

    async def handle_message(self, message: Message) -> bool:
        # 模拟AI回复
        if message.content.startswith("问："):
            question = message.content[2:]
            await self.send_message(f"[GPT] 关于 '{question}' 的想法：这是一个有趣的问题...")
            logger.info(f"GPT answered question: {question[:30]}...")
            return False  # GPT处理完，中断传递
        return True  # 不是问AI的问题，继续传递


@register_plugin("game", layer=2, description="游戏插件：简单的猜数字游戏")
class GamePlugin(Plugin):
    """2层插件示例 - 游戏（应用层，独占）"""

    def on_activate(self):
        self.target_number = 42
        self.guesses = []
        logger.info(f"Game plugin activated, target number: {self.target_number}")

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
                await self.send_message(f"[Game] 恭喜你猜对了！答案是 {self.target_number}")
                logger.success(f"Number guessed! Answer was {self.target_number}, {len(self.guesses)} attempts")
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


@register_plugin("chat", layer=1, description="聊天插件：简单对话")
class ChatPlugin(Plugin):
    """1层插件示例 - 聊天（命令层，共享）"""

    async def handle_message(self, message: Message) -> bool:
        replies = {
            "天气": "今天天气不错！",
            "吃饭": "我推荐你去吃好吃的！",
            "名字": "我是 DoroBot，你的多插件机器人助手！",
        }

        for keyword, reply in replies.items():
            if keyword in message.content:
                await self.send_message(f"🤖 {reply}")
                return False

        return True
