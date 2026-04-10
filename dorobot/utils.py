"""DoroBot 工具函数"""
import sys
import asyncio
import importlib
from pathlib import Path
from loguru import logger


def init_logging(
    level: str = "INFO",
    format_str: str | None = None,
    sink = sys.stdout
):
    """初始化日志配置

    Args:
        level: 日志级别，默认 INFO
        format_str: 自定义格式，None 使用默认格式
        sink: 输出目标，默认 sys.stdout
    """
    logger.remove()

    if format_str is None:
        format_str = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )

    # 添加控制台输出
    logger.add(sink, format=format_str, level=level)

    # 添加文件输出，每天轮转
    logs_dir = Path.cwd() / "logs"
    logs_dir.mkdir(exist_ok=True)

    logger.add(
        logs_dir / "{time:YYYY-MM-DD}.log",
        format=format_str,
        level=level,
        rotation="1 day",  # 每天轮转
        retention="30 days",  # 保留30天
        compression="zip"  # 压缩旧日志
    )

    logger.debug(f"Logging initialized with level: {level}")


def load_plugins():
    """自动加载插件目录下所有插件

    扫描 plugins/ 目录下的 .py 文件（排除 __ 开头），自动 import 并注册插件。
    插件在注册时会自动实例化。

    Returns:
        list[str]: 成功加载的插件模块名列表
    """
    plugins_dir = Path.cwd() / "plugins"
    if not plugins_dir.exists():
        logger.warning(f"Plugins directory not found: {plugins_dir}")
        return []

    logger.info(f"Loading plugins from: {plugins_dir}")

    # 收集要加载的插件: (module_name)
    plugins_to_load = []

    # 扫描根目录插件: plugins/*.py
    for f in plugins_dir.glob("*.py"):
        if not f.name.startswith("_"):
            plugins_to_load.append(f"plugins.{f.stem}")

    # 扫描子目录插件: plugins/*/__init__.py
    for subdir in plugins_dir.iterdir():
        # 如果有__init__.py，说明这是一个包，可以直接加载
        if subdir.is_dir() and not subdir.name.startswith("_") and (subdir / "__init__.py").exists():
            plugins_to_load.append(f"plugins.{subdir.name}")

    loaded = []
    for module_name in sorted(plugins_to_load):
        try:
            logger.debug(f"Loading plugin module: {module_name}")
            importlib.import_module(module_name)
            loaded.append(module_name)
        except Exception as e:
            logger.exception(f"Failed to load plugin {module_name}: {e}")

    return loaded


def run():
    """启动 DoroBot，阻塞直到收到 KeyboardInterrupt"""
    from .adapter_manager import adapter_manager
    from .space_manager import space_manager

    async def _run():
        logger.info("=" * 50)
        logger.info("DoroBot Starting...")
        logger.info("=" * 50)

        # adapter 管理外部系统生命周期
        # adapter.start() 会注册 bot 到 bot_manager，并启动它们
        await adapter_manager.start_all()

        # 启动 Space 持久化任务
        space_manager.start()

        # 保持运行直到收到停止信号
        while True:
            await asyncio.sleep(1)

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass
    finally:
        space_manager.stop()
        logger.info("DoroBot stopped")
