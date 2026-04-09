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

app.register()