from blinker import signal

capabilities_requested = {}
capabilities_available = {}
capabilities_pending = {}
registration_state = {}


def request_capability(netid, cap):
    if netid not in capabilities_requested:
        capabilities_requested[netid] = set()
    capabilities_requested[netid].add(cap)


def request_capabilities(client, caps):
    if len(registration_state[client.netid]) >= 2:
        client.writeln("CAP REQ :{}".format(" ".join(list(caps))))
        client.caps |= caps


def registration_complete(client):
    registration_state[client.netid].add("registered")
    request_capabilities(client, capabilities_available[client.netid] & capabilities_requested[client.netid])


def handle_client_create(client):
    capabilities_available[client.netid] = set()
    registration_state[client.netid] = set()
    capabilities_pending[client.netid] = set()
    client.writeln("CAP LS")


def handle_client_death(client):
    capabilities_available[client.netid] = set()
    registration_state[client.netid] = set()
    capabilities_pending[client.netid] = set()


def check_all_caps_done(client):
    if client.netid not in capabilities_pending or not capabilities_pending[client.netid]:
        client.writeln("CAP END")


def cap_done(client, cap):
    capabilities_pending[client.netid].remove(cap)
    check_all_caps_done(client)


def cap_wait(netid, cap):
    if netid not in capabilities_requested:
        capabilities_requested[netid] = set()
    capabilities_requested[netid].add(cap)

    if netid not in capabilities_pending:
        capabilities_pending[netid] = set()
    capabilities_pending[netid].add(cap)


def handle_irc_cap(message):
    if message.params[1] == "LS":
        if message.client.netid not in capabilities_available:
            capabilities_available[message.client.netid] = set()
        capabilities_available[message.client.netid].update(set(message.params[2].split()))
        print("Capabilities provided by server are {}".format(capabilities_available[message.client.netid]))
        if message.client.netid not in registration_state:
            registration_state[message.client.netid] = set()
        registration_state[message.client.netid].add("caps-known")
        request_capabilities(message.client, capabilities_available[message.client.netid] & capabilities_requested[
            message.client.netid])

    if message.params[1] == "ACK":
        print("ACK received from server, ending capability negotiation. {}".format(message.client.caps))
        signal("caps-acknowledged").send(message.client)
        check_all_caps_done(message.client)


signal("registration-complete").connect(registration_complete)
signal("netid-available").connect(handle_client_create)
signal("disconnected").connect(handle_client_death)
signal("irc-cap").connect(handle_irc_cap)
