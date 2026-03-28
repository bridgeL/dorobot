"""Adapter 基类定义

定义 Adapter 的标准接口，所有 Adapter 实现必须继承此类。
"""
from abc import ABC, abstractmethod


class Adapter(ABC):
    name: str = "adapter"

    def __init__(self):
        pass

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def stop(self):
        pass