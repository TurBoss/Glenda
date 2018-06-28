"""
parser.py
Purpose: Conversion of RFC1459 messages to/from native objects.

Copyright (c) 2014, William Pitcock <nenolod@dereferenced.org>

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""


class LobbyMessage:
    """
    Represents an Lobby message.
    """

    @classmethod
    def from_data(cls, verb, params=None, source=None, tags=None):
        """
        Create a new RFC1459Message from the given verb, parameters, and source
        having the given tags.
        """
        o = cls()
        o.verb = verb
        o.tags = dict()
        o.source = None
        o.params = list()

        if params:
            o.params = params

        if source:
            o.source = source

        if tags:
            o.tags.update(**tags)

        return o

    @classmethod
    def from_message(cls, message):
        """
        Create a new LobbyMessage from an unparsed Lobby line.
        """

        if isinstance(message, bytes):
            message = message.decode('UTF-8', 'replace')

        s = message.split(' ')

        tags = None
        if s[0].startswith('@'):
            tag_str = s[0][1:].split(';')
            s = s[1:]
            tags = {}

            for tag in tag_str:
                k, v = tag.split('=', 1)
                tags[k] = v

        source = "Lobby"
        if s[0] == 'SAID' or s[0] == 'SAIDEX':
            source = s[2]
        elif s[0] == 'SAIDPRIVATE' or s[0] == 'SAIDPRIVATEEX':
            source = s[1]

        verb = s[0].upper()
        params = s[1:]

        for param in params:
            if param.startswith(':'):
                idx = params.index(param)
                arg = ' '.join(params[idx:])
                arg = arg[1:]
                params = params[:idx]
                params.append(arg)
                break

        return cls.from_data(verb, params, source, tags)

    def __str__(self):
        return f"LobbyMessage: verb={self.verb}, params={self.params}, source={self.source}"
