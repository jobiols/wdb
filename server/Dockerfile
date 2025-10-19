# ============================================================================
# WDB Fork - Enhanced Web Debugger
# Based on the original project by Florian Mounier (Kozea)
# License: GPLv3
# Maintainer: Jorge Obiols <jorge.obiols@gmail.com>
# ============================================================================

FROM python:3.13.5-alpine

LABEL maintainer="Jorge Obiols <jorge.obiols@gmail.com>" \
      license="GPLv3" \
      description="Fork of WDB with improvements and Python 3.13 compatibility. Based on the original project by Florian Mounier (Kozea)."

RUN apk add --no-cache git gcc musl-dev linux-headers

RUN pip install --no-cache-dir \
    git+https://github.com/jobiols/wdb.git@master.py3.12-compatible-minimalist#subdirectory=client \
    git+https://github.com/jobiols/wdb.git@master.py3.12-compatible-minimalist#subdirectory=server

EXPOSE 19840 1984
CMD ["wdb.server.py", "--detached_session"]
