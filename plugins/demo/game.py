"""猜数字游戏插件"""

from loguru import logger
from dorobot import Plugin, Message


app = Plugin(
    name="game", layer=2, description="游戏插件：简单的猜数字游戏", default_active=False
)


@app.on_open()
async def on_open():
    space = app.get_space()
    space["target"] = 42
    space["guesses"] = []
    await app.send_message("游戏开始！请输入一个 0-99 的数字来猜数。")


@app.on_message()
async def handle(msg: Message) -> bool:
    space = app.get_space()
    target = space["target"]
    guesses: list = space["guesses"]

    try:
        guess = int(msg.content)
        guesses.append(guess)

        if guess < target:
            await app.send_message(f"[Game] {guess} 太小了！")
        elif guess > target:
            await app.send_message(f"[Game] {guess} 太大了！")
        else:
            await app.send_message(f"[Game] 恭喜你猜对了！答案是 {target}")
            logger.info(f"Number guessed! Answer was {target}, {len(guesses)} attempts")
            space["target"] = (target + 13) % 100

        return False

    except ValueError:
        return True


app.register()
