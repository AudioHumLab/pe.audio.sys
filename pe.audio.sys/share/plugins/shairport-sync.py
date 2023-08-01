#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

"""
    shairport-sync  Plays audio streamed from AirPlay sources.

    use:    shairport-sync.py   start | stop
"""

import sys
from subprocess import Popen


def start():
    # Former versions used alsa but recent debian package alows jack :-)
    cmd = 'shairport-sync -a $(hostname) -o jack'
    Popen( cmd, shell=True )


def stop():
    Popen( ['pkill', '-KILL', '-f', 'shairport-sync'] )


if sys.argv[1:]:
    try:
        option = {  'start' : start,
                    'stop'  : stop
                  }[ sys.argv[1] ]()
    except:
        print( '(plugins/shairport-sync) bad option' )
else:
    print(__doc__)