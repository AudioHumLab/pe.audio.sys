#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.
"""
    shairport-sync  Plays audio streamed from AirPlay sources.

    Usage:    shairport-sync.py   start | stop
"""
import  sys
import  os
from    subprocess  import Popen, call
from    socket      import gethostname
from    getpass     import getuser
import  threading
from    time        import sleep

# Debian package system service NEEDS to be disabled after installing:
#     sudo systemctl stop shairport-sync.service
#     sudo systemctl disable shairport-sync.service

UHOME = os.path.expanduser("~")
sys.path.append(f'{UHOME}/pe.audio.sys/share/miscel')

from miscel import kill_bill


def run_watchdog():

    def check_if_running():

        with open('/dev/null', 'w') as fnull:

            # This has a reverse logic :-|
            if call( ['pgrep', '-u', getuser(), 'shairport-sync'], stdout=fnull, stderr=fnull ):
                return False
            else:
                return True

    while True:

        if not check_if_running():
            start()

        sleep(10)


def start():

    log_path = f'{UHOME}/pe.audio.sys/log/shairport-sync.log'


    # Former versions used alsa but recent debian package alows jack :-)
    cmd = f'shairport-sync -a {gethostname()} -o jack'

    with open(log_path, 'a') as f:
        Popen( cmd.split(), stdout=f, stderr=f )

    job = threading.Thread(target=run_watchdog)
    job.start()


def stop():

    # kill previous scripts like this in background
    kill_bill( os.getpid() )

    call( ['pkill', '-u', getuser(), '-KILL', '-f', f'shairport-sync -a {gethostname()}'] )


if __name__ == "__main__":

    if sys.argv[1:]:

        if sys.argv[1] == 'start':
            stop()
            start()

        elif sys.argv[1] == 'stop':
            stop()

        else:
            print(__doc__)


    else:
        print(__doc__)
