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
#from ...database.db import AuthData
from ...utils import get_dynamic_screenshot, safe_send, scheduler, get_credential

from bilibili_api import user, sync, Credential

async def dy_sched():
    """动态推送"""
    uid = await db.next_uid("dynamic")
    #if not uid or not AuthData.auth:
    if not uid:
        # 没有订阅先暂停一秒再跳过，不然会导致 CPU 占用过高
        await asyncio.sleep(1)
        return
    u = await db.get_user(uid=uid)
    assert u is not None
    name = u.name

    logger.debug(f"爬取动态 {name}（{uid}）")
    try:
        # 获取cookies
        credential = get_credential()
        # 获取 UP 最新动态列表
        dynamics = await get_latest_dynamic(uid, credential)

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
            return

    dynamic = None
    for dynamic in dynamics:
        # 提取动态信息
        try:
            res = get_dynamic_info(dynamic)
            dynamic_id = res['id'] # 实际是timestamp
            dtype = res['type']
            upload_time = res['upload_time']
            name = res['name']
            title = res['title']
            description = res['content']
            images = res['images']
        except Exception as e:
            logger.error(f"加载动态卡片时出现问题：{e}")
            continue

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
                f"{name}{dtype}：\n"
                #+ str(f"动态图片可能截图异常：{err}\n" if err else "")
                #+ MessageSegment.image(image)
                #+ f"\n{url}"
                + f"{title}\n"
                + f"{description}\n"
                + f"发布时间：{upload_time}\n"
                + f"图片/分P数量：{images}\n"
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

            # 保存并更新信息
            offset[uid] = dynamic_id
            await db.update_user(uid, name)
            break

async def get_latest_dynamic(uid, credential):
    u = user.User(uid=uid, credential=credential)
    # 用于记录下一次起点
    offset = 0
    
    # 用于存储所有动态
    dynamics = []

    page = await u.get_dynamics(offset=offset)
    '''try:
        # 抓动态
        page = await u.get_dynamics(offset=offset)
    except Exception:
        # 刷新cookies
        if await AuthData.auth.check_refresh():
            await AuthData.auth.refresh()
            db.add_login({
                "sessdata": AuthData.auth.sessdata,
                "bili_jct": AuthData.auth.bili_jct,
                "ac_time_value": AuthData.auth.ac_time_value,
                "dedeuserid": AuthData.auth.dedeuserid,
            })

        page = await u.get_dynamics_new(offset=offset)'''

    if 'cards' in page:
        # 若存在 cards 字段（即动态数据），则将该字段列表扩展到 dynamics
        #print(page)
        dynamics.extend(page['cards'])
        
    return dynamics

def get_dynamic_info(dynamic: dict):
    '根据动态类型返回不同解析值'
    dtype = dynamic['desc']['type']
    card = dynamic['card']

    # 对不一定存在的项目初始化
    images = 0
    title = ""
    '''if dtype < 8:
        id = dynamic['desc']['dynamic_id']
    else:
        id = -1'''

    if dtype == 1:
        # 转发
        dtype = "转发动态"
        name = card['user']['uname']
        content = card['item']['content']
        upload_timestamp = dynamic['desc']['timestamp']
    elif dtype == 2:
        # 图文动态
        dtype = "发布图文动态"
        name = card['user']['name']
        # title = card['item']['title'] # TODO: 这个title到底是从哪里抓出来的啊。。
        content = card['item']['description']
        upload_timestamp = card['item']['upload_time']
        images = card['item']['pictures_count']
    elif dtype == 4:
        # 文字动态
        dtype = "发布纯文字动态"
        name = card['user']['uname']
        content = card['item']['content']
        upload_timestamp = dynamic['desc']['timestamp']
    elif dtype == 8:
        # 投稿视频
        dtype = "发布视频"
        name = card['owner']['name']
        content = card['desc']
        upload_timestamp = card['pubdate']
        title = card['title']
        images = card['videos']
    elif dtype == 64:
        # 投稿专栏
        dtype = "发布专栏"
        name = card['author']['name']
        content = card['summary']
        upload_timestamp = card['publish_time']
        title = card['title']
    elif dtype == 256:
        # 投稿音频
        dtype = "发布音频"
        name = card['upper']
        content = card['intro']
        upload_timestamp = card['ctime'] // 1000 # 音频的时间戳多3个0
        title = card['title']

    upload_time = datetime.fromtimestamp(upload_timestamp).strftime(r"%Y/%m/%d %H:%M:%S")
    return {
        'id': upload_timestamp, # 用时间戳代替动态id
        'type': dtype,
        'upload_time': upload_time,
        'name': name,
        'title': title,
        'content': content,
        'images': images
    }

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
