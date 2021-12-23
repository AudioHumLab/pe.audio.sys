#!/usr/bin/env python3

# Copyright (c) 2021 Rafael Sánchez
# This file is part of 'pe.audio.sys', a PC based personal audio system.
#
# This is based on 'pre.di.c,' a preamp and digital crossover
# https://github.com/rripio/pre.di.c
# Copyright (C) 2018 Roberto Ripio
# 'pre.di.c' is based on 'FIRtro', a preamp and digital crossover
# https://github.com/AudioHumLab/FIRtro
# Copyright (c) 2006-2011 Roberto Ripio
# Copyright (c) 2011-2016 Alberto Miguélez
# Copyright (c) 2016-2018 Rafael Sánchez
#
# 'pe.audio.sys' is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# 'pe.audio.sys' is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with 'pe.audio.sys'.  If not, see <https://www.gnu.org/licenses/>.

""" A JACK wrapper
"""

from time import sleep
import jack

JCLI = jack.Client('tmp', no_start_server=True)
JCLI.activate()


def connect(p1, p2, mode='connect', verbose=True):
    """ Low level tool to connect / disconnect a pair of ports.
    """

    # will retry 10 times every .1 sec
    times = 10
    while times:

        try:
            if 'dis' in mode or 'off' in mode:
                JCLI.disconnect(p1, p2)
            else:
                JCLI.connect(p1, p2)
            result = 'done'
            break

        except jack.JackError as e:
            result = f'{e}'
            if verbose:
                print( f'(jack_mod) Exception: {result}' )

        sleep(.1)
        times -= 1

    return result


def connect_bypattern( cap_pattern, pbk_pattern, mode='connect' ):
    """ High level tool to connect/disconnect a given port name patterns.
        Also works for port alias patterns.
    """

    # Try to get ports by a port name pattern
    cap_ports = JCLI.get_ports( cap_pattern, is_output=True )
    pbk_ports = JCLI.get_ports( pbk_pattern, is_input=True )

    # If not found, it can be an ALIAS pattern
    if not cap_ports:
        for p in JCLI.get_ports( is_output=True ):
            # A port can have 2 alias
            for palias in p.aliases:
                if cap_pattern in palias:
                    cap_ports.append(p)
    if not pbk_ports:
        for p in JCLI.get_ports( is_input=True ):
            # A port can have 2 alias
            for palias in p.aliases:
                if pbk_pattern in palias:
                    pbk_ports.append(p)

    #print('CAPTURE  ====> ', cap_ports)  # DEBUG
    #print('PLAYBACK ====> ', pbk_ports)

    errors = ''
    if not cap_ports:
        tmp = f'cannot find jack port "{cap_pattern}" '
        print(f'(jack_mod) {tmp}')
        errors += tmp
    if not pbk_ports:
        tmp = f'cannot find jack port "{pbk_pattern}" '
        print(f'(jack_mod) {tmp}')
        errors += tmp

    mode = 'disconnect' if ('dis' in mode or 'off' in mode) else 'connect'
    for cap_port, pbk_port in zip(cap_ports, pbk_ports):
        connect(cap_port, pbk_port, mode)


    if not errors:
        return 'ordered'
    else:
        return errors


def clear_preamp():
    """ Force clearing ANY clients, no matter what input was selected
    """
    preamp_ports = JCLI.get_ports('pre_in_loop', is_input=True)
    for preamp_port in preamp_ports:
        for client in JCLI.get_all_connections(preamp_port):
            connect( client, preamp_port, mode='off' )


def get_samplerate():
    """ wrap function """
    return JCLI.samplerate


def get_all_connections(pname):
    """ wrap function """
    ports = JCLI.get_all_connections(pname)
    return ports


def get_ports(pattern='',  is_audio=True, is_midi=False,
                                is_input=False, is_output=False,
                                is_physical=False, can_monitor=False,
                                is_terminal=False ):
    """ wrap function """
    ports = JCLI.get_ports(pattern, is_audio, is_midi,
                                    is_input, is_output,
                                    is_physical, can_monitor,
                                    is_terminal )
    return ports
