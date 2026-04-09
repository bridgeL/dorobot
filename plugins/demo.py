"""示例插件集合"""
from collections import Counter
from loguru import logger
from dorobot import Plugin, Message, register_plugin


@register_plugin("字频统计", layer=1, description="统计群里各成员的字频")
class CharFreqPlugin(Plugin):
    """1层插件示例 - 字频统计（共享层）"""

    async def handle_message(self, message: Message) -> bool:
        char_space = self.get_space(memory=False)

        if message.content.strip() == "/result":
            # 查看结果
            if not char_space:
                await self.send_message("暂无字频数据")
            else:
                top10 = Counter(dict(char_space)).most_common(10)
                lines = [f"📊 本群字频 Top10："]
                for i, (char, count) in enumerate(top10, 1):
                    lines.append(f"  {i}.「{char}」×{count}")
                await self.send_message("\n".join(lines))
            return False

        # 统计字频
        for char in message.content:
            if char.strip():
                char_space[char] = char_space.get(char, 0) + 1
        return True


@register_plugin("game", layer=2, description="游戏插件：简单的猜数字游戏")
class GamePlugin(Plugin):
    """2层插件示例 - 游戏（独占层）"""

    async def on_activate(self):
        self.get_space()["target"] = 42
        self.get_space()["guesses"] = []
        await self.send_message("游戏开始！请输入一个 0-99 的数字来猜数。")

    async def handle_message(self, message: Message) -> bool:
        space = self.get_space()
        target = space["target"]
        guesses: list = space["guesses"]

        # 处理猜数字
        try:
            guess = int(message.content)
            guesses.append(guess)

            if guess < target:
                await self.send_message(f"[Game] {guess} 太小了！")
            elif guess > target:
                await self.send_message(f"[Game] {guess} 太大了！")
            else:
                await self.send_message(f"[Game] 恭喜你猜对了！答案是 {target}")
                logger.info(
                    f"Number guessed! Answer was {target}, {len(guesses)} attempts"
                )
                space["target"] = (target + 13) % 100  # 换一个新数字

            return False  # 游戏处理完，中断传递

        except ValueError:
            # 不是数字，继续传递
            return True

