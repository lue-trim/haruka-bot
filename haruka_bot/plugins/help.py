from nonebot.matcher import matchers

from ..utils import on_command, to_me
from ..version import __version__

help = on_command("帮助", rule=to_me(), priority=5)


@help.handle()
async def _():
    message = ""
    message += """\
快速使用：
使用"/关注 <UID>"添加想要推送的主播，使用"/关注列表"确认推送开关的状态
私人订制：
可以点击机器人头像私信并发送操作指令，私信内容与大屏推送完全独立
"""
    message += "完整功能列表：\n"
    for matchers_list in matchers.values():
        for matcher in matchers_list:
            if (
                matcher.plugin_name
                and matcher.plugin_name.startswith("haruka_bot")
                and matcher.__doc__
            ):
                message += matcher.__doc__ + "\n"
    message += f"\n当前版本：HarukaBot修改版 {__version__}\n" #"详细帮助：https://haruka-bot.sk415.icu/usage/"
    await help.finish(message)
