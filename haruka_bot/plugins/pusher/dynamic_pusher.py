import asyncio
from datetime import datetime

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
    EVENT_SCHEDULER_STARTED,
)
from bilireq.exceptions import GrpcError
from bilireq.grpc.dynamic import grpc_get_user_dynamics
from bilireq.grpc.protos.bilibili.app.dynamic.v2.dynamic_pb2 import DynamicType
from grpc import StatusCode
from grpc.aio import AioRpcError
from nonebot.adapters.onebot.v11.message import MessageSegment
from nonebot.log import logger

from ...config import plugin_config
from ...database import DB as db
from ...database import dynamic_offset as offset
from ...database.db import AuthData
from ...utils import get_dynamic_screenshot, safe_send, scheduler

from bilibili_api import user, sync, Credential

async def dy_sched():
    """动态推送"""
    uid = await db.next_uid("dynamic")
    if not uid or not AuthData.auth:
        # 没有订阅先暂停一秒再跳过，不然会导致 CPU 占用过高
        await asyncio.sleep(1)
        return
    u = await db.get_user(uid=uid)
    assert u is not None
    name = u.name

    logger.debug(f"爬取动态 {name}（{uid}）")
    try:
        # 获取 UP 最新动态列表
        dynamics = await get_latest_dynamic(uid)
        name = dynamics[0]['desc']['user_profile']["info"]['uname']
        last_dynamic_id = dynamics[0]['desc']['dynamic_id']

    except Exception as e:
        logger.error(f"爬取动态失败：{e}")
        return

    if not dynamics:  # 没发过动态
        if uid in offset and offset[uid] == -1:  # 不记录会导致第一次发动态不推送
            offset[uid] = 0
        return
    # 更新昵称
    #name = dynamics[0]['card']['user']["name"]

    if uid not in offset:  # 已删除
        return
    elif offset[uid] == -1:  # 第一次爬取
        if len(dynamics) == 1:  # 只有一条动态
            offset[uid] = int(last_dynamic_id)
        return

    dynamic = None
    for dynamic in dynamics:
        # 提取动态信息
        description = dynamic['card']['item']['description']
        upload_timestamp = dynamic['card']['item']['upload_time']
        upload_time = datetime.fromtimestamp(upload_timestamp).strftime(r"%Y/%m/%d %H:%M:%S")
        dynamic_id = int(dynamic['desc']['dynamic_id'])

        if dynamic_id > offset[uid]:
            logger.info(f"检测到新动态（{dynamic_id}）：{name}（{uid}）")
            '''
            #image, err = await get_dynamic_screenshot(dynamic_id)
            #url = f"https://t.bilibili.com/{dynamic_id}"
            if image is None:
                logger.debug(f"动态不存在，已跳过：{url}")
                return
            elif dynamic.card_type in [
                DynamicType.live_rcmd,
                DynamicType.live,
                DynamicType.ad,
                DynamicType.banner,
            ]:
                logger.debug(f"无需推送的动态 {dynamic.card_type}，已跳过：{url}")
                offset[uid] = dynamic_id
                return

            type_msg = {
                0: "发布了新动态",
                DynamicType.forward: "转发了一条动态",
                DynamicType.word: "发布了新文字动态",
                DynamicType.draw: "发布了新图文动态",
                DynamicType.av: "发布了新投稿",
                DynamicType.article: "发布了新专栏",
                DynamicType.music: "发布了新音频",
            }'''
            message = (
                f"{name}发布了一条新动态：\n"
                #+ str(f"动态图片可能截图异常：{err}\n" if err else "")
                #+ MessageSegment.image(image)
                #+ f"\n{url}"
                + f"时间：{upload_time}\n"
                + f"内容：{description}\n"
            )

            push_list = await db.get_push_list(uid, "dynamic")
            for sets in push_list:
                await safe_send(
                    bot_id=sets.bot_id,
                    send_type=sets.type,
                    type_id=sets.type_id,
                    message=message,
                    at=bool(sets.at) and plugin_config.haruka_dynamic_at,
                )

            offset[uid] = dynamic_id

    if dynamic:
        await db.update_user(uid, name)

async def get_latest_dynamic(uid):
    u = user.User(uid=uid, credential=AuthData.auth)
    # 用于记录下一次起点
    offset = 0
    
    # 用于存储所有动态
    dynamics = []

    try:
        # 抓动态
        page = await u.get_dynamics(offset=offset)

        # 刷新cookies
        if await AuthData.auth.check_refresh():
            await AuthData.auth.refresh()
            db.add_login({
                "sessdata": AuthData.auth.sessdata,
                "bili_jct": AuthData.auth.bili_jct,
                "ac_time_value": AuthData.auth.ac_time_value,
                "dedeuserid": AuthData.auth.dedeuserid,
            })
    except Exception:
        page = await u.get_dynamics_new(offset=offset)
    
    if 'cards' in page:
        # 若存在 cards 字段（即动态数据），则将该字段列表扩展到 dynamics
        #print(page)
        dynamics.extend(page['cards'])
        
    return dynamics

def dynamic_lisener(event):
    if hasattr(event, "job_id") and event.job_id != "dynamic_sched":
        return
    job = scheduler.get_job("dynamic_sched")
    if not job:
        scheduler.add_job(
            dy_sched, id="dynamic_sched", next_run_time=datetime.now(scheduler.timezone)
        )

if plugin_config.haruka_dynamic_interval == 0:
    scheduler.add_listener(
        dynamic_lisener,
        EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED | EVENT_SCHEDULER_STARTED,
    )
else:
    scheduler.add_job(
        dy_sched,
        "interval",
        seconds=plugin_config.haruka_dynamic_interval,
        id="dynamic_sched",
    )
