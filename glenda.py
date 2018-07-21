#!/usr/bin/env python

import sys
import logging
import asyncio
import yaml

from asyncspring import spring

from matrix_client.client import MatrixClient
from matrix_client.api import MatrixRequestError
from requests.exceptions import MissingSchema

loop = asyncio.get_event_loop()
# loop.set_debug(True)


FORMAT = "[%(name)s][%(levelname)s]  %(message)s (%(filename)s:%(lineno)d)"

logging.basicConfig(filename='glenda.log', level=logging.DEBUG, format=FORMAT)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("irc.client").setLevel(logging.WARNING)


class Glenda:
    def __init__(self):

        self.log = logging.getLogger(__name__)

        with open("config.yaml", 'r') as yml_file:
            self.cfg = yaml.load(yml_file)

        self.rooms = []
        self.client_rooms = {}
        self.matrix_client = None
        self.lobby_client = None

    # Called when a message is recieved.
    def on_message(self, room, event):
        if event['type'] == "m.room.member":
            if event['membership'] == "join":
                print("{0} joined".format(event['content']['displayname']))
        elif event['type'] == "m.room.message":
            if event['content']['msgtype'] == "m.text":
                print("{0}: {1}".format(event['sender'], event['content']['body']))
        else:
            print(event['type'])

    @asyncio.coroutine
    async def run(self):

        self.lobby_client = await spring.connect(self.cfg["lobby"]["host"], port=self.cfg["lobby"]["port"])

        @self.lobby_client.on("said")
        async def incoming_message(parsed, user, target, text):
            self.lobby_client.say(target, "{}: you said {}".format(user.nick, text))

        @self.lobby_client.on("said-private")
        async def incoming_message(parsed, user, target, text):
            self.lobby_client.say(target, "{}: you said {}".format(user.nick, text))

        self.matrix_client = MatrixClient(self.cfg["matrix"]["host"])

        try:
            self.matrix_client.login(self.cfg["matrix"]["username"], self.cfg["matrix"]["pwd"], sync=True)

        except MatrixRequestError as e:
            self.log.debug(e)
            if e.code == 403:
                self.log.debug("Bad username or password.")
                sys.exit(4)
            else:
                self.log.debug("Check your sever details are correct.")
                sys.exit(2)

        except MissingSchema as e:
            self.log.debug("Bad URL format.")
            self.log.debug(e)
            sys.exit(3)

        for lobby_room, matrix_room in self.cfg["rooms"].items():
            self.rooms.append((lobby_room, matrix_room))

            self.lobby_client.channels_to_join.append(lobby_room)

            try:

                self.client_rooms[lobby_room] = self.matrix_client.join_room(matrix_room[0])
                self.client_rooms[lobby_room].add_listener(self.on_message)

            except MatrixRequestError as e:
                self.log.debug(e)
                if e.code == 400:
                    self.log.debug("Room ID/Alias in the wrong format")
                    sys.exit(11)
                else:
                    self.log.debug("Couldn't find room.")
                    sys.exit(12)

        self.lobby_client.login(self.cfg["lobby"]["username"], self.cfg["lobby"]["pwd"])

        try:
            self.matrix_client.login(self.cfg["matrix"]["username"], self.cfg["matrix"]["pwd"], sync=True)

        except MatrixRequestError as e:
            self.log.debug(e)
            if e.code == 403:
                self.log.debug("Bad username or password.")
                sys.exit(4)
            else:
                self.log.debug("Check your sever details are correct.")
                sys.exit(2)

        except MissingSchema as e:
            self.log.debug("Bad URL format.")
            self.log.debug(e)
            sys.exit(3)

        self.matrix_client.start_listener_thread()


def main():
    glenda = Glenda()

    loop.run_until_complete(glenda.run())
    loop.run_forever()


if __name__ == "__main__":
    main()
