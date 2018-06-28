from asyncblink import signal
import base64

import asyncspring.plugins.cap

authentication_info = {}


class AuthenticationFailed(Exception): pass


def auth(client, username, password):
    """
    Queue an authentication request using SASL PLAIN on the given client, with
    the given account name and password.
    """
    asyncspring.plugins.cap.cap_wait(client.netid, "sasl")
    authentication_info[client.netid] = [username, password]


def caps_acknowledged(client):
    """
    Internal method automatically called when the server sends CAP ACK, used to
    request authentication.
    """
    if client.netid in authentication_info:
        client.writeln("AUTHENTICATE PLAIN")


def handle_authenticate(message):
    """
    Actually send the authentication data. Done after the server acknowledges
    our request to start authentication.
    """
    if message.params[0] == "+":
        print("Authentication request acknowledged, sending username/password")
        authinfo = authentication_info[message.client.netid]
        authdata = base64.b64encode("{0}\x00{0}\x00{1}".format(*authinfo).encode())
        message.client.writeln("AUTHENTICATE {}".format(authdata.decode()))


def handle_900(message):
    """
    Handle numeric 900 ("SASL authentication successful").
    """
    print("SASL authentication complete.")
    signal("sasl-auth-complete").send(message)
    signal("auth-complete").send(message)
    asyncspring.plugins.cap.cap_done(message.client, "sasl")


def handle_failure(message):
    """
    Handle numeric 904 ("SASL authentication failed").
    """
    raise AuthenticationFailed("Numeric {}".format(message.verb))


signal("caps-acknowledged").connect(caps_acknowledged)
signal("irc-authenticate").connect(handle_authenticate)
signal("irc-900").connect(handle_900)
signal("irc-904").connect(handle_failure)
