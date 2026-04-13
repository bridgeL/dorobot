"""分层命名空间 - 支持层次化数据存储与持久化"""

import json
from pathlib import Path


class Space(dict):
    """分层命名空间

    继承自 dict，支持键值存储。
    初始化时传入多个名称，如 Space("a", "b", "c") 对应 a/b/c.json。
    """

    _instances: dict[str, "Space"] = {}

    def __new__(cls, *names: str, **kwargs):
        """单例模式：同名 name 返回已有实例"""
        key = "/".join(names)
        if key in cls._instances:
            return cls._instances[key]
        instance = super().__new__(cls)
        cls._instances[key] = instance
        return instance

    def __init__(self, *names: str, memory: bool = False):
        """初始化空间

        Args:
            *names: 空间路径部分，如 Space("a", "b", "c") -> space/a/b/c.json
            memory: 为 True 时不持久化到磁盘，也不从磁盘加载
        """
        # 如果实例已存在且已有数据，不要重复初始化（避免清空数据）
        key = "/".join(names)
        if key in self._instances and len(self) > 0:
            return

        super().__init__()
        self._names = names
        self._key = "/".join(names)
        self._dirty = False
        self._memory = memory
        # memory 模式不注册到 manager，不参与持久化
        if not memory:
            from .context import get_dorobot
            dorobot = get_dorobot()
            if dorobot:
                dorobot.space_manager.register(self)

    @property
    def name(self) -> str:
        return self._key

    @property
    def dirty(self) -> bool:
        return self._dirty

    def mark_dirty(self):
        """标记为已修改"""
        self._dirty = True

    def mark_clean(self):
        """标记为已保存"""
        self._dirty = False

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.mark_dirty()

    def __delitem__(self, key):
        super().__delitem__(key)
        self.mark_dirty()

    def setdefault(self, key, default=None):
        result = super().setdefault(key, default)
        self.mark_dirty()
        return result

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self.mark_dirty()

    def clear(self):
        super().clear()
        self.mark_dirty()

    def path(self) -> str:
        """获取文件路径

        例如 Space("a", "b", "c") -> space/a/b/c.json
        """
        return str(Path("space") / "/".join(self._names)) + ".json"

    def load(self):
        """从磁盘加载数据"""
        path = Path(self.path())
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    super().clear()
                    super().update(data)
                self._dirty = False
            except (json.JSONDecodeError, IOError):
                pass

    def save(self):
        """保存数据到磁盘"""
        if not self._dirty:
            return
        path = Path(self.path())
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(dict(self), f, ensure_ascii=False, indent=2)
            self._dirty = False
        except IOError:
            pass

    def __repr__(self) -> str:
        return f"Space({self._names!r})"
