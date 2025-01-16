#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

"""
    This plugin manages 'librespot',
    a headless Spotify Connect player daemon

    https://github.com/librespot-org/librespot

    Usage:  librespot.py   start [pulseaudio] | stop

    'pulseaudio' uses Pulseaudio as backend instead of direct output to Jack.
    This is useful if your sound card cannot run at the same samplerate as
    pe.audio.sys, as mine does (ESI UDJ6 only works at 48 KHz)

    2025-01: librespot suddently crashes, so will use a watchdog here

"""
import  sys
import  os
from    subprocess import Popen, call
from    socket import gethostname
from    getpass import getuser
import  threading
from    time import sleep

UHOME = os.path.expanduser("~")
sys.path.append(f'{UHOME}/pe.audio.sys/share/miscel')

from miscel import kill_bill


# BINARY
BINARY = '/usr/bin/librespot'


# OPTIONS LIST (do not configure here: bitrate, name, backend, device)
OTHER_OPTS = [
    #'--disable-audio-cache',
    # https://github.com/librespot-org/librespot/wiki/FAQ
    # For AUDIOPHILES
    '--mixer softvol --volume-ctrl fixed --initial-volume 100',
    '--format F32'
]

# Current user
USER = getuser()


def run_watchdog():

    def check_librespot_is_running():

        with open('/dev/null', 'w') as fnull:

            # This has a reverse logic :-|
            if call( ['pgrep', '-u', USER, 'librespot'], stdout=fnull, stderr=fnull ):
                return False
            else:
                return True

    while True:

        if not check_librespot_is_running():
            start()

        sleep(10)


def start():
    # 'librespot' binary prints out the playing track and some info.
    # We redirect them to a temporary file that will be periodically
    # read from a player control daemon.


    moreopt_str = ' '.join(OTHER_OPTS)

    cmd = f'{BINARY} --name {gethostname()} ' + \
          f'--onevent {UHOME}/pe.audio.sys/share/plugins/librespot/bind_ports.sh ' + \
          f'--bitrate 320 {BACKEND_OPTS} {moreopt_str}'

    eventsPath = f'{UHOME}/pe.audio.sys/.librespot_events'

    with open(eventsPath, 'a') as f:
        Popen( cmd.split(), stdout=f, stderr=f )

    job = threading.Thread(target=run_watchdog)
    job.start()


def stop():

    # kill previous scripts like this in background
    kill_bill( os.getpid() )

    call( ['pkill', '-u', USER, '-KILL', '-f',  'bin/librespot']  )


if __name__ == "__main__":

    if sys.argv[1:]:

        if sys.argv[1] == 'start':

            if sys.argv[2:] and 'pulse' in sys.argv[2].lower():
                BACKEND_OPTS = f'--backend pulseaudio'
            else:
                BACKEND_OPTS = f'--backend jackaudio --device librespot'

            stop()
            start()

        elif sys.argv[1] == 'stop':
            stop()

        else:
            print(__doc__)

    else:
        print(__doc__)
