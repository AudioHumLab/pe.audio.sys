#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

"""
    This module provides the system constants and configuration
    parameters that other modules need to function:

        CONFIG          The main set of system parameters
                        from config/config.yml

        EQ_CURVES       The set of curves to be used by the
                        EQ stage in Brutefir for tone and
                        loudness contour compensation

        xxx_FOLDER      Common usage folder paths

        xxx_PATH        Common usage file paths

"""
import  yaml
from    numpy import loadtxt as np_loadtxt
import  os
import  sys
from    getpass import getuser

USER                = getuser()
UHOME               = os.path.expanduser("~")
MAINFOLDER          = f'{UHOME}/pe.audio.sys'
CONFIG              = {'use_compressor': False}
LOUDSPEAKER         = ''
EQ_CURVES           = {}
LSPK_FOLDER         = f'{MAINFOLDER}/loudspeakers/{LOUDSPEAKER}'
BFCFG_PATH          = f'{LSPK_FOLDER}/brutefir_config'

BFDEF_PATH          = f'{UHOME}/.brutefir_defaults'
STATE_PATH          = f'{MAINFOLDER}/.state'
TONE_MEMO_PATH      = f'{MAINFOLDER}/.tone_memo'    # a tone_defeat helper
LOG_FOLDER          = f'{MAINFOLDER}/log'
EQ_FOLDER           = f'{MAINFOLDER}/share/eq'

MACROS_FOLDER       = f'{MAINFOLDER}/macros'
LDCTRL_PATH         = f'{MAINFOLDER}/.loudness_control'
LDMON_PATH          = f'{MAINFOLDER}/.loudness_monitor'
AUX_INFO_PATH       = f'{MAINFOLDER}/.aux_info'
AMP_STATE_PATH      = f'{UHOME}/.amplifier'

PLAYER_META_PATH    = f'{MAINFOLDER}/.player_metadata'
PLAYER_METATEMPLATE = { 'player':       '',
                        'time_pos':     '',
                        'time_tot':     '',
                        'bitrate':      '',
                        'format':       '-:-:2',
                        'file':         '',
                        'artist':       '',
                        'album':        '',
                        'title':        '',
                        'track_num':    '',
                        'tracks_tot':   ''
                      }


CDDA_MUSICBRAINZ_PATH = f'{MAINFOLDER}/.cdda_musicbrainz'
CDDA_META_PATH        = f'{MAINFOLDER}/.cdda_metadata'
CDDA_META_TEMPLATE    = { 'discid': '', 'artist': '', 'album': '',
                          'tracks': { }
                        }


def _init():
    """ Autoexec on loading this module
    """

    global CONFIG, LOUDSPEAKER, EQ_CURVES, LSPK_FOLDER, BFCFG_PATH


    def find_eq_curves():
        """ Scans share/eq/ and try to collect the whole set of EQ curves
            needed for the EQ stage in Brutefir (tone and loudness countour)
            (void)
        """
        eq_files = os.listdir(EQ_FOLDER)

        # file names ( 2x loud + 4x tones + freq = total 7 curves)
        fnames = (  'loudness_mag.dat', 'bass_mag.dat', 'treble_mag.dat',
                    'loudness_pha.dat', 'bass_pha.dat', 'treble_pha.dat',
                    'freq.dat' )

        # map dict to get the curve name from the file name
        cnames = {  'loudness_mag.dat'  : 'loud_mag',
                    'bass_mag.dat'      : 'bass_mag',
                    'treble_mag.dat'    : 'treb_mag',
                    'loudness_pha.dat'  : 'loud_pha',
                    'bass_pha.dat'      : 'bass_pha',
                    'treble_pha.dat'    : 'treb_pha',
                    'freq.dat'          : 'freqs'     }

        pendings = len(fnames)  # 7 curves
        for fname in fnames:

            # Only one file named as <fname> must be found

            if 'loudness' in fname:
                prefixedfname = f'ref_{CONFIG["refSPL"]}_{fname}'
                files = [ x for x in eq_files if prefixedfname in x]
            else:
                files = [ x for x in eq_files if fname in x]

            if files:

                if len (files) == 1:
                    EQ_CURVES[ cnames[fname] ] = \
                             np_loadtxt( f'{EQ_FOLDER}/{files[0]}' )
                    pendings -= 1
                else:
                    print(f'(config) too much \'...{fname}\' '
                           'files under share/eq/')
            else:
                print(f'(config) ERROR finding a \'...{fname}\' '
                       'file under share/eq/')

        #if not pendings:
        if pendings == 0:
            return EQ_CURVES
        else:
            return {}


    try:
        with open(f'{MAINFOLDER}/config/config.yml', 'r') as f:
            CONFIG = yaml.safe_load(f)
    except:
        print(f'(config) ERROR reading \'config.yml\'')
        sys.exit()

    LOUDSPEAKER         = CONFIG['loudspeaker']
    LSPK_FOLDER         = f'{MAINFOLDER}/loudspeakers/{LOUDSPEAKER}'
    BFCFG_PATH          = f'{LSPK_FOLDER}/brutefir_config'

    EQ_CURVES = find_eq_curves()
    if not EQ_CURVES:
        print( '(config) ERROR loading EQ_CURVES from share/eq/' )
        sys.exit()

    # cd-rom device
    if not 'cdrom_device' in CONFIG or not CONFIG["cdrom_device"]:
        CONFIG["cdrom_device"] = '/dev/cdrom'


# AUTOEXEC
_init()
