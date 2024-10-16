from nonebot.adapters.onebot.v11.event import MessageEvent

from pathlib import Path

from ...database import DB as db
from ...database.db import AuthData
from ...utils import (
    PROXIES,
    get_type_id,
    handle_uid,
    on_command,
    permission_check,
    to_me,
    uid_check,
    get_path,
)

logout_action = on_command("退出登录", rule=to_me(), priority=5)
logout_action.__doc__ = """退出登录 （清除B站鉴权信息）"""

logout_action.handle()

@logout_action.handle()
async def _(event: MessageEvent):
    """删除登录信息"""
    AuthData.auth = None
    await db.del_login()

    await logout_action.finish(f"已删除登录信息")
