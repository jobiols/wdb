#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wdb.server
"""

import sys
from setuptools import setup
from setuptools import find_packages

__version__ = '3.3.1'

requires = [
    "psutil>=2.1",
    "tornado>=6.0",
    "tornado_systemd",
]

if sys.platform == 'linux':
    requires.append('pyinotify')

setup(
    name="wdb.server",
    version=__version__,
    description="An improbable web debugger through WebSockets (server)",
    long_description="See http://github.com/jobiols/wdb",
    author="Jorge Obiols @ jobiols",
    author_email="jorge.obiols@github.com",
    url="http://github.com/jobiols/wdb",
    license="GPLv3",
    platforms="Any",
    scripts=['wdb.server.py'],
    packages=find_packages(),
    include_package_data=True,
    install_requires=requires,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Debuggers",
    ],
)
