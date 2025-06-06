import time

from bilireq.live import get_rooms_info_by_uids
from nonebot.adapters.onebot.v11.message import MessageSegment
from nonebot.log import logger

from ...config import plugin_config
from ...database import DB as db
from ...utils import PROXIES, safe_send, scheduler, calc_time_total, send_admin
import functools, traceback
from aiohttp import BasicAuth, ClientSession

status = {}
live_time = {}


@scheduler.scheduled_job(
    "interval", seconds=plugin_config.haruka_live_interval, id="live_sched"
)
async def live_sched():
    # sourcery skip: use-fstring-for-concatenation
    """直播推送"""
    uids = await db.get_uid_list("live")
    uids = uids.copy()
    if -1 in uids:
        # 不要检查uid == -1的订阅项
        uids.remove(-1)

        try:
            # 检查有没有新消息
            msg = await get_blrec_msg()
            if msg:
                await send_admin(message=msg, listen_type="live")
        except Exception as e:
            logger.error(f"获取录播消息失败：{e}")
            await send_admin(f"获取录播消息失败：{e}")

    if not uids:  # 订阅为空
        return
    logger.debug(f"爬取直播列表，目前开播{sum(status.values())}人，总共{len(uids)}人")
    res = await get_rooms_info_by_uids(uids, reqtype="web", proxies=PROXIES)
    if not res:
        return
    for uid, info in res.items():
        new_status = 0 if info["live_status"] == 2 else info["live_status"]
        if uid not in status:
            status[uid] = new_status
            continue
        old_status = status[uid]
        if new_status == old_status:  # 直播间状态无变化
            continue
        status[uid] = new_status

        name = info["uname"]
        if new_status:  # 开播
            live_time[uid] = info["live_time"]
            room_id = info["short_id"] or info["room_id"]
            url = f"https://live.bilibili.com/{room_id}"
            title = info["title"]
            cover = info["cover_from_user"] or info["keyframe"]
            area = info["area_v2_name"]
            area_parent = info["area_v2_parent_name"]
            room_area = f"{area_parent} / {area}"
            logger.info(f"检测到开播：{name}（{uid}）")
            live_msg = (
                f"{name} 开播啦！\n分区：{room_area}\n标题：{title}\n"
                #+ MessageSegment.image(cover)
                #+ f"\n{url}"
            )
        else:  # 下播
            logger.info(f"检测到下播：{name}（{uid}）")
            if not plugin_config.haruka_live_off_notify:  # 没开下播推送
                continue
            live_time_msg = (
                f"\n本次直播时长 {calc_time_total(time.time() - live_time[uid])}。"
                if live_time.get(uid)
                else "。"
            )
            live_msg = f"{name} 下播了{live_time_msg}"

        # 推送
        push_list = await db.get_push_list(uid, "live")
        for sets in push_list:
            await safe_send(
                bot_id=sets.bot_id,
                send_type=sets.type,
                type_id=sets.type_id,
                message=live_msg,
                at=bool(sets.at) if new_status else False,  # 下播不@全体
            )
        await db.update_user(int(uid), name)

async def get_blrec_msg():
    '间接获取blrec webhook信息'
    # import requests
    # from requests.auth import HTTPBasicAuth
    # 获取参数
    url = getattr(plugin_config, "messenger_url", "")
    blrec_user = getattr(plugin_config, "blrec_user", "")
    blrec_passwd = getattr(plugin_config, "blrec_passwd", "")
    if url == "":
        return ""

    # 网络请求
    headers = {
        'content-type': 'application/json', 
        }

    params = {
        'type': 'all'
        }

    # response = requests.get(url, params=params, headers=headers, auth=HTTPBasicAuth(username=blrec_user, password=blrec_passwd))
    # res_json = response.json()
    async with ClientSession() as session:
        kwargs = {
            'url': url,
            'method': 'get',
            'params': params,
            'headers': headers,
            'auth': BasicAuth(login=blrec_user, password=blrec_passwd),
        }
        async with session.request(**kwargs) as res:
            res_json = await res.json()
    #print(res_json)
    msg = res_json['message']
    return msg
