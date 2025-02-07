#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

""" Controls the preamp (inputs, level, tones and convolver)
"""

import  sys
from    os.path             import expanduser

UHOME = expanduser("~")
sys.path.append(f'{UHOME}/pe.audio.sys/share/miscel')

from    config                  import  CONFIG
from    miscel                  import  get_remote_zita_params, \
                                        remote_zita_restart
from    preamp_mod.core         import  Preamp, Convolver

# INITIATE A PREAMP INSTANCE
preamp = Preamp()
if 'powersave' in CONFIG and CONFIG["powersave"] == True:
    preamp.powersave('on')
preamp.save_state()

# INITIATE A CONVOLVER INSTANCE (XO and DRC management)
convolver = Convolver()

# Import CamillaDSP (currently only used for an optional compressor)
if CONFIG["use_compressor"]:

    import  camilla_dsp as cdsp
    # Initiate the websocket
    cdsp.PC.connect()
    # Camilla compresor is baypassed at startup
    preamp.state["compressor"] = 'off'


# Interface function for this module
def do( cmd, argstring ):
    """ Processes commands for audio control

        (i) The full_command sintax:  <command> [arg [add] ]
            'arg' is given only with some commands,
                  as an option for relative values ordering.
    """

    def analize_arg_add(argstring):
        """ returns a tuple ( <arg>, <add:True|False> )
        """

        arg, add = '', False

        args_list = argstring.replace('\r', '').replace('\n', '').split()

        if args_list[0:]:
            if args_list[-1] == 'add':
                add = True
                arg = ' '.join( args_list[:-1] )
            else:
                arg = ' '.join( args_list[:] )

        return (arg, add)

    # (i) Below we use *dummy to accommodate the parser mechanism wich
    # will include two arguments for any call here, even when not necessary.

    # 'mono' is a former command, here it is redirected to 'midside'
    def set_mono(x, *dummy):
        try:
            x = { 'on':     'mid',
                  'off':    'off',
                  'toggle': { 'off':'mid', 'side':'off', 'mid':'off'
                             } [ preamp.state['midside'] ]
                } [x]
            return preamp.set_midside(x)
        except:
            return 'bad option'


    # The management of the convolver objet needs to update <preamp.state>
    def set_drc(x, *dummy):
        result = convolver.set_drc(x)
        if result == 'done':
            preamp.state['drc_set'] = x
            # The drc impulse max gain response and its coeff attenuation are
            # taken into account when preamp computes the digital headroom
            drc_headroom = convolver.get_drc_headroom( x )
            preamp.update_drc_headroom( drc_headroom )
        return result


    def set_xo(x, *dummy):
        result = convolver.set_xo(x)
        if result == 'done':
            preamp.state['xo_set'] = x
        return result


    def add_delay(x, *dummy):
        """ Add outputs delay, typically for multiroom listening
        """
        result = convolver.add_delay(float(x))
        if result == 'done':
            preamp.state['extra_delay'] = float(x)
        return result


    def select_source(x, *dummy):
        """ A wrapper to ensure the remote zita-j2n audio sender process
            for remoteXXXX kind of sources
        """
        result = preamp.select_source(x)

        if result == 'done' and 'remote' in x:
            raddr, rport, zport = get_remote_zita_params(x)
            if raddr:
                remote_zita_restart(raddr, rport, zport)

        return result


    def manage_compressor(x, *dummy):

        x = x.split()
        oper = arg = ''
        if x:
            oper = x[0]
            if x[1:]:
                arg = x[1]

        if not oper:
            if not 'compressor' in preamp.state:
                preamp.state["compressor"] = 'off'
            return preamp.state["compressor"]

        # Proceed and get the result
        tmp = cdsp.compressor(oper, arg)

        # Not a valid result
        if type(tmp) == str:
            res = tmp

        # a valid result
        else:
            active     = tmp["active"]
            parameters = tmp["parameters"]

            if active:
                res = parameters["ratio"]
                preamp.state["compressor"] = res

            else:
                res = 'off'
                preamp.state["compressor"] = res

        return res


    def print_help(*dummy):
        return open(f'{UHOME}/pe.audio.sys/doc/peaudiosys.hlp', 'r').read()


    # extract 'add' option for relative changes
    arg, add = analize_arg_add(argstring)

    # COMMAND PROCESSING by parsing the command to his related function:
    try:
        result = {

            'state':            preamp.get_state,
            'status':           preamp.get_state,
            'get_state':        preamp.get_state,
            'get_inputs':       preamp.get_inputs,
            'get_eq':           preamp.get_eq,
            'get_target_sets':  preamp.get_target_sets,
            'get_drc_sets':     convolver.get_drc_sets,
            'get_xo_sets':      convolver.get_xo_sets,

            'input':            select_source,
            'source':           select_source,
            'solo':             preamp.set_solo,
            'mono':             set_mono,
            'midside':          preamp.set_midside,
            'polarity':         preamp.set_polarity,
            'mute':             preamp.set_mute,
            'subsonic':         preamp.set_subsonic,
            'swap_lr':          preamp.swap_lr,
            'lr_swap':          preamp.swap_lr,

            'level':            preamp.set_level,
            'volume':           preamp.set_level,
            'balance':          preamp.set_balance,
            'treble':           preamp.set_treble,
            'bass':             preamp.set_bass,
            'tone_defeat':      preamp.set_tone_defeat,
            'loudness':         preamp.set_equal_loudness,
            'eq_loudness':      preamp.set_equal_loudness,
            'equal_loudness':   preamp.set_equal_loudness,
            'lu_offset':        preamp.set_lu_offset,
            'set_target':       preamp.set_target,

            'set_drc':          set_drc,
            'drc':              set_drc,
            'set_xo':           set_xo,
            'xo':               set_xo,
            'add_delay':        add_delay,

            'compressor':       manage_compressor,

            'convolver':        preamp.switch_convolver,
            'powersave':        preamp.powersave,

            'help':             print_help

            } [ cmd.lower() ] ( arg, add )

        # ************************************
        # ** KEEPING UPDATED THE STATE FILE **
        # ************************************
        if result:
            preamp.save_state()

    except KeyError:
        result = f'(preamp) unknown command: \'{cmd}\''

    except Exception as e:
        result = f'(preamp) {cmd} ERROR: {str(e)}'

    return result
