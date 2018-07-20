from asyncblink import signal
from asyncspring.parser import LobbyMessage
from collections import defaultdict


class Registry:
    def __init__(self):
        self.mappings = set()
        # mappings contains two-tuples (user, channel)
        self.users = {}
        self.channels = {}


registries = {}


def create_registry(client):
    registries[client.netid] = Registry()
    client.tracking_registry = registries[client.netid]


signal("netid-available").connect(create_registry)


class User:
    def __init__(self, nick, user, host, netid=None):
        self.nick = nick
        self.user = user
        self.host = host
        self.account = None
        self.netid = netid
        self.previous_nicks = []

    def hostmask(self):
        return "{}!{}@{}".format(self.nick, self.user, self.host)

    def _get_channels(self):
        return list(map(lambda x: x[1], filter(lambda x: x[0] == self.nick, registries[self.netid].mappings)))

    def __repr__(self):
        return "User {}!{}@{}".format(self.nick, self.user, self.host)

    channels = property(_get_channels)


class Channel:
    def __init__(self, channel, netid=None):
        self.channel = channel
        self.available = False
        self.mode = ""
        self.topic = ""
        self.netid = netid
        self.state = set()
        self.flags = defaultdict(set)

    def _get_users(self):
        return list(map(lambda x: x[0], filter(lambda x: x[1] == self.channel, registries[self.netid].mappings)))

    def __repr__(self):
        return "Channel {}".format(self.channel)

    users = property(_get_users)


## utility functions

def parse_prefixes(server):  # -> {'v': '+', ...}
    keys, values = server.server_supports['PREFIX'][1:].split(")")
    return {keys[i]: values[i] for i in range(len(keys))}


def parse_hostmask(hostmask):
    if "!" in hostmask and "@" in hostmask:
        nick, userhost = hostmask.split("!", maxsplit=1)
        user, host = userhost.split("@", maxsplit=1)
        return nick, user, host
    return hostmask, None, None


def get_user(netid_or_message, hostmask=None):
    if isinstance(netid_or_message, LobbyMessage):
        netid = netid_or_message.client.netid
        if hostmask is None:
            hostmask = netid_or_message.source
    else:
        netid = netid_or_message

    if hostmask is None:
        raise Exception("hostmask passed as none, but no message was passed")

    registry = registries[netid]
    nick, user, host = parse_hostmask(hostmask)
    if nick in registry.users:
        if user is not None and host is not None:
            registry.users[nick].user = user
            registry.users[nick].host = host
        return registry.users[nick]

    if user is not None and host is not None:
        registry.users[nick] = User(nick, user, host, netid)
        return registry.users[nick]

    if "." in nick:  # it's probably a server
        return User(nick, nick, nick, netid)

    # We don't know about this user yet, so return a dummy.
    # This will be updated when get_user is called again with the same nick
    # and a full hostmask. This should be really rare.
    # FIXME it would probably be a good idea to /whois here
    registry.users[nick] = User(nick, None, None, netid)
    return registry.users[nick]


def get_channel(netid_or_message, x):
    if isinstance(netid_or_message, LobbyMessage):
        netid = netid_or_message.client.netid
    else:
        netid = netid_or_message

    registry = registries[netid]
    if x not in registry.channels:
        registry.channels[x] = Channel(x, netid)
    return registry.channels[x]


# signal definitions

join = signal("join")
extjoin = signal("irc-join")
account = signal("irc-account")
part = signal("part")
quit_ = signal("quit")
kick = signal("kick")
nick = signal("nick")
topic = signal("irc-332")
topic_changed = signal("irc-topic")
extwho_response = signal("irc-354")
who_response = signal("irc-352")
who_done = signal("irc-315")
channel_mode = signal("irc-324")
names_response = signal("irc-353")
names_done = signal("irc-366")
mode_set = signal("+mode")
mode_unset = signal("-mode")


def sync_channel(client, channel):
    if client.server_supports["WHOX"]:
        client.writeln("WHO {} %cnuha".format(channel))
    else:
        client.writeln("WHO {}".format(channel))
    client.writeln("MODE {}".format(channel))


sync_complete_set = {"mode", "who", "names"}


def check_sync_done(message, channel):
    if get_channel(message, channel).state == sync_complete_set:
        signal("sync-done").send(message, channel=channel)


## event handlers

@topic.connect
def handle_topic_set(message):
    channel, topic = message.params[1:]
    get_channel(message, channel).topic = topic


@topic_changed.connect
def handle_topic_changed(message):
    channel, topic = message.params
    get_channel(message, channel).topic = topic
    signal("topic-changed").send(message, user=get_user(message), channel=channel, topic=topic)


@extwho_response.connect
def handle_extwho_response(message):
    channel, ident, host, nick, account = message.params[1:]
    user = get_user(message, "{}!{}@{}".format(nick, ident, host))
    user.account = account if account != "0" else None
    handle_join(message, user, channel, real=False)


@who_response.connect
def handle_who_response(message):
    channel, ident, host, server, nick, state, realname = message.params[1:]
    user = get_user(message, "{}!{}@{}".format(nick, ident, host))
    handle_join(message, user, channel, real=False)


@names_response.connect
def handle_names_response(message):
    dummy, channel, names = message.params[1:]
    prefixes = parse_prefixes(message.client)
    for name in names.split():
        name_list = list(name)
        applicable_prefixes = []

        while name_list[0] in prefixes.values():  # multi-prefix support
            applicable_prefixes.append(name_list.pop(0))

        for prefix in applicable_prefixes:
            get_channel(message, channel).flags[prefix].add("".join(name_list))


@names_done.connect
def handle_names_done(message):
    channel, dummy = message.params[1:]
    channel_obj = get_channel(message, channel)
    channel_obj.state = channel_obj.state | {"names"}
    check_sync_done(message, channel)


@channel_mode.connect
def handle_received_mode(message):
    channel, mode = message.params[1], message.params[2]
    channel_obj = get_channel(message, channel)
    channel_obj.mode = mode
    channel_obj.state = channel_obj.state | {"mode"}
    check_sync_done(message, channel)


@who_done.connect
def handle_who_done(message):
    channel = message.params[1]
    channel_obj = get_channel(message, channel)
    channel_obj.state = channel_obj.state | {"who"}
    check_sync_done(message, channel)


@join.connect
def handle_join(message, user, channel, real=True):
    get_channel(message, channel)

    if user.nick == message.client.nickname and real:
        sync_channel(message.client, channel)
        get_channel(message, channel).available = True
    message.client.tracking_registry.mappings.add((user.nick, channel))


@extjoin.connect
def handle_extjoin(message):
    if "extended-join" not in message.client.caps:
        return
    account = message.params[1]
    get_user(message).account = account if account != "*" else None


@account.connect
def account_notify(message):
    account = message.params[0]
    get_user(message).account = account if account != "*" else None


@part.connect
def handle_part(message, user, channel, reason):
    user = get_user(message, user.nick)
    if user == message.client.nickname:
        get_channel(message, channel).available = False
    message.client.tracking_registry.mappings.discard((user.nick, channel))


@quit_.connect
def handle_quit(message, user, reason):
    user = get_user(message, user.nick)
    del message.client.tracking_registry.users[user.nick]
    for channel in set(user.channels):
        message.client.tracking_registry.mappings.remove((user.nick, channel))


@kick.connect
def handle_kick(message, kicker, kickee, channel, reason):
    message.client.tracking_registry.mappings.discard((kickee, channel))


@nick.connect
def handle_nick(message, user, new_nick):
    user = get_user(message)
    old_nick = user.nick
    user.previous_nicks.append(old_nick)
    user.nick = new_nick
    del message.client.tracking_registry.users[old_nick]
    message.client.tracking_registry.users[new_nick] = user

    mappings = set(message.client.tracking_registry.mappings)
    original_mappings = message.client.tracking_registry.mappings
    for i in mappings:
        if i[0] == old_nick:
            original_mappings.discard(i)
            original_mappings.add((new_nick, i[1]))


@mode_set.connect
def handle_mode_set(message, mode, arg, user, channel):
    prefixes = parse_prefixes(message.client)
    if mode in prefixes:
        get_channel(message, channel).flags[prefixes[mode]].add(arg)


@mode_unset.connect
def handle_mode_unset(message, mode, arg, user, channel):
    prefixes = parse_prefixes(message.client)
    if mode in prefixes:
        get_channel(message, channel).flags[prefixes[mode]].discard(arg)


signal("plugin-registered").send("asyncspring.plugins.tracking")
