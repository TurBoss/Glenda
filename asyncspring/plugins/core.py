from asyncblink import signal
from asyncspring.spring import get_user
from asyncspring.parser import LobbyMessage

import asyncio
import time

ping_clients = []


def _pong(message):
    message.client.writeln(f"PONG {message.params[0]}")


def _redispatch_message_common(message, mtype):
    target, text = message.params[0], message.params[1]
    user = get_user(message.source) if message.source else ''
    signal(mtype).send(message, user=user, target=target, text=text)
    """
    if target == message.client.nickname:
        signal("private-{}".format(mtype)).send(message, user=user, target=target, text=text)
    else:
        signal("public-{}".format(mtype)).send(message, user=user, target=target, text=text)
    """

def _redispatch_said(message):
    _redispatch_message_common(message, "said")


def _redispatch_saidex(message):
    _redispatch_message_common(message, "saidex")


def _redispatch_saidprivate(message):
    _redispatch_message_common(message, "said")


def _redispatch_saidprivateex(message):
    _redispatch_message_common(message, "saidex")


def _redispatch_notice(message):
    _redispatch_message_common(message, "notice")


def _redispatch_joined(message):
    signal("join").send(message, user=get_user(message.source), channel=message.params[0])


def _redispatch_left(message):
    user = get_user(message.source)
    channel, reason = message.params[0], None
    if len(message.params) > 1:
        reason = message.params[1]
    signal("part").send(message, user=user, channel=channel, reason=reason)


def _redispatch_quit(message):
    signal("quit").send(message, user=get_user(message.source), reason=message.params[0])


def _redispatch_kick(message):
    kicker = get_user(message.source)
    channel, kickee, reason = message.params[0], get_user(message.params[1]), message.params[2]
    signal("kick").send(message, kicker=kicker, kickee=kickee, channel=channel, reason=reason)


def _redispatch_nick(message):
    old_user = get_user(message.source)
    new_nick = message.params[0]
    if old_user.nick == message.client.nickname:
        message.client.nickname = new_nick
    signal("nick").send(message, user=old_user, new_nick=new_nick)


def _parse_mode(message):
    # :ChanServ!ChanServ@services. MODE ##fwilson +o fwilson
    if "CHANMODES" in message.client.server_supports:
        argument_modes = "".join(message.client.server_supports["CHANMODES"].split(",")[:-1])
        argument_modes += message.client.server_supports["PREFIX"].split(")")[0][1:]
    else:
        argument_modes = "beIqaohvlk"
    print("argument_modes are", argument_modes)
    user = get_user(message.source)
    channel = message.params[0]
    modes = message.params[1]
    args = message.params[2:]
    flag = "+"
    for mode in modes:
        if mode in "+-":
            flag = mode
            continue
        if mode in argument_modes:
            arg = args.pop(0)
        else:
            arg = None
        signal("{}mode".format(flag)).send(message, mode=mode, arg=arg, user=user, channel=channel)
        signal("mode {}{}".format(flag, mode)).send(message, arg=arg, user=user, channel=channel)


def _server_supports(message):
    supports = message.params[1:-1]  # No need for "Are supported by this server" or bot's nickname
    print("Server supports {}".format(supports))
    for feature in supports:
        if "=" in feature:
            k, v = feature.split("=")
            message.client.server_supports[k] = v
        else:
            message.client.server_supports[feature] = True


def _nick_in_use(message):
    message.client.old_nickname = message.client.nickname
    s = message.client.nick_in_use_handler()

    def callback():
        message.client.nickname = s
        message.client.writeln("NICK {}".format(s))

    # loop.call_later(5, callback)


def _ping_servers():
    for client in ping_clients:
        if client.last_pong != 0 and time.time() - client.last_pong > 90:
            client.connection_lost(Exception())
        client.writeln("PING")
        client.last_ping = time.time()
    asyncio.get_event_loop().call_later(29, _ping_servers)


def _catch_pong(message):
    message.client.last_pong = time.time()
    message.client.lag = message.client.last_pong - message.client.last_ping


def _redispatch_spring(message):
    signal(f"spring-{message.verb.lower()}").send(message)


def _redispatch_raw(client, text):
    message = LobbyMessage.from_message(text)
    message.client = client
    signal("spring").send(message)


def _register_client(client):
    print("Sending real registration message")
    asyncio.get_event_loop().call_later(1, client._register)


def _login_client(client):
    print("Server login")
    asyncio.get_event_loop().call_later(1, client._login)


def _queue_ping(client):
    ping_clients.append(client)
    _ping_servers()


def _connection_registered(message):
    message.client.registration_complete = True
    _queue_ping(message.client)
    for channel in message.client.channels_to_join:
        message.client.join(channel)


def _connection_denied(message):
    message.client.registration_complete = False
    print("LOGGIN DENIED BY SERVER")


def _parse_motd(message):
    pass


def _matrix_adduser(message):
    pass


def _matrix_removeuser(message):
    pass


def _matrix_joined(message):
    pass


def _matrix_left(message):
    pass


def _matrix_clients(message):
    pass


def _matrix_channeltopic(message):
    pass


signal("raw").connect(_redispatch_raw)
signal("spring").connect(_redispatch_spring)

signal("connected").connect(_login_client)

signal("spring-ping").connect(_pong)
signal("spring-pong").connect(_catch_pong)

signal("spring-said").connect(_redispatch_said)
signal("spring-saidex").connect(_redispatch_saidex)
signal("spring-saidprivate").connect(_redispatch_saidprivate)
signal("spring-saidprivateex").connect(_redispatch_saidprivateex)

signal("spring-notice").connect(_redispatch_notice)
signal("spring-joined").connect(_redispatch_joined)
signal("spring-left").connect(_redispatch_left)
signal("spring-quit").connect(_redispatch_quit)
signal("spring-kick").connect(_redispatch_kick)
signal("spring-nick").connect(_redispatch_nick)
signal("spring-mode").connect(_parse_mode)
signal("spring-005").connect(_server_supports)
signal("spring-accepted").connect(_connection_registered)
signal("spring-denied").connect(_connection_denied)

signal("spring-motd").connect(_parse_motd)

signal("spring-adduser").connect(_matrix_adduser)
signal("spring-removeuser").connect(_matrix_removeuser)

signal("spring-left").connect(_matrix_left)
signal("spring-joined").connect(_matrix_joined)

signal("spring-clients").connect(_matrix_clients)
signal("spring-channeltopic").connect(_matrix_channeltopic)
