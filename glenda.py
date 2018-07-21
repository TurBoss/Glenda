#!/usr/bin/env python

import sys
import logging
import asyncio
import yaml

from asyncspring.spring import connect


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
        self.client = None

    async def run(self):

        self.log.info("Bridged rooms:")

        for lobby_room, matrix_room in self.cfg["rooms"].items():
            self.log.info("{} <-> {}".format(lobby_room, matrix_room[0]))

            self.rooms.append((lobby_room, matrix_room))

        self.client = MatrixClient(self.cfg["matrix"]["host"])

        try:
            self.client.login(self.cfg["matrix"]["username"], self.cfg["matrix"]["pwd"], sync=True)

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

        try:
            for room in self.rooms:
                print(room)
                self.client_rooms[room[0]] = self.client.join_room(room[1][0])

        except MatrixRequestError as e:
            self.log.debug(e)
            if e.code == 400:
                self.log.debug("Room ID/Alias in the wrong format")
                sys.exit(11)
            else:
                self.log.debug("Couldn't find room.")
                sys.exit(12)

        conn = await connect(self.cfg["lobby"]["host"], port=self.cfg["lobby"]["port"])
        conn.login(self.cfg["lobby"]["username"], self.cfg["lobby"]["pwd"])

def main():

    glenda = Glenda()

    loop.run_until_complete(glenda.run())
    loop.run_forever()


if __name__ == "__main__":
    main()
