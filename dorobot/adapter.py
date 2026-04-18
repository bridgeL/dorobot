"""Adapter 基类定义

定义 Adapter 的标准接口，所有 Adapter 实现必须继承此类。
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .dorobot import Dorobot


class Adapter(ABC):
    name: str = "adapter"

    def __init__(self):
        self._dorobot: Optional["Dorobot"] = None

    def bind_dorobot(self, dorobot: "Dorobot") -> None:
        """绑定 Dorobot 实例"""
        self._dorobot = dorobot

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def stop(self):
        pass
