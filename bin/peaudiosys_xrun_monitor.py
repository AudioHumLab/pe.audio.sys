#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

""" A monitor for PipeWire or Jack XRUNS

    For Pipewire, will poll periodically 'pw-top' utility

    For Jack, will set a python-jack callback
"""

import subprocess as sp
import threading
from time import sleep
import jack


PWTOP_WANTED = ['jack_sink', 'spotify']
PWTOP_PERIOD = 3

pw_xruns   = 0
jack_xruns = 0


def get_pw_top_errors():
    """
    """

    res = []

    try:
        tmp = sp.check_output('pw-top -b -n2'.split()).decode()

        # S   ID  QUANT   RATE    WAIT    BUSY   W/Q   B/Q  ERR FORMAT           NAME
        # C   31      0      0    ---     ---   ---   ---     0                  Dummy-Driver
        # C   32      0      0    ---     ---   ---   ---     0                  Freewheel-Driver
        # C   38      0      0    ---     ---   ---   ---     0                  jack_sink
        # C   42      0      0    ---     ---   ---   ---     0                  Midi-Bridge
        # C   53      0      0    ---     ---   ---   ---     0                  spotify
        # S   ID  QUANT   RATE    WAIT    BUSY   W/Q   B/Q  ERR FORMAT           NAME
        # S   31      0      0    ---     ---   ---   ---     0                  Dummy-Driver
        # S   32      0      0    ---     ---   ---   ---     0                  Freewheel-Driver
        # R   38    512  44100  60,7us  10,1us  0,01  0,00    0     F32P 2 44100 jack_sink
        # R   53   8192  44100  24,8us  22,2us  0,00  0,00    0    F32LE 2 44100  + spotify
        # S   42      0      0    ---     ---   ---   ---     0                  Midi-Bridge

    except:
        return res

    lines = tmp.split('\n')
    lines = [x.strip() for x in lines]

    for line in lines:

        if 'W/Q' in line and 'B/Q' in line:
            res = []

        for w in PWTOP_WANTED:

            if line.endswith(w):

                line_chunks = line.split()

                err = int(line_chunks[8])

                res.append( (w, err) )

    return res


def do_pw_top_loop():

    pw_top_failures = 0

    while True:

        warning = ''

        errors = get_pw_top_errors()

        if not errors:
            print('PIPEWIRE pw-top NOT RESPONDING')
            pw_top_failures += 1

        for e in errors:
            if e[1] > 0:
                warning += f' {e[0]}:{e[1]}'

        if warning:
            warning = 'pw-top XRUNS ' + warning
            print(warning)

        if pw_top_failures > 3:
            pass

        sleep(PWTOP_PERIOD)


def pw_is_running():

    try:
        sp.check_output('pgrep pipewire'.split())
        return True
    except:
        return False


def jack_xrun_handler(x):
    print(f'jackd XRUNS: {str(x)}')


if __name__ == "__main__":

    # Pipewire monitoring is optional

    if pw_is_running():
        pw_top_job = threading.Thread(target=do_pw_top_loop)
        pw_top_job.start()
        tmp = "pw-top or "
    else:
        tmp = ''


    print(f'waiting for xruns in {tmp}jackd ...')

    # Jack monitoring
    jcli = jack.Client('tmp', no_start_server=True)
    jcli.set_xrun_callback(jack_xrun_handler)

    with jcli:
        jcli.activate()

        try:
            while True:
                sleep(1)

        except KeyboardInterrupt:
            print("Exiting Jack client...")

        finally:
            jcli.deactivate()
            jcli.close()
            print("Jack client exited.")



