# *-* coding: utf-8 *-*
# This file is part of wdb
#
# wdb Copyright (c) 2012-2016  Florian Mounier, Kozea
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import asyncio
from logging import getLogger
from struct import unpack

from tornado.iostream import IOStream, StreamClosedError
from tornado.options import options
from wdb_server.state import breakpoints, sockets, websockets

log = getLogger('wdb_server')
log.setLevel(10 if options.debug else 30)


async def handle_connection(connection, address):
    log.info('Connection received from %s' % str(address))
    stream = IOStream(connection, max_buffer_size=1024 * 1024 * 1024)

    try:
        raw_length = await stream.read_bytes(4)
        uuid_length, = unpack("!i", raw_length)
        assert uuid_length == 36, 'Wrong uuid length'

        uuid_bytes = await stream.read_bytes(uuid_length)
        uuid = uuid_bytes.decode("utf-8")
        log.debug('Assigning stream to %s' % uuid)

        sockets.add(uuid, stream)
        stream.set_close_callback(lambda: on_close(uuid))
        await read_loop(stream, uuid)

    except StreamClosedError:
        log.warning('Stream closed unexpectedly for %s' % address)
    except Exception as e:
        log.error("Error during connection handling: %s", e)


def on_close(uuid):
    log.info('uuid %s closed', uuid)
    if websockets.get(uuid):
        websockets.send(uuid, 'Die')
        websockets.close(uuid)
        websockets.remove(uuid)
    sockets.remove(uuid)


async def read_loop(stream, uuid):
    try:
        while True:
            raw_length = await stream.read_bytes(4)
            length, = unpack("!i", raw_length)
            frame = await stream.read_bytes(length)
            await handle_frame(uuid, stream, frame)
    except StreamClosedError:
        log.warning('Closed stream for %s' % uuid)


async def handle_frame(uuid, stream, frame):
    decoded = frame.decode('utf-8')
    if decoded == 'ServerBreaks':
        sockets.send(uuid, json.dumps(breakpoints.get()))
    elif decoded == 'PING':
        log.info('%s PONG' % uuid)
    elif decoded.startswith('UPDATE_FILENAME'):
        filename = decoded.split('|', 1)[1]
        sockets.set_filename(uuid, filename)
    else:
        websockets.send(uuid, frame)
