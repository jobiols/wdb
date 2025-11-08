#!/usr/bin/env bash
sd build --rm=true --no-cache=true -t jobiols/wdb:3.3.2 ./
result=$?
if [ "$result" -eq 0 ]; then
    sd push jobiols/wdb:3.3.2
else
    echo "Falló la creación de la imagen"
fi
exit $result
