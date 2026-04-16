"""犯人在跳舞插件"""

from .plugin import app

# 测试命令（不导入则不注册）
from . import test

__all__ = ["app"]
