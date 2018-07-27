import sys

import asyncio
import collections
import importlib
import logging
import random
import ssl

from asyncblink import signal

loop = asyncio.get_event_loop()

connections = {}

plugins = []

log = logging.getLogger(__name__)


def plugin_registered_handler(plugin_name):
    plugins.append(plugin_name)


signal("plugin-registered").connect(plugin_registered_handler)


def load_plugins(*plugins):
    for plugin in plugins:
        if plugin not in plugins:
            importlib.import_module(plugin)


class User:
    """
    Represents a user on SpringRTS Lobby, with their nickname, username, and hostname.
    """

    def __init__(self, username, password, email):
        self.username = username
        self.password = password
        self.email = email
        # self.hostmask = "{}!{}@{}".format(nick, user, host)
        self._register_wait = 0

    @classmethod
    def from_hostmask(self, hostmask):
        if "!" in hostmask and "@" in hostmask:
            nick, userhost = hostmask.split("!", maxsplit=1)
            user, host = userhost.split("@", maxsplit=1)
            return self(nick, user, host)
        return self(None, None, hostmask)


class LobbyProtocolWrapper:
    """
    Wraps an LobbyProtocol object to allow for automatic reconnection. Only used
    internally.
    """

    def __init__(self, protocol):
        self.protocol = protocol

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        return getattr(self.protocol, attr)

    def __attr__(self, attr, val):
        if attr == "protocol":
            self.protocol = val
        else:
            setattr(self.protocol, attr, val)


class LobbyProtocol(asyncio.Protocol):
    """
    Represents a connection to SpringRTS Lobby.
    """

    def connection_made(self, transport):

        self.work = True
        self.transport = transport
        self.wrapper = None
        self.logger = logging.getLogger("asyncspring.LobbyProtocol")
        self.last_ping = float('inf')
        self.last_pong = 0
        self.lag = 0
        self.buf = ""
        self.old_nickname = None
        self.nickname = ""
        self.server_supports = collections.defaultdict(lambda *_: None)
        self.queue = []
        self.queue_timer = 1.5
        self.caps = set()
        self.registration_complete = False
        self.channels_to_join = []
        self.autoreconnect = True

        signal("connected").send(self)
        self.logger.info("Connection success.")

        self.process_queue()

    def data_received(self, data):
        if not self.work:
            return
        data = data.decode()

        self.buf += data
        while "\n" in self.buf:
            index = self.buf.index("\n")
            line_received = self.buf[:index].strip()
            self.buf = self.buf[index + 1:]
            # print(line_received)
            signal("raw").send(self, text=line_received)

    def connection_lost(self, exc):
        if not self.work:
            return
        self.logger.critical("Connection lost.")
        signal("connection-lost").send(self.wrapper)

    # Core helper functions

    def process_queue(self):
        """
        Pull data from the pending messages queue and send it. Schedule ourself
        to be executed again later.
        """

        if not self.work:
            return
        if self.queue:
            self._writeln(self.queue.pop(0))

        loop.call_later(self.queue_timer, self.process_queue)

    def on(self, event):

        def process(f):
            """
            Register an event with Blinker. Convenience function.
            """
            self.logger.info("Registering function for event {}".format(event))
            signal(event).connect(f)
            return f

        return process

    def _writeln(self, line):
        """
        Send a raw message to SpringRTS Lobby immediately.
        """
        if not isinstance(line, bytes):
            line = line.encode("utf-8")
        # print("SENT:\t\t{}".format(line))
        self.transport.write(line + b"\r\n")
        signal("lobby-send").send(line.decode())

    def writeln(self, line):
        """
        Queue a message for sending to the currently connected SpringRTS Lobby server.
        """
        self.queue.append(line)
        return self

    def register(self, username, password, email=None):
        """
        Queue registration with the server. This includes sending nickname,
        ident, realname, and password (if required by the server).
        """

        self.username = username
        self.password = password
        self.email = email

        return self

    def _register(self):
        """
        Send registration messages to SpringLobby Server.
        """
        if self.email:
            self.writeln("REGISTER {} {} {}".format(self.username, self.password, self.email))
        else:
            self.writeln("REGISTER {} {}".format(self.username, self.password))

        self.logger.info("Sent registration information")
        signal("registration-complete").send(self)
        self.nickname = self.username

    # protocol abstractions

    def login(self, username, password):
        """
        Queue registration with the server. This includes sending nickname,
        ident, realname, and password (if required by the server).
        """
        self.username = username
        self.password = password

        return self

    def _login(self):
        """
        Send Login message to SpringLobby Server.
        """
        self.writeln("LOGIN {} {} 3200 * TurBoMatrix 0.1".format(self.username, self.password))
        signal("login-complete").send(self)

    def join(self, channel):
        """
        Join a channel.
        """
        self.writeln("JOIN {}".format(channel))

        return self

    def leave(self, channel):
        """
        Leave a channel.
        """

        self.writeln("LEAVE {}".format(channel))

    def say(self, channel, message):
        """
        Send a MSG to SpringRTS Lobby room.
        Carriage returns and line feeds are stripped to prevent bugs.
        """

        message = message.replace("\n", "").replace("\r", "")

        while message:
            self.writeln("SAY {} {}".format(channel, message[:400]))
            message = message[400:]

    def say_ex(self, channel, message):
        """
        Send a MSG to SpringRTS Lobby room using emote.
        Carriage returns and line feeds are stripped to prevent bugs.
        """

        message = message.replace("\n", "").replace("\r", "")

        while message:
            self.writeln("SAYEX {} {}".format(channel, message[:400]))
            message = message[400:]

    def say_private(self, username, message):
        """
        Send a private message to SpringRTS Lobby user.
        Carriage returns and line feeds are stripped to prevent bugs.
        """

        message = message.replace("\n", "").replace("\r", "")

        while message:
            self.writeln("SAYPRIVATE {} :{}".format(username, message[:400]))
            message = message[400:]

    def say_private_ex(self, username, message):
        """
        Send a private message to SpringRTS Lobby user in emote.
        Carriage returns and line feeds are stripped to prevent bugs.
        """

        message = message.replace("\n", "").replace("\r", "")

        while message:
            self.writeln("SAYPRIVATEEX {} :{}".format(username, message[:400]))
            message = message[400:]

    def nick_in_use_handler(self):
        """
        Choose a nickname to use if the requested one is already in use.
        """

        s = "a{}".format("".join([random.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") for i in range(8)]))
        return s

        # catch-all

        # def __getattr__(self, attr):
        #     if attr in self.__dict__:
        #         return self.__dict__[attr]

        #     def _send_command(self, *args):
        #         argstr = " ".join(args[:-1]) + " :{}".format(args[-1])
        #         self.writeln("{} {}".format(attr.upper(), argstr))

        #     _send_command.__name__ == attr
        #     return _send_command


def get_user(hostmask):
    if "!" not in hostmask or "@" not in hostmask:
        return User(hostmask, hostmask, hostmask)
    return User.from_hostmask(hostmask)


async def connect(server, port=8200, use_ssl=False):
    """
    Connect to an SpringRTS Lobby server. Returns a proxy to an LobbyProtocol object.
    """

    transport, protocol = await loop.create_connection(LobbyProtocol, host=server, port=port, ssl=use_ssl)

    protocol.wrapper = LobbyProtocolWrapper(protocol)
    protocol.server_info = {"host": server, "port": port, "ssl": use_ssl}
    protocol.netid = "{}:{}:{}{}".format(id(protocol), server, port, "+" if use_ssl else "-")

    signal("netid-available").send(protocol)

    connections[protocol.netid] = protocol.wrapper

    return protocol.wrapper


def disconnected(client_wrapper):
    """
    Either reconnect the LobbyProtocol object, or exit, depending on
    configuration. Called by LobbyProtocol when we lose the connection.
    """

    client_wrapper.protocol.work = False
    log.info("Disconnected from {}. Attempting to reconnect...".format(client_wrapper.netid))
    signal("disconnected").send(client_wrapper.protocol)
    if not client_wrapper.protocol.autoreconnect:
        sys.exit(2)

    connector = loop.create_connection(LobbyProtocol, **client_wrapper.server_info)

    def reconnected(f):
        """
        Callback function for a successful reconnection.
        """

        log.info("Reconnected! {}".format(client_wrapper.netid))
        transport, protocol = f.result()
        protocol.login(client_wrapper.username, client_wrapper.password)
        protocol.channels_to_join = client_wrapper.channels_to_join
        protocol.server_info = client_wrapper.server_info
        protocol.netid = client_wrapper.netid
        protocol.wrapper = client_wrapper
        signal("netid-available").send(protocol)
        client_wrapper.protocol = protocol

    asyncio.async(connector).add_done_callback(reconnected)


signal("connection-lost").connect(disconnected)

import asyncspring.plugins.core
