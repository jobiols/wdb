# -*- coding: utf-8 -*-
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
import logging
import os
import sys
from multiprocessing import Process
from uuid import uuid4

# Activamos logging general
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('wdb_server')
log.info("Logger inicializado")

try:
    import pkg_resources
except ImportError:
    __version__ = "pkg_resources no encontrado"
else:
    try:
        __version__ = pkg_resources.require('wdb.server')[0].version
    except pkg_resources.DistributionNotFound:
        __version__ = "wdb.server no instalado"

# Importamos después del logger
import tornado.httpclient
import tornado.options
import tornado.process
import tornado.web
import tornado.websocket
from wdb_server.state import breakpoints, sockets, syncwebsockets, websockets

# Configuración de opciones de línea de comandos
tornado.options.define(
    'theme',
    default="clean",
    help="Wdb theme to use amongst %s" % [
        theme.replace('wdb-', '').replace('.css', '')
        for theme in os.listdir(os.path.join(os.path.dirname(__file__), "static", "stylesheets"))
        if theme.startswith('wdb-')
    ]
)
tornado.options.define("debug", default=False, help="Debug mode")
tornado.options.define(
    "unminified",
    default=False,
    help="Use the unminified js (for development only)",
)
tornado.options.define("more", default=False, help="Set debug more verbose")
tornado.options.define(
    "detached_session",
    default=False,
    help="Whether to continue program on browser close",
)
tornado.options.define(
    "socket_port",
    default=19840,
    help="Port used to communicate with wdb instances",
)
tornado.options.define(
    "server_port", default=1984, help="Port used to serve debugging pages"
)
tornado.options.define(
    "show_filename",
    default=False,
    help="Whether to show filename in session list",
)
tornado.options.define(
    "extra_search_path",
    default=False,
    help=(
        "Try harder to find the 'libpython*' shared library "
        "at the cost of a slower server startup."
    ),
)

tornado.options.parse_command_line()

from wdb_server.utils import refresh_process, LibPythonWatcher


# Seteamos nivel de logging global
for l in (
    log,
    logging.getLogger('tornado.access'),
    logging.getLogger('tornado.application'),
    logging.getLogger('tornado.general'),
):
    l.setLevel(logging.DEBUG)

log.debug("Inicializando LibPythonWatcher...")
if LibPythonWatcher:
    LibPythonWatcher(
        sys.base_prefix if tornado.options.options.extra_search_path else None
    )

# Rutas estáticas
static_path = os.path.join(os.path.dirname(__file__), "static")
template_path = os.path.join(os.path.dirname(__file__), "templates")
log.debug(f"Ruta estática: {static_path}")
log.debug(f"Ruta plantillas: {template_path}")

# Handlers principales

class HomeHandler(tornado.web.RequestHandler):
    def get(self):
        log.debug("HomeHandler.get()")
        self.render('home.html')


class StyleHandler(tornado.web.RequestHandler):
    themes = [
        theme.replace('wdb-', '').replace('.css', '')
        for theme in os.listdir(os.path.join(static_path, 'stylesheets'))
        if theme.startswith('wdb-')
    ]

    def get(self):
        log.debug(f"StyleHandler.get() - Tema actual: {self.theme}")
        self.redirect(self.static_url(f'stylesheets/wdb-{self.theme}.css'))

StyleHandler.theme = tornado.options.options.theme

class ActionHandler(tornado.web.RequestHandler):
    def get(self, uuid, action):
        log.debug(f"ActionHandler.get(uuid={uuid}, action={action})")
        if action == 'close':
            log.info(f"Cerrando sesión: {uuid}")
            sockets.close(uuid)
            sockets.remove(uuid)
            websockets.close(uuid)
            websockets.remove(uuid)
        self.redirect('/')


class DebugHandler(tornado.web.RequestHandler):
    def debug(self, fn):
        log.debug(f"DebugHandler.debug(fn={fn})")
        def run():
            from wdb import Wdb
            log.info(f"Ejecutando depuración en proceso separado: {fn}")
            Wdb.get().run_file(fn)
        Process(target=run).start()
        self.redirect('/')

    def get(self, fn):
        log.debug(f"DebugHandler.get(fn={fn})")
        self.debug(fn)

    def post(self, fn):
        log.debug("DebugHandler.post()")
        fn = self.request.arguments.get('debug_file')
        if fn and fn[0]:
            fn = fn[0].decode('utf-8')
            log.debug(f"Archivo recibido via POST: {fn}")
            self.debug(fn)

# WebSocket base con validación
class BaseWebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self, *args, **kwargs):
        log.debug("BaseWebSocketHandler.open()")
        protocol = self.request.headers.get('X-Forwarded-Proto', self.request.protocol)
        host = f"{protocol}://{self.request.headers['Host']}"
        origin = self.request.headers['Origin']

        if origin != host:
            log.warning(f"Origen inválido: {origin} != {host}")
            self.close()
            return

        self.on_open(*args, **kwargs)

class MainHandler(tornado.web.RequestHandler):
    def get(self, type_, uuid):
        log.debug(f"MainHandler.get(type_={type_}, uuid={uuid})")
        self.render('wdb.html', uuid=uuid, new_version=__version__, type_=type_)

class WebSocketHandler(BaseWebSocketHandler):
    def write(self, message):
        log.debug(f"[WebSocketHandler] socket -> websocket: {message}")
        message = message.decode('utf-8')
        if message.startswith('BreakSet|') or message.startswith('BreakUnset|'):
            log.debug("[WebSocketHandler] Interceptado BreakSet/BreakUnset")
            cmd, brk = message.split('|', 1)
            brk = json.loads(brk)
            if not brk['temporary']:
                del brk['temporary']
                if cmd == 'BreakSet':
                    log.debug(f"Añadiendo breakpoint: {brk}")
                    breakpoints.add(brk)
                elif cmd == 'BreakUnset':
                    log.debug(f"Borrando breakpoint: {brk}")
                    breakpoints.remove(brk)
        self.write_message(message)

    def on_open(self, uuid):
        log.debug(f"[WebSocketHandler] Conexión abierta para UUID: {uuid}")
        self.uuid = uuid
        if isinstance(self.uuid, bytes):
            self.uuid = self.uuid.decode('utf-8')

        if self.uuid in websockets.uuids:
            log.warning(f"Ya hay una conexión abierta para UUID: {self.uuid}. Cerrando la anterior.")
            websockets.send(self.uuid, 'Die')
            websockets.close(uuid)

        if self.uuid not in sockets.uuids:
            log.warning(f"No hay socket asociado a UUID: {self.uuid}. Cerrando conexión.")
            sockets.send(self.uuid, 'Die')
            self.close()
            return

        log.info(f"Conexión WebSocket establecida para UUID: {self.uuid}")
        websockets.add(self.uuid, self)

    def on_message(self, message):
        log.debug(f"[WebSocketHandler] Mensaje recibido: {message}")
        if message.startswith('Broadcast|'):
            message = message.split('|', 1)[1]
            log.debug(f"[WebSocketHandler] Broadcast recibido: {message}")
            sockets.broadcast(message)
        else:
            log.debug(f"[WebSocketHandler] Enviando mensaje al socket: {message}")
            sockets.send(self.uuid, message)

    def on_close(self):
        if hasattr(self, 'uuid'):
            log.info(f"[WebSocketHandler] Conexión cerrada para UUID: {self.uuid}")
            if not tornado.options.options.detached_session:
                log.debug(f"[WebSocketHandler] Cerrando socket asociado a UUID: {self.uuid}")
                sockets.send(self.uuid, 'Close')
                sockets.close(self.uuid)

class SyncWebSocketHandler(BaseWebSocketHandler):
    def write(self, message):
        log.debug(f"[SyncWebSocketHandler] servidor -> syncsocket: {message}")
        self.write_message(message)

    def on_open(self):
        self.uuid = str(uuid4())
        log.debug(f"[SyncWebSocketHandler] Nuevo UUID generado: {self.uuid}")
        syncwebsockets.add(self.uuid, self)

        if not LibPythonWatcher:
            log.debug(f"[SyncWebSocketHandler] Enviando StartLoop para UUID: {self.uuid}")
            syncwebsockets.send(self.uuid, 'StartLoop')

    def on_message(self, message):
        log.debug(f"[SyncWebSocketHandler] Mensaje recibido: {message}")
        if '|' in message:
            cmd, data = message.split('|', 1)
        else:
            cmd, data = message, ''

        if cmd == 'ListSockets':
            log.debug("[SyncWebSocketHandler] Listando sockets activos")
            for uuid in sockets.uuids:
                syncwebsockets.send(
                    self.uuid,
                    'AddSocket',
                    {
                        'uuid': uuid,
                        'filename': sockets.get_filename(uuid)
                        if tornado.options.options.show_filename else ''
                    },
                )

        elif cmd == 'ListWebsockets':
            log.debug("[SyncWebSocketHandler] Listando WebSockets")
            for uuid in websockets.uuids:
                syncwebsockets.send(self.uuid, 'AddWebSocket', uuid)

        elif cmd == 'ListBreaks':
            log.debug("[SyncWebSocketHandler] Listando breakpoints")
            for brk in breakpoints.get():
                syncwebsockets.send(self.uuid, 'AddBreak', brk)

        elif cmd == 'RemoveBreak':
            brk = json.loads(data)
            log.debug(f"[SyncWebSocketHandler] Borrando breakpoint: {brk}")
            breakpoints.remove(brk)
            brk['temporary'] = False
            sockets.broadcast('Unbreak', brk)

        elif cmd == 'RemoveUUID':
            log.debug(f"[SyncWebSocketHandler] Eliminando sesión: {data}")
            sockets.close(data)
            sockets.remove(data)
            websockets.close(data)
            websockets.remove(data)

        elif cmd == 'ListProcesses':
            log.debug(f"[SyncWebSocketHandler] Listando procesos para UUID: {self.uuid}")
            refresh_process(self.uuid)

        elif cmd == 'Pause':
            log.debug(f"[SyncWebSocketHandler] Pausando proceso PID={data}")
            if int(data) == os.getpid():
                log.debug("[SyncWebSocketHandler] Pausing self")
                def self_shell(variables):
                    import wdb
                    wdb.set_trace()
                Process(target=self_shell, args=(globals(),)).start()
            else:
                log.debug(f"[SyncWebSocketHandler] Ejecutando gdb en proceso: {data}")
                tornado.process.Subprocess(
                    ['gdb', '-p', data, '-batch']
                    + [
                        "-eval-command=call %s" % hook
                        for hook in [
                            'PyGILState_Ensure()',
                            'PyRun_SimpleString("import wdb; wdb.set_trace(skip=1)")',
                            'PyGILState_Release($1)',
                        ]
                    ]
                )

    def on_close(self):
        if hasattr(self, 'uuid'):
            log.info(f"[SyncWebSocketHandler] Conexión sincrónica cerrada para UUID: {self.uuid}")
            syncwebsockets.remove(self.uuid)

# Inicializamos la aplicación Tornado
server = tornado.web.Application(
    [
        (r"/", HomeHandler),
        (r"/style.css", StyleHandler),
        (r"/(\w+)/session/(.+)", MainHandler),
        (r"/debug/file/(.*)", DebugHandler),
        (r"/websocket/(.+)", WebSocketHandler),
        (r"/status", SyncWebSocketHandler),
    ],
    debug=tornado.options.options.debug,
    static_path=static_path,
    template_path=template_path,
)

log.info("Servidor Tornado iniciado")
log.info(f"Version: {__version__}")
log.info(f"Temas disponibles: {[t.replace('wdb-', '').replace('.css', '') for t in os.listdir(os.path.join(static_path, 'stylesheets')) if t.startswith('wdb-')]}")


# # Comprobamos nueva versión en PyPI (opcional)
# log.debug("Intentando obtener información de PyPI...")
# http = tornado.httpclient.HTTPClient()
# server.new_version = None
# try:
#     response = http.fetch(
#         'https://pypi.python.org/pypi/wdb.server/json ',
#         connect_timeout=1,
#         request_timeout=1,
#     )
#     info = json.loads(response.buffer.read().decode('utf-8'))
#     version = info['info']['version']
#     if version != __version__:
#         log.info(f"Nueva versión disponible: {version}")
#         server.new_version = version
#     else:
#         log.info("Versión actualizada")
# except Exception as e:
#     log.warning("No se pudo conectar a PyPI (esto es normal si estás offline)")
#     server.new_version = None
