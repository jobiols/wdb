FROM python:3.13.5

RUN pip install git+https://github.com/jobiols/wdb.git@master.py3.12-compatible-minimalist#subdirectory=client
RUN pip install git+https://github.com/jobiols/wdb.git@master.py3.12-compatible-minimalist#subdirectory=server

EXPOSE 19840
EXPOSE 1984
CMD ["wdb.server.py", "--detached_session"]
