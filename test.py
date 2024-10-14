import json
from bilibili_api import user, sync, Credential
import datetime

async def main():
    kwargs = {
        "sessdata": "2e2c66bd%2C1744089179%2C57a80aa1CjBBfmHT4w5aJOIfKasssK6klgax-OWvPpSMGpppeX239v9TS7RtOkfgSZK551-m-AISVjdvUWFqdHlNVnBfMHVtcDg0TVpTYnBXal9RUGdjWGNuMW1QUl9fYVZSMGNXWmdiaWU4SkdVMENfUzRWOW9nM1JodEpYX1hhM1dCTFF5TG1NaGVrSmJ3IIEC", 
        "bili_jct": "0075945fd96256417c8bfe0ee8faa577", 
        "dedeuserid": "313019770", 
        }
    c = Credential(**kwargs)
    u = user.User(1950658, credential=c)
    # 用于记录下一次起点
    offset = 0
    
    # 用于存储所有动态
    dynamics = []

    #page = await u.get_dynamics_new(offset=offset)
    page = await u.get_dynamics()
    
    if 'cards' in page:
        # 若存在 cards 字段（即动态数据），则将该字段列表扩展到 dynamics
        #print(page)
        dynamics.extend(page['cards'])
        
    # 打印动态数量
    print(f"共有 {len(dynamics)} 条动态")
    print(json.dumps(dynamics[0]))

    # 提取动态信息
    last_dynamic_id = dynamics[0]['desc']['dynamic_id']
    description = dynamics[0]['card']['item']['description']
    upload_timestamp = dynamics[0]['card']['item']['upload_time']
    upload_time = datetime.datetime.fromtimestamp(upload_timestamp).strftime(r"%Y/%m/%d, %H:%M:%S")

    return {
        'last_dynamic_id': last_dynamic_id,
        'description': description,
        'upload_time': upload_time,
    }

# 入口

if __name__ == "__main__":
    #import haruka_bot.plugins.pusher.dynamic_pusher as dynamic
    sync(main())
