from nonebot.adapters.onebot.v11.event import MessageEvent
from bilibili_api import Credential

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
login_action.__doc__ = """登录 <cookies> \
    （用于B站相关API鉴权，cookies格式需为包含sessdata/dedeuserid/ac_time_value/bili_jct几个字段的json）"""

login_action.handle()

@login_action.handle()
async def _(event: MessageEvent):
    """保存登录信息"""
    from ...database.db import AuthData
    import json
    # 加载数据
    msg = event.message[0]
    #print(msg)
    msg = msg.data
    msg = msg['text']
    data = '{' + msg.split('{', 1)[1] # 切割数据
    try:
        data_dict = json.loads(data)
    except Exception as e:
        await login_action.finish(f"出现错误：{e}")

    # 取出参数
    AuthData.auth = Credential(**data_dict)
    await db.add_login(**data_dict)

    await login_action.finish(f"已保存登录信息: {data_dict}")
