#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

import os
import sys
import subprocess as sp
from   time import sleep
from   camilladsp import CamillaClient

UHOME = os.path.expanduser("~")
sys.path.append(f'{UHOME}/pe.audio.sys/share/miscel')

from   miscel   import process_is_running, LOG_FOLDER, Fmt
import jack_mod as jack

COMPRESSOR_CYCLE = ['off', '1.0:1', '2.0:1', '3.0:1']

HOST        = '127.0.0.1'
PORT        = 1234

# CamillaDSP config file path
CAMILLA_YML = f'{UHOME}/pe.audio.sys/config/camilladsp.yml'

# The CamillaDSP connection
PC = CamillaClient(HOST, PORT)


def _remove_jack_camilla_from_system_card():

    tries = 10
    while tries:
        x = jack.get_ports('cpal_client', is_audio=True)
        if len(x) == 4:
            break
        tries -= 1
        sleep(.1)

    sleep(.1)   # safest

    if not tries:
        raise Exception('Unable to get CamillaDSP ports in JACK, check log folder.')

    for (is_input, is_output) in ((True, False), (False, True)):

        for cpal_port in jack.get_ports('cpal_client', is_input=is_input, is_output=is_output):

            wired_ports = jack.get_all_connections(cpal_port)

            for p in wired_ports:
                if is_input:
                    jack.connect(p, cpal_port, 'disconnect')
                else:
                    jack.connect(cpal_port, p, 'disconnect')


def _insert_cdsp():

    # disconnect pre_in_loop --> brutefir (if so)
    for pre_out in ('pre_in_loop:output_1', 'pre_in_loop:output_2'):
        pre_out_clients = jack.get_all_connections(pre_out)
        pre_out_clients = [x.name for x in pre_out_clients]
        for pre_out_client in [c for c in pre_out_clients if 'brutefir' in c.lower()]:
            jack.connect(pre_out, pre_out_client, 'disconnect')

    # connect pre_in_loop --> cpal
    jack.connect('pre_in_loop:output_1', 'cpal_client_in:in_0')
    jack.connect('pre_in_loop:output_2', 'cpal_client_in:in_1')

    # connect cpal --> brutefir
    jack.connect('cpal_client_out:out_0', 'brutefir:in.L')
    jack.connect('cpal_client_out:out_1', 'brutefir:in.R')


def _init(compressor='off'):
    """ defaults to bypass the compressor stage
    """

    def stop_cdsp():

        sp.call('killall -KILL camilladsp 1>/dev/null 2>&1', shell=True)
        sleep(.25) # safest

        tries = 10
        while tries:
            if not process_is_running('camilladsp'):
                break
            tries -= 1
            sleep(.1)
        if not tries:
            raise Exception('Unable to stop CamillaDSP.')


    def run_cdsp(config_file):

        # Starting CamillaDSP **MUTED**
        RATE     = jack.get_samplerate()
        cdsp_cmd = f'camilladsp --wait --mute -r {RATE} -a {HOST} -p {PORT} ' + \
                   f'--logfile "{LOG_FOLDER}/camilladsp.log" {config_file}'

        print(f'{Fmt.MAGENTA}Pleae wait for CamillaDSP to start ...{Fmt.END}')
        p = sp.Popen( cdsp_cmd, shell=True )

        tries = 120
        while tries:
            try:
                PC.connect()
                break
            except:
                tries -= 1
                sleep(.5)

        if not tries:
            raise Exception('Unable to run CamillaDSP, check log folder.')

        print(f'{Fmt.BLUE}Logging CamillaDSP to log/camilladsp.log ...{Fmt.END}')

        # Remove JACK system connections
        _remove_jack_camilla_from_system_card()

        # Inserting before Brutefir
        _insert_cdsp()

        # Unmute
        PC.volume.set_main_mute(False)


    if process_is_running('camilladsp'):
        stop_cdsp()

    # Running
    run_cdsp(CAMILLA_YML)

    # Set the compressor (default is bypassed)
    _bypass('compressor', not compressor != 'off')


def _bypass(step='', mode='state'):
    """ Bypass a pipeline step
        (only works for a `compressor` processor step)

        returns: the bypassed state (boolean)
    """

    def get_step_pipeline_index(cfg, step_id):
        index = -1
        for i, s in enumerate( cfg["pipeline"] ):
            if step_id in s["name"]:
                index = i
        return index


    cfg = PC.config.active()

    if 'compressor' in step:

        i = get_step_pipeline_index(cfg, step)

        if mode in (True, 'true', 1, 'on'):
            cfg["pipeline"][i]["bypassed"] = True

        elif mode in (False, 'false', 0, 'off'):
            cfg["pipeline"][i]["bypassed"] = False

        else:
            return cfg["pipeline"][i]["bypassed"]

        # mute / unmute to avoid pops
        mute(True)
        PC.config.set_active(cfg)
        sleep(.1)
        mute(False)

        return PC.config.active()["pipeline"][i]["bypassed"]


def mute(mode='state'):
    """ Mute camillaDSP

        returns: the mute state (boolean)
    """

    if mode in (True, 'true', 'on', 1):
        PC.volume.set_main_mute(True)

    if mode in (False, 'false', 'off', 0):
        PC.volume.set_main_mute(False)

    if mode == 'toggle':
        new_mode = {True: False, False: True} [PC.volume.main_mute() ]
        PC.volume.set_main_mute(new_mode)


    return PC.volume.main_mute()


def state():
    return PC.general.state().name


def config():
    return PC.config.active()


def compressor(oper='', ratio=''):
    """ Modifies both:
            - the compressor pipeline bypass
            - the compressor processor parameters

        Returns a json string with the compressor state and parameters, example:

            '{"active": True, "threshold": -60.0, "ratio": "3.0:1", "makeup_gain": 26.7}'
    """

    def get_parameters():

        cfg = PC.config.active()
        pms = cfg["processors"]["tv_compressor"]["parameters"]
        threshold   = pms["threshold"]
        factor      = pms["factor"]
        makeup_gain = pms["makeup_gain"]

        return {'threshold':threshold, 'ratio': f'{factor}:1', 'makeup_gain': makeup_gain}


    def rotate_compressor():

        if not _bypass('compressor'):
            current = get_parameters()["ratio"]
        else:
            current = 'off'

        # If current ratio is not included in COMPRESSOR_CYCLE
        try:
            cur_index   = COMPRESSOR_CYCLE.index(current)
        except:
            cur_index = -1

        next_index  = (cur_index + 1) % len(COMPRESSOR_CYCLE)

        new = COMPRESSOR_CYCLE[next_index]

        if new == 'off':
            _bypass('compressor', True)

        else:
            _bypass('compressor', False)
            set_compressor(new)


    def set_compressor(ratio):

        def calc_makeup_gain(fac, th=60):
            """ Estimates the make up gain for a given compression factor, that is
                a compressor ratio of "fac:1", assuming a "quasi full scale compressor"
                (threshold = -60 dB)
            """

            experimetal_divider = 1.5

            return round( -(th - th / fac) / experimetal_divider, 1)

        threshold   = -60
        factor      = round(float( ratio.split(':')[0] ), 1)
        makeup_gain = calc_makeup_gain(factor, threshold)

        cfg = PC.config.active()
        pms = cfg["processors"]["tv_compressor"]["parameters"]
        pms["threshold"]   = threshold
        pms["factor"]      = factor
        pms["makeup_gain"] = makeup_gain

        PC.config.set_active(cfg)


    # Compressor enable / disable commands
    if oper in ('on', True, 'true'):
        _bypass('compressor', False)

    elif oper in ('off', False, 'false'):
        _bypass('compressor', True)

    elif oper == 'toggle':
        new_mode = {True: False, False: True} [ _bypass('compressor') ]
        _bypass('compressor', new_mode)

    # State command
    elif oper == 'get':
        pass

    # Change ratio commands
    elif oper == 'set':
        set_compressor(ratio)

    elif oper == 'rotate':
        rotate_compressor()

    else:
        return 'not valid'

    parameters  = get_parameters()
    active      = not _bypass('compressor', 'state')

    return  {'active': active, 'parameters': parameters}

