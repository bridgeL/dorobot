"""消息数据类"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Message:
    """消息数据类"""

    content: str
    sender_id: str
    sender_name: str
    session_id: str = ""
    session_type: str = "session"  # group, private
    group_id: str = ""
    user_id: str = ""
    raw_data: Optional[dict] = None
