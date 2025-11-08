FROM python:3.14-slim
LABEL maintainer="Jorge Obiols <jorge.obiols@gmail.com>" \
      license="GPLv3" \
      description="WDB server with Python 3.14 compatibility."

ARG WDB_VERSION="3.3.2"

# Dependencias necesarias para compilar e instalar
RUN apt-get update && apt-get install -y --no-install-recommends \
      git \
      build-essential \
    && rm -rf /var/lib/apt/lists/*

# Clonar e instalar WDB desde GitHub público
RUN git clone https://github.com/jobiols/wdb.git /opt/wdb \
    && pip install /opt/wdb/client \
    && pip install /opt/wdb/server \
    && rm -rf /opt/wdb

EXPOSE 19840
EXPOSE 1984

CMD ["wdb.server.py", "--detached_session", "--debug", "--more"]