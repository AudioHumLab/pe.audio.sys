#!/bin/bash

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.


# Python venv
if [[ ! $VIRTUAL_ENV ]]; then
    source "$HOME"/.env/bin/activate 1>/dev/null 2>&1
fi


BOLD=$(tput bold)
NORMAL=$(tput sgr0)

SERVERPATH="$HOME"/"pe.audio.sys/share/miscel/server.py"

opc=$1

# Reading TCP address and port from the pe.audio.sy config file
ADDR=$( grep peaudiosys_address ~/pe.audio.sys/config/config.yml | awk '{print $NF}' )
ADDR=${ADDR//\"/}; CTL_ADDR=${ADDR//\'/}
PORT=$( grep peaudiosys_port ~/pe.audio.sys/config/config.yml | awk '{print $NF}' )
if [[ ! $ADDR || ! PORT ]]; then
    echo ${BOLD}
    echo '(i) Not found control TCP server address/port in `config.yml`,'
    echo '    using defaults `0.0.0.0:9990`'
    echo ${NORMAL}
    ADDR='0.0.0.0'
    PORT=9990
fi


if [[ $opc == *"-h"* ]]; then
    echo "usage:    peaudiosys_server_restart.sh  [stop | --verbose]"
    echo ""
    echo "          stop            stops the server"
    echo "          -v --verbose    will keep messages to console,"
    echo "                          otherways will redirect to /dev/null"
    exit 0
fi


# Killing the running service:
server_is_runnnig=$(pgrep -fla "server.py peaudiosys")
if [[ ! $server_is_runnnig ]]; then
    echo "(i) pe.audio.sys server was not running."
fi
# ***NOTICE*** the -f "srtring " MUST have an ending blank in order
#              to avoid confusion with 'peaudiosys_ctrl'
pkill -KILL -u $USER -f "server.py peaudiosys "
if [[ $opc == *'stop'* ]]; then
    exit 0
fi
sleep .25


# Re-launching the service.
# (i) It is IMPORTANT to redirect stdout & stderr to keep it alive even
#     if the launcher session has been closed (e.g. a crontab job),
#     except if -v --verbose is indicated
if [[ $opc == *"-v"* ]]; then
    echo "(i) RESTARTING pe.audio.sys server (VERBOSE MODE)"
    python3 "$SERVERPATH" "peaudiosys" "$ADDR" "$PORT" -v &

else
    echo "(i) RESTARTING pe.audio.sys server (QUIET MODE redirected to /dev/null)"
    python3 "$SERVERPATH" "peaudiosys" "$ADDR" "$PORT" >/dev/null 2>&1 &
fi
