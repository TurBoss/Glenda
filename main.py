# -*- coding: future_fstrings -*-


# A simple chat client for matrix.
# This sample will allow you to connect to a room, and send/recieve messages.
# Args: host:port username password room
# Error Codes:
# 1 - Unknown problem has occured
# 2 - Could not find the server.
# 3 - Bad URL Format.
# 4 - Bad username/password.
# 11 - Wrong room format.
# 12 - Couldn't find room.
# 13 - IRC error

import sys
import logging
import yaml
import argparse

from matrix_client.client import MatrixClient
from matrix_client.api import MatrixRequestError
from requests.exceptions import MissingSchema

from ircbot import IrcBot

from daemon_python import DaemonPython

FORMAT = "[%(name)s][%(levelname)s]  %(message)s (%(filename)s:%(lineno)d)"

logging.basicConfig(filename='glenda.log', level=logging.DEBUG, format=FORMAT)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("irc.client").setLevel(logging.WARNING)


class GlendaDaemon(DaemonPython):

    def __init__(self, pid_file):
        super(DaemonPython, self).__init__()

        self.log = logging.getLogger(__name__)

        self.pid_file = pid_file

        with open("config.yaml", 'r') as yml_file:
            self.cfg = yaml.load(yml_file)

        # Matrix

        self.client = None

        self.rooms = {}

        self.bot_owner = self.cfg["bot_owner"]

        self.host = self.cfg["matrix"]["host"]
        self.domain = self.cfg["matrix"]["domain"]

        self.username = self.cfg["matrix"]["username"]
        self.password = self.cfg["matrix"]["password"]

        # IRC

        self.bot = None

        self.irc_server = self.cfg["irc"]["spring_server"]

        self.bot_nick = self.cfg["irc"]["bot_nick"]
        self.bot_password = self.cfg["irc"]["bot_password"]

        self.rooms_id = {}
        self.channels = []

    def run(self):

        self.log.info("Bridged rooms:")

        for channel, room in self.cfg["channels"].items():
            self.log.info(f"{channel} <-> {room[0]}")

            self.rooms_id[channel] = room
            self.channels.append(channel)

        self.client = MatrixClient(self.host)

        try:
            self.client.login_with_password(self.username, self.password)

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
            for k, v in self.rooms_id.items():
                self.rooms[k] = self.client.join_room(v[0])

        except MatrixRequestError as e:
            self.log.debug(e)
            if e.code == 400:
                self.log.debug("Room ID/Alias in the wrong format")
                sys.exit(11)
            else:
                self.log.debug("Couldn't find room.")
                sys.exit(12)

        self.bot = IrcBot(self.channels,
                          self.domain,
                          self.username,
                          self.bot_nick,
                          self.irc_server,
                          self.bot_password,
                          self.client,
                          self.rooms,
                          self.rooms_id,
                          self.bot_owner)

        try:
            self.bot.start()

        except Exception as e:
            self.log.debug(e)
            sys.exit(13)


def main():
    parser = argparse.ArgumentParser(description='Glenda Service.')

    parser.add_argument('operation',
                        metavar='OPERATION',
                        type=str,
                        help='Operation with daemon. Accepts any of these values: start, stop, restart, status',
                        choices=['start', 'stop', 'restart', 'status'])

    args = parser.parse_args()
    operation = args.operation

    pidfile = 'glenda.pid'

    daemon = GlendaDaemon(pidfile)

    if operation == 'start':
        logging.info("Glenda started")
        daemon.start()
    elif operation == 'restart':
        logging.info("Glenda restarted")
        daemon.restart()
    elif operation == 'stop':
        logging.info("Glenda stopped")
        daemon.stop()
    elif operation == 'status':
        logging.info("Not implemented yet(tm)")
        # daemon.stop()
    else:
        logging.info("Unknown command")
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
