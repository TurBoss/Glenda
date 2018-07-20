from appservice_framework import AppService
from appservice_framework import database as db
from asyncspring.spring import connect

import asyncio
import yaml

loop = asyncio.get_event_loop()
loop.set_debug(True)

connections = {}


async def create_new_user(apps, client, spring_user):
    user_id = spring_user.username
    user = apps.get_user(serviceid=user_id)

    if not user:
        user = await apps.create_matrix_user(user_id,
                                             nick=user_id)
    return user


async def add_users_to_room(apps, client, conv, room):
    for user in conv.users:
        if not user.is_self:
            user = await create_new_user(apps, client, user)

            if not user in room.users:
                await apps.add_user_to_room(user.matrixid, room.matrixalias)


async def create_new_room(apps, client, auth_user, service_roomid):
    conv = client.get_conversation(service_roomid)

    # Set the conversation name
    convname = None

    if conv.name:
        convname = conv.name
    elif len(conv.users) == 2:
        for user in conv.users:
            if not user.is_self:
                convname = user.full_name

    room = await apps.create_linked_room(auth_user, service_roomid,
                                         matrix_roomname=convname)

    return room




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

        return conn, serviceid

    # Use a context manager to ensure clean shutdown.
    with apps.run() as run_forever:
        conn, serviceid = apps.get_connection(wait_for_connect=True)

        @conn.on("said")
        async def incoming_message(parsed, user, target, text):
            print("SAID!!!!!!!!!! {} {}".format(user.username, target))

            # matrix_user = await apps.create_matrix_user("{}".format(user.username))

            matrix_user1 = apps.get_user("@tole:springrts.com", user_type="auth")
            # matrix_user2 = apps.get_user("@turboss:springrts.com", user_type="auth")

            # print(matrix_user1)

            # assert isinstance(auth_user, db.AuthenticatedUser)

            # room = await apps.create_linked_room(matrix_user1,
            #                                     "test",
            #                                     matrix_roomid="#test:springrts.com",
            #                                     matrix_roomname="Test")

            # await apps.add_user_to_room(matrix_user1, "#test:springrts.com")

            #await apps.relay_service_message(matrix_user1, matrix_user1, text, None)

        run_forever()


if __name__ == "__main__":
    main()
