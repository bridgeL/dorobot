"""Space 管理器 - 管理所有 Space 实例的持久化"""

import asyncio
from pathlib import Path

from .space import Space


class SpaceManager:
    """Space 管理器

    管理所有 Space 实例的持久化（保存到磁盘）。
    注意：Space 本身通过 _instances 实现了单例模式，同名 name 只会创建一个实例。
    space_manager 的作用是统一管理所有 Space 的持久化，二者职责不同：
    - Space._instances：解决同名 Space 的单例问题，确保同一 name 只创建一个实例
    - space_manager：负责定期扫描 dirty 的 Space 并保存到磁盘
    这样做的好处是，即使 Space 没有注册到 space_manager（如 memory=True），
    也不影响其他 Space 的持久化。
    """

    def __init__(self):
        self.spaces: dict[str, Space] = {}
        self._running = False
        self._task: asyncio.Task | None = None

    def register(self, space: Space):
        """注册 Space 实例"""
        self.spaces[space.name] = space

    def init(self):
        """从磁盘加载所有 Space 数据

        遍历 space/ 目录下的所有 .json 文件，加载对应的 Space。
        注意：Space.__new__ 已实现单例模式，同名 name 不会重复实例化。
        """

        space_dir = Path("space")
        if not space_dir.exists():
            return

        for json_path in space_dir.rglob("*.json"):
            rel_path = json_path.relative_to(space_dir)
            # 将路径转回 names：a/b/c.json -> ("a", "b", "c")
            name_parts = tuple(str(rel_path)[:-5].split("/"))
            Space(*name_parts)  # 单例获取或创建


def init_space():
    """初始化 Space 持久化，从磁盘加载数据"""
    space_manager.init()

    async def _scan_loop(self):
        """定期扫描并保存 dirty 的 Space"""
        while self._running:
            for space in list(self.spaces.values()):
                if space.dirty:
                    space.save()
            await asyncio.sleep(1)

    def start(self):
        """启动定期保存任务"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._scan_loop())

    def stop(self):
        """停止定期保存任务并保存所有"""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        # 保存所有 dirty 的 Space
        for space in self.spaces.values():
            if space.dirty:
                space.save()


# 全局单例
space_manager = SpaceManager()
