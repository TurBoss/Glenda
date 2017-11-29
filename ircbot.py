#! /usr/bin/env python

from io import StringIO

import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr


class IrcBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channels, nickname, server, password, client, rooms, rooms_id, bot_owner, port=6667, ):

        spec = irc.bot.ServerSpec(server, port=port, password=password)
        irc.bot.SingleServerIRCBot.__init__(self, [spec], nickname, nickname)

        self.bot_owner = bot_owner

        self.channel_list = channels

        self.client = client
        self.rooms = rooms
        self.rooms_id = rooms_id

        for name, room in self.rooms.items():
            self.rooms[name].add_listener(self.on_matrix_msg)

        self.client.start_listener_thread()

    def on_matrix_msg(self, room, event):

        if event['type'] == "m.room.message":
            if event['sender'] != "@TurBot:jauriarts.org":
                if event['content']['msgtype'] == "m.image":
                    for channel, room_id in self.rooms_id.items():
                       if event['room_id'] in room_id[1]:
                           url = "https://jauriarts.org:8448/_matrix/media/v1/download/jauriarts.org/"
                           mxc_url = event['content']['url']
                           pic_code = mxc_url[-24:]
                           pic_url = "{0}{1}".format(url, pic_code)
                           sender = event['sender'].split(":", 1)[0]
                           msg =  "<{0}> {1}".format(sender, pic_url)

                           self.connection.privmsg(channel, msg)

                if event['content']['msgtype'] == "m.text":
                    for channel, room_id in self.rooms_id.items():
                        if event['room_id'] in room_id[1]:
                            buf = StringIO(event['content']['body'])
                            for line in buf.read().splitlines():
                                self.connection.privmsg(channel,
                                    "<{0}> {1}".format(event['sender'].split(":", 1)[0],
                                                       line))

                if event['content']['msgtype'] == "m.emote":
                    for channel, room_id in self.rooms_id.items():
                        if event['room_id'] in room_id[1]:
                            self.connection.privmsg(channel,
                                                    "/me <{0}> {1}".format(event['sender'].split(":", 1)[0],
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

        self.rooms["{0}".format(e.target)].send_text("[{0}] {1}".format(source[0], msg))

        a = e.arguments[0].split(":", 1)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            self.do_command(e, a[1].strip())
        return

    def on_action(self, c, e):

        msg = e.arguments[0]
        source = e.source.split("!", 1)

        self.rooms["{0}".format(e.target)].send_text("* {0} {1}".format(source[0], msg))

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

        if cmd == "disconnect":
            if nick == self.bot_owner:
                self.disconnect()
            else:
                c.privmsg(nick, "you are not the bot owner")

        elif cmd == "die":
            if nick == self.bot_owner:
                self.die()
            else:
                c.privmsg(nick, "you are not the bot owner")

        elif cmd == "stats":
            for chname, chobj in self.channels.items():
                c.privmsg(nick, "--- Channel statistics ---")
                c.privmsg(nick, "Channel: {0}".format(chname))
                users = sorted(chobj.users())
                c.privmsg(nick, "Users: {0}".format(", ".join(users)))
                opers = sorted(chobj.opers())
                c.privmsg(nick, "Opers: {0}".format(", ".join(opers)))
                voiced = sorted(chobj.voiced())
                c.privmsg(nick, "Voiced: {0}".format(", ".join(voiced)))

        elif cmd == "dcc":
            dcc = self.dcc_listen()
            c.ctcp("DCC", nick, "CHAT chat {0} {1}".format(
                ip_quad_to_numstr(dcc.localaddress),
                dcc.localport))

        else:
            c.privmsg(nick, "Not understood: {0}".format(cmd))
