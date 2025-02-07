#!/bin/bash

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

# This is only for testing purposes. The minimum or linear phase behavior
# of the soft EQ stage of Brutefir must be selected in the config file.


function help_exit {
    echo "Usage: peaudiosys_bfeq_linear_phase.sh  toggle | true | false"
    exit 0
}

if [[ $1 ]]; then

    if [[ $1 == *"true"* || $1 == *"false"* ]]; then
        new="$1"
    elif [[ $1 == *"toggle"* ]]; then
        curr=$(grep "bfeq_linear_phase:" "$HOME"/pe.audio.sys/config/config.yml)
        curr=$(echo "$curr" | cut -d ":" -f 2)
        if [[ $curr == *"true"* ]]; then
            new='false'
        else
            new='true'
        fi
    else
        help_exit
    fi
else
    help_exit
fi

# Editing config.yml
sed -i -e '/bfeq_linear_phase/c\bfeq_linear_phase: '$new \
    "$HOME"/pe.audio.sys/config/config.yml

# Restarting
peaudiosys_server_restart.sh

# Awaiting preamp service
PORT=$( grep peaudiosys_port ~/pe.audio.sys/config/config.yml | awk '{print $NF}' )
times=10
while [[ $times -ne "0" ]]; do
    ans=$(echo state | nc -N localhost $PORT)
    if [[ $ans == *"level"* ]]; then
        break
    fi
    sleep 1
    ((times--))
done

if [[ $times -eq "0" ]]; then
    echo "(!) preamp service broken :-/"
fi

# Recalculate curves
echo "level 0 add" | nc -N localhost $PORT
echo
# Check
echo "get_eq" | nc -N localhost $PORT
echo
