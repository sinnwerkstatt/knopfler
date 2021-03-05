import asyncio
import json
from urllib.request import urlopen

from sanic import Sanic, response
from sanic.request import Request


def format_alert(msg, html=False):
    try:
        alerts = json.loads(msg)["alerts"]
    except:
        return f"Error trying to parse JSON!!!\n\n{msg}"
    ret = []
    for alert in alerts:
        labels = alert["labels"]
        ret += [
            f"[{alert['status']}] {labels['instance']}: {labels['alertname']} {labels.get('name','')}"
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
                return response.text("this is just an endpoint for the alertmanager")
            room.send_html(format_alert(request.body, html=True))
            return response.json({"status": "ok"})

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
                return response.text("this is just an endpoint for the alertmanager")
            self.bot.send_message(format_alert(request.body), channel)
            return response.json({"status": "ok"})

        return link


class Knopfler:
    def __init__(self, config):
        self.app = Sanic(name="knopfler")
        self.bots = {}
        for bot in config.get("bots"):
            if bot["type"] == "rocket":
                self.bots[bot["name"]] = RocketBot(bot)
            if bot["type"] == "matrix":
                self.bots[bot["name"]] = MatrixBot(bot)

        for link in config.get("links"):
            newroute = self.bots[link["bot"]].get_link(link["channel"])
            self.app.add_route(newroute, link["url"], methods=("GET", "POST"))

        async def home(request):
            return response.text("♫ knopfler is up and running")

        self.app.add_route(home, "/")

        if config.get("healthcheck"):

            async def healthcheck_task():
                while True:
                    urlopen(config["healthcheck"])
                    await asyncio.sleep(60 * 5)

            self.app.add_task(healthcheck_task)


def main():
    config = json.load(open("knopfler.json"))
    knopfler = Knopfler(config)
    if config.get("unix-socket"):
        import os
        import socket

        with socket.socket(socket.AF_UNIX) as sock:
            sock.bind("knopfler.socket")
            knopfler.app.run(sock=sock)
        os.remove("knopfler.socket")
    else:
        knopfler.app.run(host="0.0.0.0", port=9282)


if __name__ == "__main__":
    main()
