#!/usr/bin/env python3
"""
    A helper to analyze the real XO output as sent to the sound card DAC,
    so you can decide if more or less convolver gain can be used on each way
    alongside with some analog line attenuator, this way you can probably
    improve the S/N mainly in the tweeter analog chain.

    JAPA and JAAA are excellent tools from Fons Adriaensen
    https://kokkinizita.linuxaudio.org/linuxaudio/index.html

    Notice that both tools have nice signal generators:

    - JAAA: white noise and two sines
    - JAPA: pink and white noise

    Usage:

        wa2_2_RTA.py   [-japa | -jaaa | -deq]  [wayID]

        -deq    will tray to connect to an external Behringer DEQ2496 if available under JACK

        wayID   'sw', 'lo', 'mi', 'hi'

        if not wayID is given, the RTA will be connected to the pe.audio.sys preamp ports.
"""

import sys
import jack
import psutil
from subprocess import Popen
from time import sleep


def jxxx_is_running(process_name):
    # Iterate through all running processes
    for proc in psutil.process_iter(['cmdline']):
        try:
            # (i) proc.info['cmdline']) is a list of command line args
            cmdline = ' '.join( proc.info['cmdline'] )
            # Match process name (case-insensitive)
            if process_name.lower() in cmdline.lower() and not 'way_2_RTA' in cmdline:
                return True
        except:
            pass
    return False


def run_jxxx(jxxx):

    try:
        Popen(f'{jxxx} -J'.split())
        sleep(2)
        return True
    except Exception as e:
        print(e)
        return False


def clear_rta():

    for p in (RTA_PORTS):
        clis = jc.get_all_connections(p)
        for cli in clis:
            try:
                jc.disconnect(cli, p)
            except Exception as e:
                print(e)


def restore_rta():

    print(f'restoring RTA `{RTA}` to pre-amp')

    clear_rta()

    for o, i in zip(PRE_PORTS, RTA_PORTS):
        try:
            jc.connect(o, i)
        except Exception as e:
            print(e)


def way_2_rta(way):

    clear_rta()

    outs = jc.get_ports(f'brutefir:{way}')

    if not outs:
        print(f'jack port NOT FOUND: brutefir:{way}')

    for o, i in zip(outs, RTA_PORTS):
        try:
            jc.connect(o, i)
        except Exception as e:
            print(e)


if __name__ == "__main__":

    # https://kokkinizita.linuxaudio.org/linuxaudio/index.html
    # JAPA or JAAA or an external DEQ2496

    PRE_PORTS = ('pre_in_loop:output_1', 'pre_in_loop:output_2')
    RTA = 'japa'
    way = ''

    for opc in sys.argv[1:]:

        if '-jaaa' in opc:
            RTA = 'jaaa'

        elif '-japa' in opc:
            RTA = 'japa'

        elif '-d' in opc:
            RTA = 'DEQ2496'

        elif '-h' in opc:
            print(__doc__)
            sys.exit()

        else:
            way = opc


    if RTA in  ('japa', 'jaaa') and not jxxx_is_running(RTA):
         if not run_jxxx(RTA):
            print(f'Cannot run `{RTA}`')
            sys.exit()


    jc        = jack.Client('tmp')
    RTA_PORTS = jc.get_ports(RTA, is_input=True)[:2]

    if not RTA_PORTS:
        print(f'jack ports NOT found: {RTA}')
        sys.exit()

    ways =  ('sw', 'lo', 'mi', 'hi')

    if not way in ways:
        if way:
            print( f'must give a valid way: {ways}' )
        else:
            restore_rta()
        sys.exit()

    way_2_rta(way)
