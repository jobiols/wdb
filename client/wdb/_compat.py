import sys
from urllib.parse import quote
from socketserver import TCPServer
from collections import OrderedDict
from importlib.util import find_spec
from importlib import import_module

def to_bytes(string):
    return string.encode('utf-8')

def from_bytes(bytes_):
    return bytes_.decode('utf-8')

def force_bytes(bytes_):
    if isinstance(bytes_, str):
        return bytes_.encode('utf-8')
    return bytes_

# def u(s):
#     return s

def is_str(string):
    return isinstance(string, (str, bytes))

def existing_module(module):
    return bool(find_spec(module))

try:
    from log_colorizer import get_color_logger
except ImportError:
    import logging
    logger = logging.getLogger
else:
    logger = get_color_logger

def _detect_lines_encoding(lines):
    if not lines or lines[0].startswith(u("\xef\xbb\xbf")):
        return "utf-8"
    magic = _cookie_search("".join(lines[:2]))
    if magic is None:
        return 'utf-8'
    encoding = magic.group(1)
    try:
        codecs.lookup(encoding)
    except LookupError:
        return 'utf-8'
    return encoding