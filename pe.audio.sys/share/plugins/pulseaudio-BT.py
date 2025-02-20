#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

"""
    -- THIS IS OBSOLETE --

    Enables Pulseaudio to get sound from paired BT devices.

    usage:  pulseaudio-BT.py   start|stop

    (i) Needs Pulseaudio BT module (install it if necesssary)

            pulseaudio-module-bluetooth

"""
from subprocess import Popen
import sys

PAmodules = ['module-bluetooth-discover', 'module-bluetooth-policy']


def start():
    # Enable PA BT modules
    for m in PAmodules:
        Popen( f'pactl load-module {m}'.split() )


def stop():
    for m in PAmodules:
        Popen( f'pactl unload-module {m}'.split() )


if __name__ == '__main__':

    if sys.argv[1:]:
        if sys.argv[1] == 'stop':
            stop()
        elif sys.argv[1] == 'start':
            start()
        else:
            print(__doc__)
            sys.exit()
