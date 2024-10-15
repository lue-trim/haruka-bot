from bilibili_api import user
from ...database.db import AuthData

from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.params import ArgPlainText
from nonebot_plugin_guild_patch import GuildMessageEvent

from pathlib import Path

from ...plugins import dynamic_pusher
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

add_sub = on_command("关注", aliases={"添加主播"}, rule=to_me(), priority=5)
add_sub.__doc__ = """关注 UID"""

add_sub.handle()(permission_check)

add_sub.handle()(handle_uid)

add_sub.got("uid", prompt="请输入要关注的UID")(uid_check)


@add_sub.handle()
async def _(event: MessageEvent, uid: str = ArgPlainText("uid")):
    """根据 UID 订阅 UP 主"""
    user = await db.get_user(uid=uid)
    name = user and user.name
    if not name:
        try:
            if not AuthData.auth:
                await add_sub.finish("请先使用sessdata登录")
            dynamics = await get_latest_dynamic(uid)
            name = dynamics[0]['desc']['user_profile']["info"]['uname']
        except Exception as e:
            await add_sub.finish(
                f"未知错误，错误内容：\n\
                {str(e)}"
                )

    if isinstance(event, GuildMessageEvent):
        await db.add_guild(
            guild_id=event.guild_id, channel_id=event.channel_id, admin=True
        )
    result = await db.add_sub(
        uid=uid,
        type=event.message_type,
        type_id=await get_type_id(event),
        bot_id=event.self_id,
        name=name,
        # TODO 自定义默认开关
        live=True,
        dynamic=True,
        at=False,
    )
    if result:
        await add_sub.finish(f"已关注 {name}（{uid}）")
    await add_sub.finish(f"{name}（{uid}）已经关注了")

async def get_user_info(uid):
    '获取用户详情(容易被风控)'
    u = user.User(uid=uid, credential=AuthData.auth)
    return await u.get_user_info()

async def get_latest_dynamic(uid):
    u = user.User(uid=uid, credential=AuthData.auth)
    # 用于记录下一次起点
    offset = 0
    
    # 用于存储所有动态
    dynamics = []

    try:
        page = await u.get_dynamics(offset=offset)
    except Exception:
        page = await u.get_dynamics_new(offset=offset)
    
    if 'cards' in page:
        # 若存在 cards 字段（即动态数据），则将该字段列表扩展到 dynamics
        #print(page)
        dynamics.extend(page['cards'])
        
    return dynamics
