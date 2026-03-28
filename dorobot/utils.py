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
        logs_dir / "bot.log",
        format=format_str,
        level=level,
        rotation="00:00",  # 每天午夜轮转
        retention="30 days",  # 保留30天
        compression="zip"  # 压缩旧日志
    )

    logger.debug(f"Logging initialized with level: {level}")


def load_plugins(plugins_dir: str | Path | None = None, package: str = "plugins"):
    """自动加载指定目录下的所有插件

    扫描目录中的 .py 文件（排除 __ 开头），自动 import 并注册插件。
    插件在注册时会自动实例化。

    Args:
        plugins_dir: 插件目录路径，None 则使用当前工作目录下的 plugins/
        package: 模块包名，用于 import，默认 "plugins"

    Returns:
        list[str]: 成功加载的插件模块名列表
    """

    if plugins_dir is None:
        plugins_dir = Path.cwd() / "plugins"
    else:
        plugins_dir = Path(plugins_dir)

    if not plugins_dir.exists():
        logger.warning(f"Plugins directory not found: {plugins_dir}")
        return []

    logger.info(f"Loading plugins from: {plugins_dir}")

    plugin_files = [
        f for f in plugins_dir.glob("*.py")
        if not f.name.startswith("_")
    ]

    loaded = []
    for file_path in sorted(plugin_files):
        module_name = f"{package}.{file_path.stem}"
        try:
            importlib.import_module(module_name)
            logger.info(f"Loaded plugin module: {file_path.name}")
            loaded.append(file_path.stem)
        except Exception as e:
            logger.error(f"Failed to load plugin {file_path.name}: {e}")

    return loaded


def run():
    """启动 DoroBot，阻塞直到收到 KeyboardInterrupt"""
    from .adapter_manager import adapter_manager

    async def _run():
        logger.info("=" * 50)
        logger.info("DoroBot Starting...")
        logger.info("=" * 50)

        # adapter 管理外部系统生命周期
        # adapter.start() 会注册 bot 到 bot_manager，并启动它们
        await adapter_manager.start_all()

        # 保持运行直到收到停止信号
        while True:
            await asyncio.sleep(1)

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("DoroBot stopped")
