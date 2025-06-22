FROM python:3.13.5-alpine

RUN apk add --no-cache git gcc musl-dev linux-headers

RUN pip install --no-cache-dir \
    git+https://github.com/jobiols/wdb.git@master.py3.12-compatible-minimalist#subdirectory=client \
    git+https://github.com/jobiols/wdb.git@master.py3.12-compatible-minimalist#subdirectory=server

EXPOSE 19840 1984
CMD ["wdb.server.py", "--detached_session"]
