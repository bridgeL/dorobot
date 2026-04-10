"""犯罪舞蹈 V2 - 基于 AppPlugin 状态机

状态转移:
  idle -> room.waiting (创建房间)
  room.waiting -> idle (解散房间)
  room.waiting -> room.starting (开始游戏)
  room.waiting -> room.waiting (加入/离开)
  room.starting -> game.play (发牌完毕)
  game.play -> game.play (正常出牌)
  game.play -> game.trade (交易)
  game.play -> game.exchange (情报交换)
  game.play -> game.ended (游戏结束)
  game.trade -> game.play (交易完成)
  game.exchange -> game.play (情报交换完成)
  game.ended -> room.waiting (再来一局)
  game.ended -> idle (解散)
"""

from .plugin import app
from . import room
from . import game as _  # noqa: F401 - 导入用于触发装饰器注册


# ========== 生命周期 ==========

@app.on_open()
async def on_open():
    """插件启动"""
    app.set_state("idle")
    room.setup_room_space()
    await app.send_message(
        "🎭 犯罪舞蹈 V2\n"
        "发送【创建房间】开始\n"
        "发送【帮助】查看规则"
    )


# ========== 全局命令 ==========

@app.on_command(None, ["帮助", "游戏帮助"])
async def cmd_help_global(message, args: str):
    """全局帮助"""
    state = app.get_state()

    if state == "idle":
        msg = (
            "🎭 犯罪舞蹈 V2\n"
            "【创建房间】- 创建新房间\n"
            "【帮助】- 查看规则"
        )
    elif state.startswith("room"):
        msg = (
            "🎭 房间命令\n"
            "【加入】- 加入房间\n"
            "【开始】- 开始游戏（房主）\n"
            "【解散】- 解散房间（房主）\n"
            "【离开】- 离开房间\n"
            "【状态】- 查看房间状态"
        )
    elif state.startswith("game"):
        msg = (
            "🎭 游戏命令\n"
            "【出牌 牌名 @目标】- 出牌\n"
            "【手牌】- 查看手牌（私聊）\n"
            "【状态】- 查看游戏状态\n"
            "【结束】- 结束游戏（房主）"
        )
    else:
        msg = "发送【帮助】查看当前可用命令"

    await app.send_message(msg)


# 注册插件
app.register()
