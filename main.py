#!/usr/bin/env python3

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

import sys
import logging
import yaml
import argparse

from matrix_client.client import MatrixClient
from matrix_client.api import MatrixRequestError
from requests.exceptions import MissingSchema

from ircbot import IrcBot

from daemon_python import DaemonPython


class Glendaemon(DaemonPython):

    def __init__(self, pid_file):
        super(DaemonPython, self).__init__()

        self.pid_file = pid_file

        with open("config.yaml", 'r') as yml_file:
            self.cfg = yaml.load(yml_file)

        # Matrix

        self.rooms = {}

        self.bot_owner = self.cfg["bot_owner"]

        self.host = self.cfg["matrix"]["host"]
        self.domain = self.cfg["matrix"]["domain"]

        self.username = self.cfg["matrix"]["username"]
        self.password = self.cfg["matrix"]["password"]

        # IRC

        self.irc_server = self.cfg["irc"]["spring_server"]

        self.bot_nick = self.cfg["irc"]["bot_nick"]
        self.bot_password = self.cfg["irc"]["bot_password"]

        self.rooms_id = {}
        self.channels = []

        self.client = MatrixClient(self.host)

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

    def run(self):

        print("Bridged rooms:")

        for channel, room in self.cfg["channels"].items():
            print("{0} <-> {1}".format(channel, room[0]))

            self.rooms_id[channel] = room

            self.channels.append(channel)

        try:
            self.client.login_with_password(self.username, self.password)
        except MatrixRequestError as e:
            print(e)
            if e.code == 403:
                print("Bad username or password.")
                sys.exit(4)
            else:
                print("Check your sever details are correct.")
                sys.exit(2)
        except MissingSchema as e:
            print("Bad URL format.")
            print(e)
            sys.exit(3)

        try:
            for k, v in self.rooms_id.items():
                self.rooms[k] = self.client.join_room(v[0])
        except MatrixRequestError as e:
            print(e)
            if e.code == 400:
                print("Room ID/Alias in the wrong format")
                sys.exit(11)
            else:
                print("Couldn't find room.")
                sys.exit(12)

        self.bot.start()


def main():

    parser = argparse.ArgumentParser(description='Glenda Service.')

    parser.add_argument('operation',
                        metavar='OPERATION',
                        type=str,
                        help='Operation with daemon. Accepts any of these values: start, stop, restart, status',
                        choices=['start', 'stop', 'restart', 'status'])

    args = parser.parse_args()
    operation = args.operation

    pidfile = '/var/run/mydaemon.pid'
    daemon = Glendaemon(pidfile)

    if operation:
        if operation == 'start':
            daemon.start()
        if operation == 'restart':
            daemon.restart()
        if operation == 'stop':
            daemon.stop()
        else:
            print("Unknown command")
            sys.exit(2)

        sys.exit(0)


if __name__ == "__main__":
    main()
