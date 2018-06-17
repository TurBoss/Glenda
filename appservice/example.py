from appservice_framework import AppService

from asyncspring.spring import connect

from Crypto.Hash import MD5
from Crypto.Hash import SHA256

import base64
import asyncio

from blinker import signal


import yaml

loop = asyncio.get_event_loop()
loop.set_debug(True)


connections = {}

# test_room = "#test"


def main():

    print("open config.")
    with open("config.yaml", 'r') as yml_file:
        cfg = yaml.load(yml_file)

    apps = AppService(matrix_server=cfg["matrix"]["host"],
                      server_domain=cfg["matrix"]["domain"],
                      access_token=cfg["matrix"]["token"],
                      user_namespace=cfg["matrix"]["user_namespace"],
                      sender_localpart=cfg["matrix"]["sender_localpart"],
                      room_namespace=cfg["matrix"]["room_namespace"],
                      database_url=cfg["matrix"]["database_url"],
                      loop=loop)

    @apps.service_connect
    async def connect_spring(apps, serviceid, auth_token):
        print("connect to springlobby")

        conn = connect(cfg["lobby"]["host"], port=cfg["lobby"]["port"])

        """
        passwd_hash = base64.b64encode(MD5.new("".encode("utf-8")).digest()).decode("utf-8")
        user = "bot"

        conn.login(user, passwd_hash)
        """
        """
        @conn.on("login-complete")
        def join_defaults(lobby):
            conn.join("#moddev")
            conn.join("#sy")
            conn.join("#bots")
        """
        return conn, serviceid

    # user1 = apps.add_authenticated_user("@turboss:springrts.com", "", serviceid="matrix")

    # Use a context manager to ensure clean shutdown.
    with apps.run() as run_forever:
        print("run forever")
        run_forever()


if __name__ == "__main__":
    main()
