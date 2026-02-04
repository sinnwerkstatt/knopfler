import asyncio
import json
from typing import ClassVar, Literal
from urllib.request import urlopen

import uvicorn
from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class AlertLabel(BaseModel):
    instance: str
    alertname: str
    name: str = ""


class AlertMsg(BaseModel):
    labels: AlertLabel
    status: Literal["firing"] | str


class AlertsMsgFormat(BaseModel):
    alerts: list[AlertMsg]


class ConfigBot(BaseModel):
    name: str
    type: Literal["matrix", "rocket"]
    user_id: str
    token: str
    server: str


class ConfigLink(BaseModel):
    bot: str
    url: str
    channel: str


class Config(BaseModel):
    bots: list[ConfigBot]
    links: list[ConfigLink]
    healthcheck: str | None = None
    unix_socket: bool = Field(default=False, alias="unix-socket")


def format_alert(msg: AlertsMsgFormat, html=False):
    try:
        alerts = msg.alerts
    except KeyError:
        return f"Error trying to parse JSON!!!\n\n{msg}"
    ret = []
    for alert in alerts:
        labels = alert.labels
        status = "🔥" if alert.status == "firing" else "✅"
        ret += [
            f"[{status} {alert.status}]",
            f"{labels.instance}: {labels.alertname} {labels.name}",
        ]
    if html:
        return "<br>".join(ret)
    return "\n".join(ret)


class MatrixBot:
    joined_rooms: ClassVar = {}

    def __init__(self, bot_config: ConfigBot):
        from nio import AsyncClient  # noqa PLC0415

        self.bot = AsyncClient(bot_config.server, bot_config.user_id)
        self.bot.access_token = bot_config.token

    def get_link(self, channel):
        async def link_fn(request: Request):
            if request.method == "GET":
                return Response("this is just an endpoint for the alertmanager")

            data = await request.json()
            alerts = AlertsMsgFormat(**data)

            if channel not in self.joined_rooms:
                join_res = await self.bot.join(channel)
                try:
                    self.joined_rooms[channel] = join_res.room_id
                except AttributeError as e:
                    raise Exception("Expected the join to succeed") from e

            target_room_id = self.joined_rooms[channel]

            await self.bot.room_send(
                room_id=target_room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": format_alert(alerts, html=False),
                    "format": "org.matrix.custom.html",
                    "formatted_body": format_alert(alerts, html=True),
                },
            )

            return JSONResponse({"status": "ok"})

        return link_fn


# disable, I don't think anybody uses this anymore?
# class RocketBot:
#     def __init__(self, bot_config:ConfigBot):
#         from RocketChatBot import RocketChatBot
#
#         self.bot = RocketChatBot(
#             bot_config.user, bot_config.password, bot_config["server"]
#         )
#
#     def get_link(self, channel):
#         async def link(request: Request):
#             if request.method == "GET":
#                 return Response("this is just an endpoint for the alertmanager")
#
#             data = await request.json()
#             alerts = AlertsMsgFormat(**data)
#             self.bot.send_message(format_alert(alerts), channel)
#             return JSONResponse({"status": "ok"})
#
#         return link


config_data = json.load(open("knopfler.json"))
config = Config(**config_data)

app = Starlette(debug=True)

bots = {}
for bot in config.bots:
    if bot.type == "rocket":
        raise Exception("Is anybody using knopfer? With rocket? Let me know")
        # bots[bot.name] = RocketBot(bot)
    if bot.type == "matrix":
        bots[bot.name] = MatrixBot(bot)

for link in config.links:
    newroute = bots[link.bot].get_link(link.channel)
    if not link.url.startswith("/"):
        link.url = f"/{link.url}"
    app.add_route(link.url, newroute, methods=["GET", "POST"])


async def home(_request: Request):
    return Response("♫ knopfler is up and running")


app.add_route("/", home)

heartbeat_tasks = set()

if config.healthcheck:

    async def send_heartbeat():
        while True:
            urlopen(config.healthcheck)  # noqa: S310
            await asyncio.sleep(60 * 5)

    @app.on_event("startup")
    async def startup():
        task = asyncio.create_task(send_heartbeat())
        heartbeat_tasks.add(task)
        task.add_done_callback(heartbeat_tasks.discard)


def main():
    if config.unix_socket:
        uvicorn.run("knopfler:app", uds="knopfler.socket")
    else:
        uvicorn.run("knopfler:app", host="0.0.0.0", port=9282)  # noqa: S104
