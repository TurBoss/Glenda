#! /usr/bin/env python
#
# Example program using irc.bot.
#
# Joel Rosdahl <joel@rosdahl.net>

"""A simple example bot.

This is an example bot that uses the SingleServerIRCBot class from
irc.bot.  The bot enters a channel and listens for commands in
private messages and channel traffic.  Commands in channel messages
are given by prefixing the text by the bot name followed by a colon.
It also responds to DCC CHAT invitations and echos data sent in such
sessions.

The known commands are:

    stats -- Prints some channel information.

    disconnect -- Disconnect the bot.  The bot will try to reconnect
                  after 60 seconds.

    die -- Let the bot cease to exist.

    dcc -- Let the bot invite you to a DCC CHAT connection.
"""

import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr


class IrcBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channels, nickname, server, password, client, rooms, rooms_id, port=6667, ):

        spec = irc.bot.ServerSpec(server, port=port, password=password)
        irc.bot.SingleServerIRCBot.__init__(self, [spec], nickname, nickname)

        self.channel_list = channels

        self.client = client
        self.rooms = rooms
        self.rooms_id = rooms_id

        for name, room in self.rooms.items():
            self.rooms[name].add_listener(self.on_matrix_msg)

        self.client.start_listener_thread()

    def on_matrix_msg(self, room, event):

        if event['type'] == "m.room.message":
            if event['content']['msgtype'] == "m.text":
                if event['sender'] != "@TurBot:jauriarts.org":
                    for channel, room_id in self.rooms_id.items():
                        if event['room_id'] in room_id:
                            self.connection.privmsg(channel,
                                                    "<{0}> {1}".format(event['sender'].split(":", 1)[0],
                                                                       event['content']['body']))
        else:
            print(event['type'])

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        for channel in self.channel_list:
            c.join(channel)

    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments[0])

    def on_pubmsg(self, c, e):

        msg = e.arguments[0]
        source = e.source.split("!", 1)

        if e.target == "#sy":
            self.rooms["#spring-rts:jauriarts.org"].send_text("[{0}] {1}".format(source[0], msg))
        else:
            self.rooms["{0}:jauriarts.org".format(e.target)].send_text("[{0}] {1}".format(source[0], msg))

        a = e.arguments[0].split(":", 1)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            self.do_command(e, a[1].strip())
        return

    def on_dccmsg(self, c, e):
        # non-chat DCC messages are raw bytes; decode as text
        text = e.arguments[0].decode('utf-8')
        c.privmsg("You said: " + text)

    def on_dccchat(self, c, e):
        if len(e.arguments) != 2:
            return
        args = e.arguments[1].split()
        if len(args) == 4:
            try:
                address = ip_numstr_to_quad(args[2])
                port = int(args[3])
            except ValueError:
                return
            self.dcc_connect(address, port)

    def do_command(self, e, cmd):
        nick = e.source.nick
        c = self.connection

        if nick != "TurBoss":
            return

        if cmd == "disconnect":
            self.disconnect()
        elif cmd == "die":
            self.die()
        elif cmd == "stats":
            for chname, chobj in self.channels.items():
                c.notice(nick, "--- Channel statistics ---")
                c.notice(nick, "Channel: " + chname)
                users = sorted(chobj.users())
                c.notice(nick, "Users: " + ", ".join(users))
                opers = sorted(chobj.opers())
                c.notice(nick, "Opers: " + ", ".join(opers))
                voiced = sorted(chobj.voiced())
                c.notice(nick, "Voiced: " + ", ".join(voiced))
        elif cmd == "dcc":
            dcc = self.dcc_listen()
            c.ctcp("DCC", nick, "CHAT chat %s %d" % (
                ip_quad_to_numstr(dcc.localaddress),
                dcc.localport))
        else:
            c.notice(nick, "Not understood: " + cmd)
