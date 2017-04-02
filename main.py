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

from matrix_client.client import MatrixClient
from matrix_client.api import MatrixRequestError
from requests.exceptions import MissingSchema

from ircbot import IrcBot


def main():

    with open("config.yaml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    # Matrix

    rooms = {}

    bot_owner = cfg["bot_owner"]

    host = cfg["matrix"]["host"]

    username = cfg["matrix"]["username"]
    password = cfg["matrix"]["password"]

    # IRC

    irc_server = cfg["irc"]["spring_server"]

    bot_nick = cfg["irc"]["bot_nick"]
    bot_password = cfg["irc"]["bot_password"]

    rooms_alias = []
    rooms_id = {}
    channels = []

    print("Bridged rooms:")

    for channel, room in cfg["channels"].items():
        print("{0} <-> {1}".format(channel, room[0]))
        rooms_alias.append(room[0])

        rooms_id[channel] = room[1]

        channels.append(channel)

    client = MatrixClient(host)

    try:
        client.login_with_password(username, password)
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
        for name in rooms_alias:
            rooms[name] = client.join_room(name)
    except MatrixRequestError as e:
        print(e)
        if e.code == 400:
            print("Room ID/Alias in the wrong format")
            sys.exit(11)
        else:
            print("Couldn't find room.")
            sys.exit(12)

    bot = IrcBot(channels, bot_nick, irc_server, bot_password, client, rooms, rooms_id, bot_owner)
    bot.start()

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)

    main()
