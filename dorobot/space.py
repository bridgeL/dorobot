"""分层命名空间 - 支持层次化数据存储与持久化"""

import json
from pathlib import Path


class Space(dict):
    """分层命名空间

    继承自 dict，支持键值存储。
    命名规则：使用 `.` 分隔层级，如 `user.profile` 对应 `space/user/profile.json`。
    """

    _instances: dict[str, "Space"] = {}

    def __new__(cls, name: str):
        """单例模式：同名 name 返回已有实例"""
        if name in cls._instances:
            return cls._instances[name]
        instance = super().__new__(cls)
        cls._instances[name] = instance
        return instance

    def __init__(self, name: str):
        """初始化空间

        Args:
            name: 空间名称，使用 `.` 分隔层级，如 `user.profile`
        """
        super().__init__()
        self._name = name
        self._dirty = False
        # 自动注册到 manager
        from dorobot.space_manager import space_manager

        space_manager.register(self)

    @property
    def name(self) -> str:
        return self._name

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
        """获取文件路径，将 `.` 转换为 `/`，末尾加 `.json`

        例如 `user.profile` -> `space/user/profile.json`
        """
        parts = self._name.split(".")
        return str(Path("space") / "/".join(parts)) + ".json"

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
        return f"Space({self._name!r})"
