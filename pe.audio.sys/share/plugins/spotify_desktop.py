#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

"""
    Launch the Spotify Desktop App alongside an spotify_monitor_daemon.py that will:

        - listen for events from Spotify Desktop

        - and writes down the metadata into a file for others to read it.

    usage:   spotify_desktop.py   start | stop

    NOTICE: In recent desktops running PipeWire, we need here to restart
            the Spotify Desktop process, in order to link it to the proper
            PipeWire-Jack sink after restarting the pe.audio.sys Jack process.

            We also RECOMMEND to minimize Spotify in order to stop
            Spotify main window to load lots of widgets with high CPU spense:

                apt install xdotool  (see below command line)

"""
#
# THIS needs: apt install playerctl
#
# For playerctl v0.x will run spotify_monitor_daemon_v1.py
# For playerctl v2.x will run spotify_monitor_daemon_v2.py

import sys
import os
from subprocess import Popen, check_output, call
from time import sleep
from getpass import getuser

UHOME = os.path.expanduser("~")
PLUGINSFOLDER = f'{UHOME}/pe.audio.sys/share/plugins'


def get_playerctl_version():
    try:
        tmp = check_output('playerctl --version'.split()).decode()
        tmp = tmp.lower().replace('v', '')
        return tmp[0]
    except:
        return 'error'


def check_Spotify_Desktop_process():
    wait_sec = 15
    while wait_sec:
        tmp = check_output( 'pgrep -fli spotify | cut -d" " -f2',
                            shell=True).decode().split()
        if 'spotify' in tmp:
            print('(spotify_monitor) found Spotify Desktop running')
            sleep(3)    # wait a while extra to ensure communication
            return True
        wait_sec -= 1
        sleep(1)
    return False


def start():

    Popen('spotify 1>/dev/null 2>&1', shell=True)
    # Safe wait to ensure we can minimize the app in order to stop
    # Spotify main window to load lots of widgets...
    sleep(10)
    Popen('xdotool search --name Spotify windowminimize %@', shell=True)


    if not check_Spotify_Desktop_process():
        print('(spotify_monitor) Unable to detect Spotify Desktop running')
        sys.exit()

    v = get_playerctl_version()

    if v in ('0', '1', '2'):
        if v in ('0', '1'):
            v = 1
        Popen( f'{PLUGINSFOLDER}/spotify_monitor/spotify_monitor_daemon_v{v}.py' )
        print( f'(spotify_monitor) Starting \'spotify_monitor_daemon_v{v}.py\'' )
    else:
        print( '(spotify_monitor) Unable to find playerctl --version' )


def stop():

    call( f'pkill -u {getuser()} -f spotify_monitor_daemon', shell=True )

    Popen('killall spotify', shell=True)


if sys.argv[1:]:

    if sys.argv[1] == 'stop':
        stop()

    elif sys.argv[1] == 'start':
        start()

    else:
        print(__doc__)

else:
    print(__doc__)
