#!/usr/bin/env python
import os
import socket
import asyncio
from logging import DEBUG, INFO, WARNING, getLogger

from tornado.netutil import bind_sockets
from tornado.options import options
from tornado.tcpserver import TCPServer
from tornado_systemd import SYSTEMD_SOCKET_FD, SystemdHTTPServer
from wdb_server import server
from wdb_server.streams import handle_connection

log = getLogger('wdb_server')

# Esto pone el log en modo DEBUG
# options.debug = True
# options.more = True

if options.debug:
    log.setLevel(INFO)
    if options.more:
        log.setLevel(DEBUG)
else:
    log.setLevel(WARNING)


class WdbTCPServer(TCPServer):
    async def handle_stream(self, stream, address):
        await handle_connection(stream.socket, address)


async def main():
    if os.getenv('LISTEN_PID'):
        log.info('Getting socket from systemd')
        sck = socket.fromfd(
            SYSTEMD_SOCKET_FD + 1,
            socket.AF_INET6 if socket.has_ipv6 else socket.AF_INET,
            socket.SOCK_STREAM,
        )
        sck.setblocking(False)
        sck.listen(128)
        sockets = [sck]
    else:
        log.info('Binding sockets')
        sockets = bind_sockets(options.socket_port)

    log.info('Starting WDB TCP server')
    tcp_server = WdbTCPServer()
    tcp_server.add_sockets(sockets)

    log.info('Starting HTTP server')
    http_server = SystemdHTTPServer(server)
    http_server.listen(options.server_port)

    log.info('Entering asyncio loop')
    await asyncio.Event().wait()  # wait forever


if __name__ == '__main__':
    asyncio.run(main())
