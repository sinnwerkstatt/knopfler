import logging

import hcl
from matrix_client.client import MatrixClient
from matrix_client.errors import MatrixHttpLibError
from vibora import Request, Route, Vibora

from modules.alertmanager import alertmanager

logger = logging.getLogger("knopfler")


class MatrixLink:
    client: MatrixClient
    server: str
    user_id: str
    token: str
    rooms: dict

    def __init__(self, vibora: Vibora):
        self.vibora = vibora
        try:
            config = hcl.load(open('knopfler.hcl'))
            self.server = config['server']
            self.user_id = config['user']
            self.token = config['token']
        except FileNotFoundError:
            self._setup()
            return
        self.client = MatrixClient(self.server, user_id=self.user_id, token=self.token)
        self.rooms = {}
        if config.get('alerting'):
            self.alerting(config['alerting'])

    def _setup(self):
        self.server = input("Please enter the server name: ")
        user = input("Please enter the user: ")
        passwd = input("Please enter the password: ")
        print()
        try:
            client = MatrixClient(self.server)
            client.login(username=user, password=passwd)
        except MatrixHttpLibError as e:
            print(e)
            print()
            print("Did you specify the server with http/https:// ?")
            return
        config = {"server": self.server, "token": client.token, }
        open('knopfler.hcl', 'w').write(hcl.dumps(config, sort_keys=True, indent=2))
        print("success; saved login credentials to knopfler.hcl")

    def alerting(self, conf):
        self.rooms['alert_room'] = self.client.join_room(conf['room'])

        async def newroute(request: Request):
            return await alertmanager(request, self)

        pattern = f"/hooks{conf['hook']}".encode()
        new_route = Route(pattern, newroute, (b'POST',))
        self.vibora.add_route(new_route)
        print(f'added route {pattern}')
