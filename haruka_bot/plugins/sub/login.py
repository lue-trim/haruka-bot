from bilireq.auth import WebAuth
from nonebot.adapters.onebot.v11.event import MessageEvent

from pathlib import Path

from ...database import DB as db
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

login_action = on_command("登录", rule=to_me(), priority=5)
login_action.__doc__ = """登录 sessdata"""

login_action.handle()

login_action.got("uid", prompt="请输入sessdata")


@login_action.handle()
async def _(event: MessageEvent, data: str):
    """保存登录信息"""
    from ...database.db import AuthData
    import json
    # 加载数据
    data_json = json.loads(data)

    # 取出参数
    refresh_token = data_json['token']['tokens']['refresh_token']
    cookies = data_json['cookie']['cookies']
    AuthData.auth = WebAuth(auth={"refresh_token": refresh_token, "cookies": cookies})

    await login_action.finish("已保存登录信息")
