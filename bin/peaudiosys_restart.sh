#!/bin/bash

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.


# Python venv
if [[ ! $VIRTUAL_ENV ]]; then
    source "$HOME"/.env/bin/activate 1>/dev/null 2>&1
fi


function do_stop {
    echo '(i) STOPPING pe.audio.sys'
    $HOME/pe.audio.sys/start.py stop
}


function do_start {

    #if [[ ! $XDG_CURRENT_DESKTOP ]]; then
    if [[ ! $DBUS_SESSION_BUS_ADDRESS ]]; then
        # Needed for jackd when called w/o X environment:
        export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket
    fi

    # (i) Unattended restarts in headless machines can have a weird behavior,
    #     so will retry restarting if necessary up to 3 times.
    tries=3
    if [[ $1 == *'-n'* ]]; then
        tries=1
    fi
    c=1
    while [[ $c -le $tries ]]; do

        echo "$(date +%Y-%m-%dT%H:%M:%S)"" try #"$c >> $HOME/pe.audio.sys/log/peaudiosys_restart_tries.log
        echo '(i) RESTARTING pe.audio.sys (all printouts hidden to /dev/null)'
        echo '    Startup process logged in <pe.audio.sys/log/start.log>'
        $HOME/pe.audio.sys/start.py all --log 1>/dev/null 2>&1 &

        echo '    waiting for the server to be running ... .. .'
        # wait a bit to ensure the server is shut down
        sleep 5
        n=55
        ok='false'
        while [[ $n -gt 0 ]]; do
            # ***NOTICE*** the -f "srtring " MUST have an ending blank in order
            #              to avoid confusion with 'peaudiosys_ctrl'
            if [[ $(pgrep -fla "server.py peaudiosys " -u $USER) ]]; then
                ok='true'
                break
            fi
            sleep 1
            ((n-=1))
        done

        if [[ $ok == 'true' ]]; then
            echo "    OK, server running in "$((60-n))"s"
            break
        else
            if [[ $c -lt $tries ]]; then
                echo "    server NOT detected in 60s, retrying ..."
            else
                echo "    server NOT detected during "$c" attempts. Bye."
            fi
        fi

        ((c+=1))

    done

}


if [[ $1 == 'stop' ]]; then
    do_stop

elif [[ ! $1 || $1 == *'start' ]]; then
    do_start $2

else
    echo
    echo "USAGE:   peaudiosys_restart.sh  [ start [--noretry]  |  stop ]"
    echo
    echo "         --noretry   will skip retrying up to 3 times"
    echo
    echo "         Startup process will be logged in <pe.audio.sys/log/start.log>"
    echo "         For further debugging run manually from a terminal:"
    echo "             peaudio.sys/start.py all & "
    echo

fi
