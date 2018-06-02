from appservice_framework import AppService

from asyncspring import spring

from Crypto.Hash import MD5
from Crypto.Hash import SHA256

import base64
import asyncio

import yaml

loop = asyncio.get_event_loop()
loop.set_debug(True)

test_room = "#test"


def main():

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
        conn = await spring.connect(loop, "lobby.springrts.com", port=8200)


        passwd = base64.b64encode(MD5.new("pladur13lol".encode("utf-8")).digest()).decode("utf-8")
        user = "bot"

        conn.login(user, passwd)
        """
        @conn.on("login-complete")
        def join_defaults(lobby):
            conn.join("#moddev")
            conn.join("#sy")
            conn.join("#bots")
        """
        return conn, serviceid

    # user1 = apps.add_authenticated_user("@turboss:springrts.com", "MDAxYmxvY2F0aW9uIHNwcmluZ3J0cy5jb20KMDAxM2lkZW50aWZpZXIga2V5CjAwMTBjaWQgZ2VuID0gMQowMDI5Y2lkIHVzZXJfaWQgPSBAdHVyYm9zczpzcHJpbmdydHMuY29tCjAwMTZjaWQgdHlwZSA9IGFjY2VzcwowMDIxY2lkIG5vbmNlID0gWWRFM2d3Iy4wZlAwNkR0VAowMDJmc2lnbmF0dXJlIH6nLVH6iM95hv_zfvdU-i_Z3F819BR9j9hOWKXm0ObJCg", serviceid="matrix")

    # Use a context manager to ensure clean shutdown.
    with apps.run() as run_forever:
        run_forever()


if __name__ == "__main__":
    main()
