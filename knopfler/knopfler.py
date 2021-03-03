import json

from sanic import Sanic, response
from sanic.request import Request


class MatrixBot:
    def __init__(self, bot_config):
        from matrix_client.client import MatrixClient
        self.bot = MatrixClient(bot_config["server"], user_id=bot_config["user_id"], token=bot_config["token"])

    def get_link(self, channel):
        async def link(request: Request):
            print(request.method)
            print(request.body)
            room = self.bot.join_room(channel)
            room.send_html(f"{request.method} - {request.body}")
            return response.json({'status': 'ok'})

        return link


class RocketBot:
    def __init__(self, bot_config):
        from RocketChatBot import RocketChatBot
        self.bot = RocketChatBot(bot_config["user"], bot_config["password"], bot_config["server"])

    def get_link(self, channel):
        async def link(request: Request):
            print(request.method)
            print(request.body)
            self.bot.send_message(f"{request.method} - {request.body}", channel)
            return response.json({'status': 'ok'})

        return link


class Knopfler:
    def __init__(self):
        self.app = Sanic(name="knopfler")
        config = json.load(open('knopfler.json'))
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


if __name__ == '__main__':
    # socket:
    # import socket
    #
    # sock = socket.socket(socket.AF_UNIX)
    # sock.bind('/tmp/api.sock')
    # Knopfler().app.run(sock=sock)
    Knopfler().app.run(host='0.0.0.0', port=9282)
