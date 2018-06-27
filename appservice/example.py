from appservice_framework import AppService
from asyncspring.spring import connect

import asyncio
import yaml

loop = asyncio.get_event_loop()
loop.set_debug(True)

connections = {}


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
        print("connect {} to springlobby".format(serviceid))

        conn = await connect(cfg["lobby"]["host"], port=cfg["lobby"]["port"])
        conn.login(serviceid, auth_token)

        @conn.on("public-message")
        def incoming_message(message, user, channel):
            print("test")
            # conn.say(channel, "Hi {}! You're connecting from {}.".format(user.nick, user.host))

        return conn, serviceid

    """
    @apps.service_join_room
    async def send_message(apps, auth_user, room, content):
        conn = await apps.service_connections[auth_user]

        conn.send('PRIVMSG', target=room.serviceid, message=content['body'])
    """

    # user1 = apps.add_authenticated_user("@tole:springrts.com", "pladur", serviceid="tole")

    # Use a context manager to ensure clean shutdown.
    with apps.run() as run_forever:
        conn, serviceid = apps.get_connection(wait_for_connect=True)

        @conn.on("private")
        def incoming_message(parsed, user, target, text):

            matrix_user = apps.create_matrix_user(user)
            apps.add_user_to_room(matrix_user, f"#test:localhost")
            apps.relay_service_message(user, target, text, None)

        run_forever()


if __name__ == "__main__":
    main()
