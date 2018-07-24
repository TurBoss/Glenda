#!/usr/bin/env python3

import sys
import logging
import asyncio
import yaml

from asyncspring import spring

from matrix_client.client import MatrixClient
from matrix_client.api import MatrixRequestError, MatrixHttpLibError
from requests.exceptions import MissingSchema

from urllib.parse import urlparse

loop = asyncio.get_event_loop()
# loop.set_debug(True)


FORMAT = "[%(asctime)s] [%(name)s] [%(levelname)s]  %(message)s (%(filename)s:%(lineno)d)"

logging.basicConfig(filename='glenda.log', level=logging.DEBUG, format=FORMAT)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class Glenda:
    def __init__(self, cfg):

        self.log = logging.getLogger(__name__)

        self.cfg = cfg

        self.matrix_rooms = {}
        self.lobby_rooms = {}
        self.matrix_client = None
        self.lobby_client = None

    # Called when a message is recieved from the matrix
    def on_room_message(self, room, event):
        if event['sender'] == "@{}:{}".format(self.cfg["matrix"]["username"], self.cfg["matrix"]["domain"]):
           # ignore messages sent by ourself
           return
        if event['type'] != "m.room.message":
           self.log.error("unknown event: %s" %(event))
           return
        if not event["room_id"] in self.matrix_rooms:
           self.log.error("Unknown room: %s vs %s" %(event, self.matrix_rooms))
           return

        lobby_room = self.matrix_rooms[event["room_id"]]
        if event['content']['msgtype'] == "m.text":
            user = self.matrix_client.get_user(event['sender'])
            user_display_name = user.get_display_name()
            self.lobby_client.say(lobby_room, "<{}> {}".format(user_display_name, event['content']['body']))
        elif event['content']['msgtype'] == "m.emote":
            user = self.matrix_client.get_user(event['sender'])
            user_display_name = user.get_display_name()
            self.lobby_client.say_ex(lobby_room, "<{}> {}".format(user_display_name, event['content']['body']))
        elif event['content']['msgtype'] == "m.image":
            user = self.matrix_client.get_user(event['sender'])
            user_display_name = user.get_display_name()
            mxc_url = event['content']['url']
            o = urlparse(mxc_url)
            domain = o.netloc
            pic_code = o.path
            url = "https://{0}/_matrix/media/v1/download/{0}{1}".format(domain, pic_code)
            msg = "<{}> {}".format(user_display_name, url)
            self.lobby_client.say_ex(lobby_room, "<{}> {}".format(user_display_name, msg))

    def setup_bridge(self, lobby_room, matrix_room):
        self.lobby_client.channels_to_join.append("#{}".format(lobby_room))
        try:
            response = self.matrix_client.join_room(matrix_room)
            response.add_listener(self.on_room_message)
            self.lobby_rooms[lobby_room] = response
            self.matrix_rooms[response.room_id] = lobby_room
        except MatrixRequestError as e:
            if e.code == 400:
                self.log.error("Room ID/Alias in the wrong format")
                sys.exit(11)
            else:
                self.log.error("Couldn't find  %s room." %(matrix_room))
                sys.exit(12)

    async def run(self):

        self.lobby_client = await spring.connect(self.cfg["lobby"]["host"], port=self.cfg["lobby"]["port"])

        self.matrix_client = MatrixClient(self.cfg["matrix"]["host"])

        try:
            self.matrix_client.login(self.cfg["matrix"]["username"], self.cfg["matrix"]["pwd"], sync=True)

        except MatrixRequestError as e:
            self.log.debug(e)
            if e.code == 403:
                self.log.error("Bad username or password.")
                sys.exit(4)
            else:
                self.log.error("Check your sever details are correct.")
                sys.exit(2)

        except MissingSchema as e:
            self.log.error("Bad URL format.")
            self.log.error(e)
            sys.exit(3)

        for lobby_room, matrix_room in self.cfg["rooms"].items():
            self.setup_bridge(lobby_room, matrix_room)

        self.lobby_client.login(self.cfg["lobby"]["username"], self.cfg["lobby"]["pwd"])

        try:
            self.matrix_client.login(self.cfg["matrix"]["username"], self.cfg["matrix"]["pwd"], sync=True)

        except MatrixRequestError as e:
            if e.code == 403:
                self.log.error("Bad username or password.")
                sys.exit(4)
            else:
                self.log.error("Check your sever details are correct.")
                sys.exit(2)

        except MissingSchema as e:
            self.log.error("Bad URL format.")
            self.log.error(e)
            sys.exit(3)

        self.matrix_client.start_listener_thread()


def main():

    with open("config.yaml", 'r') as yml_file:
        cfg = yaml.load(yml_file)

    glenda = Glenda(cfg)

    loop.run_until_complete(glenda.run())

    @glenda.lobby_client.on("said")
    def on_lobby_said(parsed, user, target, text):
        if user == cfg["lobby"]["username"]:
            return
        print(glenda.lobby_rooms)
        matrix_room = glenda.lobby_rooms[target]
        try:
            matrix_room.send_text("<{}> {}".format(user, text))
        except MatrixHttpLibError:
            matrix_room.send_text("<{}> {}".format(user, text))

    @glenda.lobby_client.on("saidex")
    def on_lobby_saidex(parsed, user, target, text):
        if user == cfg["lobby"]["username"]:
            return
        matrix_room = glenda.lobby_rooms[target]
        matrix_room.send_emote("<{}> {}".format(user, text))

    loop.run_forever()


if __name__ == "__main__":
    main()
