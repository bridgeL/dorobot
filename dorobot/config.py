"""DoroBot 配置"""

import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Config:
    """DoroBot 配置类"""

    cmd_prefix: str = os.getenv("CMD_PREFIX", "/")


# 全局配置实例
global_config = Config()
