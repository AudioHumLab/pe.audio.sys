#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

import sys
import os
from   subprocess import Popen, check_output
import json
import numpy as np
from   time import sleep
import threading

import jack_mod     as jack
import brutefir_mod as bf

UHOME = os.path.expanduser("~")
THISDIR = os.path.dirname( os.path.realpath(__file__) )
sys.path.append(f'{UHOME}/pe.audio.sys/share/miscel')
sys.path.append( THISDIR )

from config import  STATE_PATH, CONFIG, EQ_FOLDER, EQ_CURVES, TONE_MEMO_PATH, \
                    LSPK_FOLDER, LDMON_PATH, MAINFOLDER

from miscel import  read_state_from_disk, read_json_from_file, get_peq_in_use, \
                    time_sec2mmss, Fmt, calc_gain

USE_AMIXER = False
try:
    USE_AMIXER = CONFIG["alsamixer"]["use_alsamixer"]
    if USE_AMIXER:
        import alsa
except Exception as e:
    print(f'(core.py) {str(e)}')

ZEROS = np.zeros( EQ_CURVES["freqs"].shape[0] )

# Aux to manage the powersave feature (auto start/stop Brutefir process)
def powersave_loop( convolver_off_driver, convolver_on_driver,
                    end_loop_flag, reset_elapsed_flag ):
    """ Loops forever every 1 sec reading the dBFS level on preamp input.
        If detected signal is below NOISE_FLOOR during MAX_WAIT then stops
        Brutefir. If signal level raises, then resumes Brutefir.

        Events managed here:
        convolver_off_driver:   Will set when no detected signal
        convolver_on_driver:    Will set when detected signal
        end_loop_flag:          Will check on every loop
        reset_elapsed_flag:     Will check and clear, useful when switching
                                to a no signal source to avoid killing brutefir
                                suddenly (see Preamp.select_source#NewSource)
    """


    def read_loudness_monitor():
        # Lets use LU_M (LU Momentary) from .loudness_monitor
        d = read_json_from_file(LDMON_PATH, timeout=1)
        if 'LU_M' in d:
            LU_M = d["LU_M"]
        else:
            LU_M = 0.0
        dBFS = LU_M - 23.0  # LU_M is referred to -23dBFS
        return dBFS


    def loudness_monitor_is_running():
        try:
            check_output('pgrep -f loudness_monitor.py'.split()).decode()
            return True
        except:
            return False


    # Default values:
    NOISE_FLOOR = -70
    MAX_WAIT    =  60
    # CONFIG values overrides:
    if "powersave_noise_floor" in CONFIG:
        NOISE_FLOOR = CONFIG["powersave_noise_floor"]
    if "powersave_minutes" in CONFIG:
        MAX_WAIT = CONFIG["powersave_minutes"] * 60

    # Using a level meter, loudness_monitor.py is preferred,
    # if not available will use level_meter.py
    loud_mon_available = loudness_monitor_is_running()
    if loud_mon_available:
        print( f'(powersave) using \'loudness_monitor.py\'' )
    else:
        # Prepare and start a level_meter.Meter instance
        sys.path.append( f'{MAINFOLDER}/share/audiotools' )
        from level_meter import Meter
        meter = Meter(device='pre_in_loop', mode='peak', bar=False)
        meter.start()
        print( f'(powersave) using \'level_meter.py\'' )

    # Loop forever each 1 sec will check signal level
    print(f'(powersave) running')
    lowSigElapsed = 0
    while True:

        if reset_elapsed_flag.isSet():
            lowSigElapsed = 0
            reset_elapsed_flag.clear()

        # Reading level
        if loud_mon_available:
            dBFS = read_loudness_monitor()
        else:
            dBFS = meter.L

        # Level detected
        if dBFS > NOISE_FLOOR:
            if not bf.is_running():
                print(f'(powersave) signal detected, requesting to restart Brutefir')
                convolver_on_driver.set()
            lowSigElapsed = 0
        else:
            lowSigElapsed +=1

        # No level detected
        if dBFS < NOISE_FLOOR and lowSigElapsed >= MAX_WAIT:
            if bf.is_running():
                print(f'(powersave) low level during {time_sec2mmss(MAX_WAIT, mode="__m__s")}, '
                       'requesting to stop Brutefir' )
                convolver_off_driver.set()

        # Break loop
        if end_loop_flag.isSet():
            break

        sleep(1)


# The Preamp: audio processor, selector, and system state keeper ===============
def init_audio_settings():
    """ Forcing if indicated on config.yml or restoring last state from disk
    """

    def try_init(prop):
        """ Try to set a value defined under CONFIG['on_init'][prop]
            Returns a warning or an empty string
        """
        value = CONFIG["on_init"][prop]

        # Skipping if not defined
        if value is None:
            return ''

        # Manage the special key 'max_level'
        if prop == 'max_level':
            value = min( value, preamp.state["level"] )
            prop = 'level'

        func = {
                'xo':               convolver.set_xo,
                'drc':              convolver.set_drc,
                'input':            preamp.select_source,
                'target':           preamp.set_target,
                'level':            preamp.set_level,
                'muted':            preamp.set_mute,
                'bass':             preamp.set_bass,
                'treble':           preamp.set_treble,
                'balance':          preamp.set_balance,
                'subsonic':         preamp.set_subsonic,
                'equal_loudness':   preamp.set_equal_loudness,
                'lu_offset':        preamp.set_lu_offset,
                'midside':          preamp.set_midside,
                'polarity':         preamp.set_polarity,
                'solo':             preamp.set_solo
                }[prop]

        # Some keys can be formerly named:
        if prop == 'xo':
            state_prop = 'xo_set'
        elif prop == 'drc':
            state_prop = 'drc_set'
        else:
            state_prop = prop

        # Processing
        warning = ''
        if func( value ) == 'done':
            preamp.state[state_prop] = value
            print('(on_init)', prop, value)
        else:
            warning = f'{Fmt.RED}bad {prop}:{value}{Fmt.END}'
            print('(on_init)', warning)
            # Using last state
            value = preamp.state[state_prop]
            if func( value ) != 'done':
                # This should never happen:
                warning = f'{Fmt.RED}{Fmt.BOLD} BAD STATE {prop}:{value}{Fmt.END}'

        return warning


    # temporary Preamp and Convolver instances
    preamp    = Preamp()
    convolver = Convolver()
    warnings  = ''


    # DEFAULTS
    if not 'subsonic' in CONFIG['on_init'] or not CONFIG['on_init']['subsonic']:
        CONFIG['on_init']['subsonic'] = 'off'

    # Iterate over config.on_init:
    for prop in CONFIG['on_init']:
        warning = try_init(prop)
        if warning:
            warnings += f'{warning}, '

    # saving state to disk, then closing tmp instances
    preamp.save_state()
    del(convolver)
    del(preamp)

    if not warnings:
        print( f'{Fmt.BLUE}(core.on_init) done.{Fmt.END}' )
        return 'done'
    else:
        print( f'(core.on_init) {warnings[:-2]}' )
        return warnings[:-2]


def connect_monitors():
    """ Connect source monitors to preamp-loop
    """
    if CONFIG["source_monitors"]:
        for monitor in CONFIG["source_monitors"]:
            jack.connect_bypattern('pre_in_loop', monitor)


class Preamp(object):
    """ attributes:

            state           state dictionary
            inputs          the available inputs dict.
            target_sets     target curves available under the 'eq' folder
            bass_span       available span for tone curves
            treble_span
            gain_max        max authorised gain
            balance_max     max authorised balance

        methods:

            save_state      save state dict to disk

            select_source
            set_level
            set_balance
            set_bass
            set_treble
            set_lu_offset
            set_equal_loudness
            set_target
            set_solo
            set_mute
            set_midside
            swap_lr

            get_state
            get_inputs
            get_target_sets
            get_eq

            convolver       stops or resume Brutefir (energy saving)

    """


    # Preamp INIT
    def __init__(self):

        # The available inputs
        self.inputs = CONFIG["sources"]

        # The state dictionary
        self.state = read_state_from_disk()

        # The jack port of the selected source
        source = self.state["input"]
        if source != 'none':
            jport = CONFIG["sources"][source]["jack_pname"].split(':')[0]
        else:
            jport = ''
        self.state["input_port"] = jport

        # Convoler runs
        self.state["convolver_runs"] = bf.is_running()

        # will add some informative values:
        self.state["loudspeaker"] = CONFIG["loudspeaker"]
        self.state["loudspeaker_ref_SPL"] = CONFIG["refSPL"]
        self.state["fs"] = jack.JCLI.samplerate

        # tone_memo keeps tone values even when tone_defeat is activated
        self.state["tone_defeat"] = False
        self.tone_memo = {}
        self.tone_memo["bass"]    = self.state["bass"]
        self.tone_memo["treble"]  = self.state["treble"]

        # The target curves available under the 'eq' folder
        self.target_sets = self._find_target_sets()

        # The available span for tone curves
        self.bass_span   = int( (EQ_CURVES["bass_mag"].shape[0] - 1) / 2 )
        self.treble_span = int( (EQ_CURVES["treb_mag"].shape[0] - 1) / 2 )

        # Max authorised gain
        self.gain_max    = float(CONFIG["gain_max"])
        # Max authorised balance
        self.balance_max = float(CONFIG["balance_max"])

        # Initiate brutefir input connected ports (used from switch_convolver)
        self.bf_sources = bf.get_in_connections()

        # get swap LR
        self.state["lr_swapped"] = self._check_pre_in_swapped()

        # get JACK stuff
        self.state["jack_buffer"] = jack.JCLI.blocksize
        self.state["jack_device"] = jack.get_device()

        # UPDATE STATE FILE
        self.save_state()


        # INTERNAL

        # The drc impulse max gain response and its coeff attenuation are
        # taken into account when Preamp validates the digital headroom
        self.drc_headroom = 0.0

        # Powersave
        #   State file info
        self.state["powersave"] = False
        #
        #   Powersave loop: breaking flag
        self.ps_end = threading.Event()
        #
        #   Powersave loop:reset elapsed low level detected counter flag
        self.ps_reset_elapsed = threading.Event()
        #
        #   Convolver driving events
        def wait_PS_convolver_off():
            """ Event handler for convolver switch off requests
            """
            while True:
                # waiting ...
                self.ps_convolver_off.wait()
                print(f'(core) Thread \'waits for convolver OFF\' received event')
                self.ps_convolver_off.clear()
                self.switch_convolver('off')
        #
        def wait_PS_convolver_on():
            """ Event handler for convolver switch on requests
            """
            while True:
                # waiting ...
                self.ps_convolver_on.wait()
                print(f'(core) Thread \'waits for convolver ON\' received event')
                self.ps_convolver_on.clear()
                self.switch_convolver('on')
        #
        self.ps_convolver_off = threading.Event()
        self.ps_convolver_on  = threading.Event()
        t1 = threading.Thread( name='waits for convolver OFF',
                               target=wait_PS_convolver_off )
        t2 = threading.Thread( name='waits for convolver ON',
                               target=wait_PS_convolver_on )
        t1.start()
        t2.start()
        self._print_threads()


    # Preamp METHODS:
    # (i) Remember to return some result from any method below.
    #     Also notice that we use *dummy to accommodate the preamp.py parser
    #     mechanism wich always will include two arguments for any Preamp call.

    def _get_pre_in_cables(self):
        """ Get preamp source wiring
        """
        pre_ins = jack.get_ports('pre_in_loop', is_input=True)
        cables = []
        for p in pre_ins:
            try:
                s = jack.get_all_connections(p)[0]
            except:
                s = None
            cables.append( (s, p) )
        return cables


    def _check_pre_in_swapped(self):
        """ Check for crossed channels in preamp source wiring
        """
        cables = self._get_pre_in_cables()
        try:
            res = cables[0][0].name > cables[1][0].name
        except:
            res = False
        return res


    def update_drc_headroom(self, x):
        self.drc_headroom = x
        # This updates the digital gain_headroom in the .state file:
        self._validate( self.state )


    def _find_target_sets(self):
        """ Retrieves the sets of available target curves under the share/eq folder.

                                file name:              returned set name:
            minimal name        'target_mag.dat'        'target'
            a more usual name   'xxxx_target_mag.dat'   'xxxx'

            A 'none' set name is added as default for no target eq to be applied.

            (list of <target names>)
        """

        def extract(x):
            """ Aux to extract a meaningful set name, examples:
                    'xxxx_target_mag.dat'   will return 'xxxx'
                    'target_mag.dat'        will return 'target'
            """

            if x[:6] == 'target':
                return 'target'
            else:
                x = x[:-14]

            # strip trailing unions if used
            for c in ('.', '-', '_'):
                if x[-1] == c:
                    x = x[:-1]

            return x


        result = []

        files = os.listdir( EQ_FOLDER )
        tfiles = [ x for x in files if ('target_mag' in x) or ('target_pha' in x) ]

        for fname in tfiles:
            set_name = extract(fname)
            if not set_name in result:
                result.append( set_name )

        return ['none'] + sorted(result)


    def _calc_eq_curve(self, cname, candidate):
        """ Retrieves the tone or loudness curve
            Tone curves depens on candidate-state bass & treble.
            Loudness compensation curve depens on the configured refSPL.
            (mag, pha: numpy arrays)
        """
        # (i) Former FIRtro curves array files xxx.dat were stored in Matlab way,
        #     so when reading them with numpy.loadtxt() it was needed to transpose
        #     and flipud in order to access to the curves data in a natural way.
        #     Currently the curves are stored in pythonic way, so numpy.loadtxt()
        #     will read directly usable data.

        # Tone eq curves are given [-span...0...-span]
        if cname == 'bass':
            bass_center_idx   = (EQ_CURVES["bass_mag"].shape[0] - 1) // 2
            index             = int(round(candidate["bass"])) + bass_center_idx

        elif cname == 'treb':
            treble_center_idx = (EQ_CURVES["treb_mag"].shape[0] - 1) // 2
            index             = int(round(candidate["treble"])) + treble_center_idx

        # Using the previously detected flat curve index and
        # also limiting as per the eq_loud_ceil boolean inside config.yml
        elif cname == 'loud':

            index_max   = EQ_CURVES["loud_mag"].shape[0] - 1
            index_flat  = CONFIG['refSPL']
            index_min   = 0
            if CONFIG["eq_loud_ceil"]:
                index_max = index_flat

            if candidate["equal_loudness"]:
                index = CONFIG['refSPL'] + candidate["level"]
            else:
                index = index_flat
            index = int(round(index))

            # Clamp index to the available "loudness deepness" curves set
            index = max( min(index, index_max), index_min )


        return EQ_CURVES[f'{cname}_mag'][index], \
               EQ_CURVES[f'{cname}_pha'][index]


    def _calc_eq(self, candidate):
        """ Calculate the eq curves to be applied in the Brutefir EQ module,
            as per the given candidate tone, loudness and target curves
            (mag, pha: numpy arrays)
        """

        # getting loudness and tones curves
        loud_mag, loud_pha = self._calc_eq_curve( 'loud', candidate )
        bass_mag, bass_pha = self._calc_eq_curve( 'bass', candidate )
        treb_mag, treb_pha = self._calc_eq_curve( 'treb', candidate )

        # getting target curve
        target_name = candidate["target"]
        if target_name == 'none':
            targ_mag = ZEROS
            targ_pha = ZEROS
        else:
            if target_name != 'target':     # see doc string on find_target_sets()
                target_name += '_target'
            targ_mag = np.loadtxt( f'{EQ_FOLDER}/{target_name}_mag.dat' )
            targ_pha = np.loadtxt( f'{EQ_FOLDER}/{target_name}_pha.dat' )

        # Compose
        eq_mag = targ_mag + loud_mag * candidate["equal_loudness"] \
                 + bass_mag + treb_mag

        if CONFIG["bfeq_linear_phase"]:
            eq_pha = ZEROS
        else:
            eq_pha = targ_pha + loud_pha * candidate["equal_loudness"] \
                     + bass_pha + treb_pha

        return eq_mag, eq_pha


    def _print_threads(self):
        """ Console info about active threads
        """
        print( f'(core) {threading.activeCount()} threads:' )
        for i, t in enumerate(threading.enumerate()):
            print(' ', i, t.name)
        return 'done'


    def powersave(self, mode, *dummy):
        """ on:  Initiate a threaded powersave_loop signal monitor job.
            off: Flags to break the loop then will termitate the threaded job.
        """

        if mode == 'on':
            ps_job = threading.Thread( name='powersave LOOP',
                                       target=powersave_loop,
                                       args=( self.ps_convolver_off,
                                              self.ps_convolver_on,
                                              self.ps_end,
                                              self.ps_reset_elapsed ) )
            ps_job.start()
            self.state["powersave"] = True

        elif mode == 'off':
            self.ps_end.set()
            # To ensure that powersave_loop 1 sec cicle can detect
            # the ps_end flag, then terminate itself.
            sleep(2)
            self.ps_end.clear()
            self.state["powersave"] = False

        else:
            return 'bad option'

        self._print_threads()

        return 'done'


    def switch_convolver( self, mode, *dummy ):

        result = 'nothing done'

        if mode == 'off':

            if bf.is_running():
                self.bf_sources = bf.get_in_connections()
                # Allows other Brutefir, kills just our.
                Popen(f'pkill -f  "brutefir brutefir_config"', shell=True)
                # Brutefir 1.0m process is 'brutefir.real'
                Popen(f'pkill -f  "brutefir.real brutefir_config"', shell=True)
                sleep(2)
                print(f'{Fmt.BLUE}{Fmt.BOLD}(core) STOPPING BRUTEFIR (!){Fmt.END}')
                result = 'done'

        elif mode == 'on':

            if not bf.is_running():

                # This avoids that powersave loop kills Brutefir
                self.ps_reset_elapsed.set()

                result = bf.restart_and_reconnect(bf_sources=self.bf_sources,
                                                  delay=self.state["extra_delay"] )
                if result == 'done':
                    print(f'{Fmt.BLUE}{Fmt.BOLD}(core) BRUTEFIR RESUMED{Fmt.END}')
                    self._validate( self.state ) # this includes mute
                    c = Convolver()
                    c.set_xo ( self.state["xo_set"]  )
                    c.set_drc( self.state["drc_set"] )
                    del( c )
                else:
                    result = f'PANIC: {result}'

        else:
            result = 'bad option'

        self.save_state()

        return result


    def _validate( self, candidate ):
        """ Validates that the given 'candidate' (new state dictionary)
            does not exceed gain limits

            (i) USE_AMIXER (ALSA Mixer)

                Brutefir will not compute the level value,
                it will be applied at the sound card output mixer.

        """
        gmax            = self.gain_max
        gain            = calc_gain( candidate )

        # (!) candidate2 leaves candidate tone values untouched
        #     in case of tone defeat control activated
        candidate2 = candidate.copy()

        if self.state["tone_defeat"]:
            candidate2["bass"] = 0
            candidate2["treble"] = 0

        eq_mag, eq_pha  = self._calc_eq( candidate2 )

        bal             = candidate["balance"]

        headroom = gmax - gain - np.max(eq_mag) - np.abs(bal / 2.0) + self.drc_headroom
        # DEBUG
        #print('gmax', 'gain', 'max_eq', 'bal/2', 'drc_hr', '=', 'headroom')
        #print(gmax,  -gain, -np.max(eq_mag), - np.abs(bal / 2.0), + self.drc_headroom, '=', headroom)

        # (i)
        # 'config.yml' SOURCE's GAIN are set arbitrarily at the USER's OWN RISK,
        # so we exclude it from the headroom calculation.
        # So although 'gmax: 0.0' (this is digital domain alowed gain),
        # if a source had gain: 6.0, the real 'gain' on Brutefir level stage
        # can be up to +6.0 dB because of this consideration.
        if candidate["input"] != 'none':
            try:
                input_gain = float( CONFIG["sources"][candidate["input"]]["gain"] )
            except:
                input_gain = 0.0
        else:
            input_gain = 0.0

        headroom += input_gain

        # APPROVED
        if headroom >= 0:

            if not USE_AMIXER:
                bf.set_gains( candidate )

            else:

                amixer_result = alsa.set_amixer_gain( candidate["level"] )

                if amixer_result == 'done':
                    bf.set_gains( candidate, nolevel=True )

                else:
                    # If for some reason alsa mixer has not adjusted the wanted dB,
                    # it will return some info ended by the amount of pending dB
                    # to be applied. Example:
                    #   "clamped, dB pending: 3.0"
                    dBpending = round( float(amixer_result.split()[-1]), 1)
                    bf.set_gains( candidate, nolevel=True, dBextra=dBpending )

            bf.set_eq( eq_mag, eq_pha )
            self.state = candidate
            self.state["gain_headroom"] = round(headroom, 1)
            self.save_tone_memo()
            return 'done'

        # REFUSED
        else:
            return 'not enough headroom'


    def save_state(self):
        self.state["convolver_runs"] = bf.is_running()
        with open(STATE_PATH, 'w') as f:
            f.write( json.dumps( self.state ) )


    def save_tone_memo(self):
        self.tone_memo["bass"]   = self.state["bass"]
        self.tone_memo["treble"] = self.state["treble"]
        with open(TONE_MEMO_PATH, 'w') as f:
            f.write( json.dumps( self.tone_memo ) )


    def get_state(self, *dummy):
        return self.state


    def get_target_sets(self, *dummy):
        return self.target_sets


    def set_level(self, value, relative=False):
        candidate = self.state.copy()
        if relative:
            candidate["level"] += round(float(value), 2)
        else:
            candidate["level"] =  round(float(value), 2)
        return self._validate( candidate )


    def set_balance(self, value, relative=False):
        candidate = self.state.copy()
        if relative:
            candidate["balance"] += round(float(value), 2)
        else:
            candidate["balance"] =  round(float(value), 2)
        if abs(candidate["balance"]) <= self.balance_max:
            return self._validate( candidate )
        else:
            return 'too much'


    def set_bass(self, value, relative=False):
        candidate = self.state.copy()
        if relative:
            candidate["bass"] += round(float(value), 2)
        else:
            candidate["bass"] =  round(float(value), 2)
        if abs(candidate["bass"]) <= self.bass_span:
            return self._validate( candidate )
        else:
            return 'too much'


    def set_treble(self, value, relative=False):
        candidate = self.state.copy()
        if relative:
            candidate["treble"] += round(float(value), 2)
        else:
            candidate["treble"] =  round(float(value), 2)
        if abs(candidate["treble"]) <= self.treble_span:
            return self._validate( candidate )
        else:
            return 'too much'


    def set_tone_defeat(self, value, *dummy):

        if type(value) == bool:
            value = str(value)

        try:
            if value.lower() in ('false', 'true', 'off', 'on', 'toggle'):
                value = { 'false': False, 'off': False,
                          'true' : True,  'on' : True,
                          'toggle': {False: True, True: False}
                                                 [ self.state["tone_defeat"] ]
                        } [ value.lower() ]
                self.state["tone_defeat"] = value
                return self._validate( self.state )
            else:
                return 'syntax error'

        except Exception as e:
            return f'internal error: {str(e)}'


    def set_lu_offset(self, value, relative=False):
        candidate = self.state.copy()
        # this try if intended just to validate the given value
        try:
            if relative:
                candidate["lu_offset"] += round(float(value), 2)
            else:
                candidate["lu_offset"] =  round(float(value), 2)
            return self._validate( candidate )
        except:
            return 'bad value'


    def set_equal_loudness(self, value, *dummy):
        candidate = self.state.copy()
        if type(value) == bool:
            value = str(value)
        try:
            value = { 'on': True , 'off': False,
                      'true': True, 'false': False,
                      'toggle': {True: False, False: True
                                 }[self.state["equal_loudness"]]
                     } [ value.lower() ]
            candidate["equal_loudness"] = value
            return self._validate( candidate )
        except:
            return 'bad option'


    def set_target(self, value, *dummy):
        candidate = self.state.copy()
        if value in self.target_sets:
            candidate["target"] = value
            return self._validate( candidate )
        else:
            return f'target \'{value}\' not available'


    def set_solo(self, value, *dummy):
        if value.lower() in ('off', 'l', 'left', 'r', 'right'):
            if value.lower() == 'left':
                value = 'l'
            if value.lower() == 'right':
                value = 'r'
            self.state["solo"] = value.lower()
            if not USE_AMIXER:
                bf.set_gains( self.state )
            else:
                bf.set_gains( self.state, nolevel=True )
            return 'done'
        else:
            return 'bad option'


    def set_polarity(self, value, *dummy):
        if value in ('+', '-', '++', '--', '+-', '-+'):
            self.state["polarity"] = value.lower()
            if not USE_AMIXER:
                bf.set_gains( self.state )
            else:
                bf.set_gains( self.state, nolevel=True )
            return 'done'
        else:
            return 'bad option'


    def set_mute(self, value, *dummy):
        if type(value) == bool:
            value = str(value)
        try:
            if value.lower() in ('false', 'true', 'off', 'on', 'toggle'):
                value = { 'false': False, 'off': False,
                          'true' : True,  'on' : True,
                          'toggle': {False: True, True: False}
                                                 [ self.state["muted"] ]
                        } [ value.lower() ]
                self.state["muted"] = value
                if not USE_AMIXER:
                    bf.set_gains( self.state )
                else:
                    bf.set_gains( self.state, nolevel=True )
                return 'done'
        except:
            return 'bad option'


    def set_midside(self, value, *dummy):
        if value.lower() in ( 'mid', 'side', 'off' ):
            self.state["midside"] = value.lower()
            if not USE_AMIXER:
                bf.set_gains( self.state )
            else:
                bf.set_gains( self.state, nolevel=True )
        else:
            return 'bad option'
        return 'done'


    def swap_lr(self, *dummy):
        """ Swap L <> R channels at preamp input
            Useful for some cases as swapped film channels when downmixed
        """

        def swap(cables):
            jack.connect(cables[0][0], cables[1][1])
            jack.connect(cables[1][0], cables[0][1])


        try:
            cables = self._get_pre_in_cables()
            jack.clear_preamp()
            swap( cables )
            self.state["lr_swapped"] = self._check_pre_in_swapped()
            return 'done'

        except Exception as e:
            return f'cannot swap preamp inputs'


    def set_subsonic(self, value, *dummy):

        if value.lower() in ('off', 'mp', 'lp', 'toggle', 'rotate'):

            nvalue = {  'off':  'off',
                        'mp':   'mp',
                        'lp':   'lp',
                        'toggle': { 'off':  'mp',
                                    'mp':   'off',
                                    'lp':   'off'
                                  }[ self.state["subsonic"] ],
                        'rotate': { 'off':  'mp',
                                    'mp':   'lp',
                                    'lp':   'off'
                                  }[ self.state["subsonic"] ]
                     } [ value.lower() ]

            result = bf.set_subsonic( nvalue )

            if result == 'done':
                self.state["subsonic"] = nvalue

            else:
                self.state["subsonic"] = 'off'

            return result

        else:
            return 'bad option'


    def get_eq(self, *dummy):
        freq, mag , pha = bf.read_eq()
        return { 'band': freq.tolist(), 'mag': mag.tolist(),
                                        'pha': pha.tolist() }


    def select_source(self, source, *dummy):

        def try_select(source):
            """ this is the source selector """
            w = '' # warnings

            # clearing 'preamp' connections
            jack.clear_preamp()

            # connecting the new SOURCE to PREAMP input
            # (i) Special case 'remoteXXX' source name can have a ':port' suffix
            jport = CONFIG["sources"][source]["jack_pname"].split(':')[0]
            res = jack.connect_bypattern(jport, 'pre_in')

            if res == 'ordered':
                self.state["input_port"] = jport
            else:
                w += res


            # Trying to set the desired xo and drc for this source
            c = Convolver()
            try:
                xo = CONFIG["sources"][source]["xo"]
                if xo and c.set_xo( xo ) == 'done':
                    self.state["xo_set"] = xo
                elif xo:
                    if w:
                        w += '; '
                    w += f'\'xo:{xo}\' in \'{source}\' is not valid'
            except:
                pass
            try:
                drc = CONFIG["sources"][source]["drc"]
                if drc and c.set_drc( drc ) == 'done':
                    self.state["drc_set"] = drc
                elif drc:
                    if w:
                        w += '; '
                    w += f'\'drc:{drc}\' in \'{source}\' is not valid'
            except:
                pass
            del(c)

            # end of trying to select the source
            if not w:
                return 'done'
            else:
                return w # warnings

        def on_change_input_behavior(candidate):
            try:
                for option, value in CONFIG["on_change_input"].items():
                    if value is not None:
                        candidate[option] = value
            except:
                print('(core) config.yml: missing \'on_change_input\' options')
            return candidate

        result = 'nothing done'

        # Source = 'none'
        if source == 'none':
            jack.clear_preamp()
            self.state["input_port"] = ''
            self.state["input"] = source
            result = 'done'

        # Bad source
        elif source not in self.inputs:
            result = f'unknown source \'{source}\''

        # New source
        else:
            result = try_select(source)
            self.state["input"] = source
            candidate = self.state.copy()
            # Global audio settings on change input, but ensure the convolver
            # is running before applying audio settings.
            if not self.state["convolver_runs"]:
                self.ps_reset_elapsed.set()
                self.switch_convolver('on')
            candidate = on_change_input_behavior(candidate)
            # Some source specific audio settings overrides global settings
            # LU offset
            if 'lu_offset' in CONFIG["sources"][source]:
                candidate["lu_offset"] = \
                               CONFIG["sources"][source]["lu_offset"]
            # Target eq curve
            if 'target' in CONFIG["sources"][source]:
                candidate["target"] = CONFIG["sources"][source]["target"]
            self._validate( candidate )

        return result


    def get_inputs(self, *dummy):
        return [ x for x in self.inputs.keys() ]


# The Convolver: drc and xo Brutefir stages management =========================
class Convolver(object):
    """ attributes:

            drc_coeffs      list of pcm FIRs for DRC
            xo_coeffs       list of pcm FIRs for XOVER
            drc_sets        sets of FIRs for DRC
            xo_sets         sets of FIRs for XOVER
            lspk_ways       filtering stages (loudspeaker ways)

        methods:

            set_drc
            set_xo

            get_drc_sets
            get_xo_sets
    """


    def __init__(self):

        # DRC pcm files must be named:
        #    drc.X.DRCSETNAME.pcm
        #
        #       where X must be L | R
        #
        # XO pcm files must be named:
        #   xo.XX[.C].XOSETNAME.pcm
        #
        #       where XX must be:     fr | lo | mi | hi | sw
        #       and channel C can be:  L | R  (optional)
        #
        #       Using C allows to have dedicated FIR per channel

        files   = os.listdir(LSPK_FOLDER)
        coeffs  = [ x.replace('.pcm', '') for x in files ]
        self.drc_coeffs = [ x for x in coeffs if x[:4] == 'drc.'  ]
        self.xo_coeffs  = [ x for x in coeffs if x[:3] == 'xo.'   ]
        #print('\nxo_coeffs:', xo_coeffs) # debug

        # The available DRC sets
        self.drc_sets = []
        for drc_coeff in self.drc_coeffs:
            drcSetName = drc_coeff[6:]
            if drcSetName not in self.drc_sets:
                self.drc_sets.append( drcSetName )

        # The available XO sets, i.e the last part of a xo_coeff
        self.xo_sets = []
        for xo_coeff in self.xo_coeffs:
            xoSetName = xo_coeff.split('.')[-1]
            if xoSetName not in self.xo_sets:
                self.xo_sets.append( xoSetName )

        # lspk_ways are the XO filter stages definded inside brutefir_config
        # 'f.WW.C' where WW:fr|lo|mi|hi|sw and C:L|R
        self.lspk_ways = bf.get_config()['lspk_ways']

        # debug
        #print('drc_sets:', self.drc_sets)
        #print('xo_sets:', self.xo_sets)
        #print('lspk_ways:', self.lspk_ways)

    # Bellow we use *dummy to accommodate the preamp.py parser mechanism
    # wich always will include two arguments for any function call.


    def get_drc_headroom(self, drc_set):
        return bf.get_drc_headroom(drc_set)


    def set_drc(self, drc, *dummy):
        if drc in self.drc_sets or drc == 'none':
            bf.set_drc( drc )
            return 'done'
        else:
            return f'drc set \'{drc}\' not available'


    def set_xo(self, xo_set, *dummy):
        if xo_set in self.xo_sets:
            bf.set_xo( self.lspk_ways, self.xo_coeffs, xo_set )
            return 'done'
        else:
            return f'xo set \'{xo_set}\' not available'


    def add_delay(self, ms, *dummy):
        return bf.add_delay(ms)


    def get_drc_sets(self, *dummy):
        return self.drc_sets


    def get_xo_sets(self, *dummy):
        return self.xo_sets

