import asyncio
import json
from urllib.request import urlopen

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def format_alert(msg, html=False):
    try:
        alerts = json.loads(msg)["alerts"]
    except:
        return f"Error trying to parse JSON!!!\n\n{msg}"
    ret = []
    for alert in alerts:
        labels = alert["labels"]
        status = "🔥" if alert["status"] == "firing" else "✅"
        ret += [
            f"[{status} {alert['status']}] {labels['instance']}: {labels['alertname']} {labels.get('name','')}"
        ]
    if html:
        return "<br>".join(ret)
    return "\n".join(ret)


class MatrixBot:
    def __init__(self, bot_config):
        from matrix_client.client import MatrixClient

        self.bot = MatrixClient(
            bot_config["server"],
            user_id=bot_config["user_id"],
            token=bot_config["token"],
        )

    def get_link(self, channel):
        room = self.bot.join_room(channel)

        async def link(request: Request):
            if request.method == "GET":
                return Response("this is just an endpoint for the alertmanager")
            room.send_html(format_alert(request.body, html=True))
            return JSONResponse({"status": "ok"})

        return link


class RocketBot:
    def __init__(self, bot_config):
        from RocketChatBot import RocketChatBot

        self.bot = RocketChatBot(
            bot_config["user"], bot_config["password"], bot_config["server"]
        )

    def get_link(self, channel):
        async def link(request: Request):
            if request.method == "GET":
                return Response("this is just an endpoint for the alertmanager")
            self.bot.send_message(format_alert(request.body), channel)
            return JSONResponse({"status": "ok"})

        return link


config = json.load(open("knopfler.json"))

app = Starlette(debug=True)


bots = {}
for bot in config.get("bots",[]):
    if bot["type"] == "rocket":
        bots[bot["name"]] = RocketBot(bot)
    if bot["type"] == "matrix":
        bots[bot["name"]] = MatrixBot(bot)
for link in config.get("links",[]):
    newroute = bots[link["bot"]].get_link(link["channel"])
    if not link["url"].startswith("/"):
        link["url"] = f"/{link['url']}"
    app.add_route(link["url"], newroute, methods=["GET", "POST"])


async def home(request: Request):
    return Response("♫ knopfler is up and running")


app.add_route("/", home)

if config.get("healthcheck"):

    async def send_heartbeat():
        while True:
            urlopen(config["healthcheck"])
            await asyncio.sleep(60 * 5)

    @app.on_event("startup")
    async def startup():
        asyncio.create_task(send_heartbeat())


def main():
    if config.get("unix-socket"):
        uvicorn.run("knopfler:app", uds="knopfler.socket")
    else:
        uvicorn.run("knopfler:app", host="0.0.0.0", port=9282)
