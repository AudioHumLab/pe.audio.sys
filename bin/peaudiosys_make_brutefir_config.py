#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

"""
    Makes a pe.audio.sys Brutefir config file

    Usage:

     peaudiosys_make_brutefir_config.py <YOUR_LSPK> [ options ]

        -nodumpeq     Disables dumping rendering eq logic

        -force        Force to overwrite brutefir_config

        -p=N          Set listen port (default 3000)

    See `brutefir_config.yml` details in loudspeakers/examples
"""

import pathlib
import yaml
import sys
import os
from subprocess import call

UHOME = os.path.expanduser("~")

EQFOLDER = f'{UHOME}/pe.audio.sys/share/eq'
FREQPATH = f'{EQFOLDER}/freq.dat'
PORT = 3000

EQ_CLI = \
f'''
# THE EQ & CLI MODULES
logic:

# The Command Line Interface server TCP port
"cli" {{ port: PORT; }},

# The eq module provides a filter coeff to render a run-time EQ.
# (i) Bands here must match with the ones in your xxxxfreq.dat file.
"eq" {{
    debug_dump_filter: "/tmp/brutefir-rendered-%d";
    {{
        coeff: "c.eq";

        bands:
BANDS
    }};
}};

'''

EQ_BANDS = """
            10, 11.2, 12.5, 14, 16, 18, 20, 22.4, 25, 28, 31.5,
            35.5, 40, 45, 50, 56, 63, 71, 80, 90, 100, 112,
            125, 140, 160, 180, 200, 224, 250, 280, 315, 355,
            400, 450, 500, 560, 630, 710, 800, 900, 1000,
            1120, 1250, 1400, 1600, 1800, 2000, 2240, 2500,
            2800, 3150, 3550, 4000, 4500, 5000, 5600, 6300,
            7100, 8000, 9000, 10000, 11200, 12500, 14000, 16000,
            18000, 20000;
"""

GENERAL_SETTINGS = \
'''
# GENERAL SETTINGS

convolver_config:  "~/.brutefir_convolver_FS";
sampling_rate:      FS;
filter_length:      FLENSTR;
float_bits:         32;
overflow_warnings:  true;
allow_poll_mode:    false;
monitor_rate:       true;
powersave:          -80;
lock_memory:        true;
show_progress:      false;

'''

IO = \
'''
# I/O

input "in.L", "in.R" {
    # does not connect inputs in jack:
    device:   "jack" { clientname: "brutefir";
                       ports: ""/"in.L", ""/"in.R"; };
    sample:   "AUTO";
    channels: 2/0,1;
};

output OUTPUTS_LIST {
    # hardwire to Jack sound card:
    device: "jack" { ports:
PORTS_MAP;
    };
    sample:   "AUTO";
    channels: CHANNELS_LIST;
    maxdelay: MAXDELAY; # about 500 ms for multiroom compensation
    dither:   DITHER;
    delay:    DELAY_LIST
};

'''

COEFF_EQ = \
"""
# COEFFs for EQ & LOUDNESS
# 1 block length is enough because smooth eq curves

coeff "c.eq" {
    filename: "dirac pulse";
    shared_mem: true;
    blocks: 1;
};

"""

COEFF_SUBSONIC = \
"""
# COEFFs for SUBSONIC
# (i) If partitioned <filter_length>, set <blocks> to cover
#     the 4096 taps from the subsonic.xx.pcm files

coeff "subsonic.mp" {
    filename:    "SUBSONIC_MP";
    format:      "FLOAT_LE";
    shared_mem:  false;
    attenuation: 0;
    blocks:      BLOCKS;
};

coeff "subsonic.lp" {
    filename:    "SUBSONIC_LP";
    format:      "FLOAT_LE";
    shared_mem:  false;
    attenuation: 0;
    blocks:      BLOCKS;
};

"""

COEFF_DRC_HEADER = \
'''
# COEFFs for DRC
# PCMs found under the loudspeaker folder
'''

COEFF_DRC = \
'''
coeff "drc.C.NAME" {
    filename:    "drc.C.NAME.pcm";
    format:      "FLOAT_LE";
    shared_mem:  false;
    attenuation: ATTEN;
};

'''

COEFF_XO_HEADER = \
'''
# COEFFs for XO
# PCMs found under the loudspeaker folder
'''

COEFF_XO = \
'''
coeff "xo.XONAME" {
    filename:    "xo.XONAME.pcm";
    format:      "FLOAT_LE";
    shared_mem:  false;
    attenuation: 0;
};

'''

FILTERS_LEV_EQ_DRC = \
'''
# CONVOLVER:  LEVEL filter
# Not a filter just for level and channel routing purposes
# (i) Initial 50 dB atten for a safe startup

filter "f.lev.L" {
    from_inputs:  "in.L"/50.0/1, "in.R"//0;
    to_filters:   "f.eq.L";
    coeff:        -1;
};

filter "f.lev.R" {
    from_inputs:  "in.L"//0, "in.R"/50.0/1;
    to_filters:   "f.eq.R";
    coeff:        -1;
};


# CONVOLVER:  EQ filters

filter "f.eq.L" {
    from_filters: "f.lev.L";
    to_filters:   "f.drc.L";
    coeff:        "c.eq";
};

filter "f.eq.R" {
    from_filters: "f.lev.R";
    to_filters:   "f.drc.R";
    coeff:        "c.eq";
};

# CONVOLVER: DRC filters

filter "f.drc.L" {
    from_filters: "f.eq.L";
    to_filters:   LFILTERS;
    coeff:        -1;
};

filter "f.drc.R" {
    from_filters: "f.eq.R";
    to_filters:   RFILTERS;
    coeff:        -1;
};

'''

FILTERS_HEADER = \
'''
# CONVOLVER: XOVER filters
'''

FILTER_STEREO = \
'''
filter "f.WAY.CH" {
    from_filters: "f.drc.CH";
    to_outputs:   "WAY.CH"/ATTEN/POL;
    coeff:        "xo.WAY.mp";
};
'''

FILTER_SUB = \
'''
filter "f.sw" {
    from_filters: "f.drc.L"/3.0, "f.drc.R"/3.0;
    to_outputs:   "sw"/ATTEN/POL;
    coeff:        "xo.sw.mp";
};
'''


def update_eq_bands():
    """ get freqs from the share/eq folder
    """

    global EQ_BANDS

    try:
        with open(FREQPATH, 'r') as f:
            tmp = f.read()

        freqs = [round(float(f),3) for f in tmp.split() if f]
        EQ_BANDS = make_bands_str(freqs)
        print(f'(i) Using eq bands from: {FREQPATH}\n')

    except Exception as e:
        print(f'(!) ERROR reading: {FREQPATH}, using predefined eq R20 bands.\n')


def make_bands_str(freqs):

    maxlen = 9

    lines = '\n'
    i = 0
    while True:
        line = [ x for x in freqs[i: i + maxlen] ]
        line = ', '.join( [ str(x).replace('.0', '') for x in line ] )
        if line:
            line = ' ' * 12 + line  + ',\n'
            lines += line
        else:
            break
        i += maxlen

    return lines[:-2] + ';\n'


def do_GENERAL_SETTINGS():

    global FLENSTR

    FLENSTR = str(CONFIG["partition_size"])
    numpa    = CONFIG["num_partitions"]
    if numpa > 1:
        FLENSTR += f',{numpa}'

    tmp = GENERAL_SETTINGS
    tmp = tmp.replace('FS', str(FS))
    tmp = tmp.replace('FLENSTR', FLENSTR)
    return tmp


def do_IO():

    def ms2samples(ms):
        return int( round(ms * FS / 1000))


    if not CONFIG["dither"] in (True, False):
        print('ERROR: Bad dither must be true or false')
        sys.exit()

    IO_tmp  = IO.replace('DITHER', 'true' if  CONFIG["dither"] else 'false')

    outs_list   = ''
    ports_map   = ''

    void_count = 0
    for out, params in CONFIG["outputs"].items():
        if not params["bflabel"]:
            void_count += 1
            params["bflabel"] = f'void_{void_count}'
        outs_list += f'"{params["bflabel"]}", '
        if not 'void_' in params["bflabel"]:
            ports_map += f'        "system:playback_{out}"/"{params["bflabel"]}",\n'
        else:
            ports_map += f'        ""/"{params["bflabel"]}",\n'

    outs_list = outs_list.rstrip()[:-1]
    ports_map = ports_map.rstrip()[:-1]

    IO_tmp = IO_tmp.replace('OUTPUTS_LIST', outs_list)
    IO_tmp = IO_tmp.replace('PORTS_MAP',    ports_map)

    chann_list = [ str(c - 1) for c in CONFIG["outputs"].keys() ]
    chann_list = f'{len(chann_list)}/{",".join( chann_list )}'

    global DELAY_LIST

    delays_ms      = [ CONFIG["outputs"][o]["delay"] for o in CONFIG["outputs"].keys() ]
    delays_samples = [ ms2samples(d) for d in delays_ms ]

    delays_ms      = [ str(d) for d in delays_ms ]
    delays_samples = [ str(d) for d in delays_samples ]

    DELAY_LIST  = ','.join(delays_samples) + '; # ms: ' + ', '.join(delays_ms)

    IO_tmp = IO_tmp.replace('CHANNELS_LIST', chann_list)
    IO_tmp = IO_tmp.replace('DELAY_LIST',    DELAY_LIST)
    IO_tmp = IO_tmp.replace('MAXDELAY', str(int(FS / 2)))

    return IO_tmp


def do_DRC_COEFFS():

    def get_atten(drc):
        val = CONFIG["drc_flat_region_dB"][drc]
        if val:
            atten = round( float(val), 1)
        else:
            atten = 0.0
        return atten


    tmp = COEFF_DRC_HEADER

    drc_files = [ f for f in LSPKFILES if f.startswith('drc.') ]

    if not drc_files:
        return tmp

    drc_sets = set( [ f.replace('.pcm', '').split('.')[-1] for f in drc_files ] )

    for drc in CONFIG["drc_flat_region_dB"]:
        atten = get_atten(drc)

        for drc_set in drc_sets:
            if drc in drc_set:

                tmp += COEFF_DRC.replace('C.NAME', f'L.{drc_set}').replace('ATTEN', str(atten))
                tmp += COEFF_DRC.replace('C.NAME', f'R.{drc_set}').replace('ATTEN', str(atten))

    return tmp


def do_XO_COEFFS():
    ''' COEFF_XO:

            coeff "xo.XONAME" {
                filename:    "xo.XONAME.pcm";
                format:      "FLOAT_LE";
                shared_mem:  false;
                attenuation: 0;
            };
    '''
    global NO_FR_XO     # No Full Range Xover flag for later filter definition

    NO_FR_XO = False

    xo_files = [ f for f in LSPKFILES if f.startswith('xo.') ]

    # eg: hi.mp, lo.mp, sw.mp, hi.lp, lo.lp, sw.lp ...
    xo_fsets = [ f.replace('xo.', '').replace('.pcm', '') for f in xo_files ]

    # eg: hi, lo, sw
    xo_fways = set( [ x.split('.')[0] for x in xo_fsets ] )

    tmp = COEFF_XO_HEADER

    for _, params in CONFIG["outputs"].items():

        bf_way_ch = params["bflabel"]  # eg: hi.L, low.L, sw ...
        bf_way = bf_way_ch.split('.')[0]  #     hi, lo, sw

        if 'void_' in bf_way_ch:
            continue

        if bf_way in xo_fways:

            for xo_fset in xo_fsets:
                if bf_way == xo_fset.split('.')[0]:
                    if not xo_fset in tmp:
                        tmp += COEFF_XO.replace('XONAME', xo_fset)

        # We can define full range ways without xover pcm
        elif bf_way == 'fr':
            NO_FR_XO = True
            continue

        else:
            raise Exception(f'PCM coeff not found for {bf_way_ch}')

    return tmp


def do_FILTERS_LEV_EQ_DRC():

    tmp = FILTERS_LEV_EQ_DRC;
    lfilters = ''
    rfilters = ''

    for _, params in CONFIG["outputs"].items():

        way_ch = params["bflabel"]

        if 'void_' in way_ch:
            continue

        if way_ch.endswith('.L'):
            lfilters += f'"f.{way_ch}", '
        elif way_ch.endswith('.R'):
            rfilters += f'"f.{way_ch}", '
        else:
            lfilters += f'"f.{way_ch}", '
            rfilters += f'"f.{way_ch}", '

    tmp = tmp.replace( 'LFILTERS', lfilters[:-2] )
    tmp = tmp.replace( 'RFILTERS', rfilters[:-2] )

    return tmp


def do_FILTERS():
    '''
        filter "f.WAY.CH" {
            from_filters: "f.drc.CH";
            to_outputs:   "WAY.CH"/ATTEN/POL;
            coeff:        "xo.WAY.mp";
        };
    '''

    def pol2int(p):
        p = {   '+' :   1,
                '1' :   1,
                 1  :   1,
                '-' :  -1,
               '-1' :  -1,
                -1  :  -1
              }[p]
        return p


    tmp = FILTERS_HEADER

    for _, params in CONFIG["outputs"].items():

        way_ch = params["bflabel"]

        if not 'void_' in way_ch:

            # Regular stereo way
            if not 'sw' in way_ch:

                way, ch = way_ch.split('.')
                tmp += FILTER_STEREO.replace('CH', ch).replace('WAY', way)

                if way == 'fr' and NO_FR_XO:
                    tmp = tmp.replace('"xo.fr.mp"', '-1')

            # Subwoofer mixed way
            else:
                tmp += FILTER_SUB

            # Output Attenuation and Polarity
            att = params["gain"] * -1 if params["gain"] else 0.0
            pol = params["polarity"]

            tmp = tmp.replace( 'ATTEN', str(att)).replace('POL', str(pol2int(pol)) )


    return tmp


def notice_delay2ms():
    """ Translates samples to ms
    """
    delays = [ int(x) for x in DELAY_LIST.split(',') ]
    notice = '# samples ~ xxx ms'

    tmp = ''
    for d in delays:
        ms = round(d / int(FS) * 1000, 1)
        tmp += f'{ms}, '
    tmp = tmp.rstrip()[:-1]

    notice = notice.replace('xxx', tmp)
    return notice


def do_subsonic():

    global COEFF_SUBSONIC

    SUBSONIC_MP = f'{EQFOLDER}/{FS}/subsonic.mp.pcm'
    SUBSONIC_LP = f'{EQFOLDER}/{FS}/subsonic.lp.pcm'

    for fname in (SUBSONIC_MP, SUBSONIC_LP):
        if not pathlib.Path(fname).is_file():
            print(f'ERROR: cannot access to: {fname}')
            sys.exit()

    COEFF_SUBSONIC = COEFF_SUBSONIC.replace('SUBSONIC_MP', SUBSONIC_MP)
    COEFF_SUBSONIC = COEFF_SUBSONIC.replace('SUBSONIC_LP', SUBSONIC_LP)

    # Taps of a FLOAT32 pcm file
    filesize = pathlib.Path(SUBSONIC_MP).stat().st_size
    taps = int(filesize / 4)


    flen    = CONFIG["filter_length"]
    psize   = CONFIG["partition_size"]

    nblocks = 1
    if flen >= taps:
        while True:
            if nblocks * psize >= taps:
                break
            else:
                nblocks += 1
    else:
        print(f'WARNING: Subsonic {taps} taps > {flen}\n')

    COEFF_SUBSONIC = COEFF_SUBSONIC.replace('BLOCKS', str(nblocks))

    return COEFF_SUBSONIC


def read_config():
    """ Read configuration from loudspeakers/LSPK/brutefir_config.yml

        Outputs are given in NON standard YML, having 4 fields
        An output can be void, or at least to have a valid id:
            BrutefirId   Gain    Polarity  Delay (ms)
    """

    def check_output_params(out, params):

        bflabel, gain, pol, delay = params

        if not bflabel or not bflabel.replace('.', '').replace('_', '').isalpha():
            raise Exception( f'Output {out} bad name: {bflabel}' )

        if not bflabel[:2] == 'sw' and not bflabel[-2:] in ('.L', '.R'):
            raise Exception( f'Output {out} bad name: {bflabel}' )

        if gain:
            gain = round(float(gain), 1)
        else:
            gain = 0.0

        if pol:
            valid_pol = ('+', '-', '1', '-1', 1, -1)
            if not pol in valid_pol:
                raise Exception( f'Polarity must be in {valid_pol}' )
        else:
            pol = 1

        if delay:
            delay = round(float(delay), 3)
        else:
            delay = 0.0

        return out, (bflabel, gain, pol, delay)


    global CONFIG, FS

    try:
        with open(f'{LSPKFOLDER}/brutefir_config.yml', 'r') as f:
            CONFIG = yaml.safe_load(f)

    except Exception as e:
        print(f'(i) Error reading {LSPKNAME}/brutefir_config.yml: {str(e)}\n' )
        sys.exit()


    # Samplerate
    if not CONFIG["samplerate"] in (44100, 48000, 96000):
        raise Exception( f'Bad samplerate in brutefir_config.yml' )

    FS = CONFIG["sample_rate"]


    # Filter length (partition size and number of partitions)
    if cmdline_flength:
        CONFIG["filter_length"] = cmdline_flength

    else:
        CONFIG["filter_length"] = str(CONFIG["filter_length"])

    if ',' in CONFIG["filter_length"]:
        numpa = int( CONFIG["filter_length"].split(',')[-1].strip() )
    else:
        numpa = 1
    psize = int( CONFIG["filter_length"].split(',')[0].strip() )
    flen  = psize * numpa

    if not flen in (1024, 2048, 4096, 8192, 16384, 32768):
        raise Exception(f'ERROR: Bad filter length {flen} must be power of 2 and >= 1024')

    CONFIG["partition_size"] = psize
    CONFIG["num_partitions"] = numpa
    CONFIG["filter_length"]  = psize * numpa


    # Dither
    if not CONFIG["dither"] in (True, False):
        raise Exception( f'Bad dither in brutefir_config.yml' )


    # Outputs
    ways = []
    void_count = 0
    for out, params in CONFIG["outputs"].items():

        # It is expected 4 fields
        params = params.split() if params else []
        params += [''] * (4 - len(params))

        # Redo in dictionary form
        if not any(params):
            void_count += 1
            params = {'bflabel': f'void_{void_count}', 'gain': 0.0,
                      'polarity': '', 'delay': 0.0}

        else:
            _, p = check_output_params(out, params)
            bflabel, gain, pol, delay = p
            params = {'bflabel': bflabel, 'gain': gain, 'polarity': pol, 'delay': delay}
            ways.append( bflabel.split('.')[0] )

        CONFIG["outputs"][out] = params


    # Outputs match the JACK sound card device
    sc_channels = get_sound_card_num_outputs()
    num_outputs = len(CONFIG["outputs"].keys())
    if sc_channels and num_outputs != sc_channels:
        raise Exception(f'{num_outputs} outputs does not match sound card {sc_channels} channels')


    # Subsonic option
    if not 'subsonic' in CONFIG:
        CONFIG["subsonic"] = False
    else:
        if not CONFIG["subsonic"] in (True, False):
            raise Exception('Bad subsonic must be true or false')

    # Check ways
    ways = set(ways)
    if 'fr' in ways and ('lo' in ways or 'hi' in ways or 'mi' in ways):
        raise Exception( f'Erron in brutefir_config.yml: {ways} not valid' )


def main():

    tmp = EQ_CLI.replace('BANDS', EQ_BANDS[1:-1]).lstrip() \
                .replace('PORT', str(PORT))

    if disable_dump:
        tmp = tmp.replace('debug_dump_filter', '#debug_dump_filter')

    tmp += do_GENERAL_SETTINGS()
    tmp += do_IO()
    tmp += COEFF_EQ
    if CONFIG["subsonic"]:
        tmp += do_subsonic()
    tmp += do_DRC_COEFFS()
    tmp += do_XO_COEFFS()
    tmp += do_FILTERS_LEV_EQ_DRC()
    tmp += do_FILTERS()

    if not force:
        bf_file = 'brutefir_config_draft'
    else:
        bf_file = 'brutefir_config'

    print()
    print(f'(i) `loudspeakers/{LSPKNAME}/{bf_file}`:')
    print()
    print(f'    Fs:                 {FS}')
    print(f'    Filter lenght:      {CONFIG["partition_size"]},{CONFIG["num_partitions"]}')
    print(f'    Output dither:      {CONFIG["dither"]}')
    print(f'    Outputs delay:      {DELAY_LIST}')
    print(f'    Subsonic filter:    {"enabled" if CONFIG["subsonic"] else "disabled"}')
    print()
    print(f'(!) Check carefully:')
    print(f'    - The sampling rate match the one from your .pcm files')
    print(f'    - Soundcard channels mapping and delays')
    print(f'    - Attenuation for each coefficent if needed.')
    print(f'    - \'to_outputs\': polarity and attenuation for each way.')
    print()

    fout = f'{LSPKFOLDER}/{bf_file}'

    if force:
        ans = input(f'ARE YOU SURE TO OVERWRITE {bf_file}? (y/N) ')
        if ans.lower() != 'y' and ans.lower() != 's':
            print('NOT saved')
            sys.exit()

    with open(fout, 'w') as f:
        f.write(tmp)

    print(f'SAVED to: {fout}\n')


def get_sound_card_num_outputs():

    pconfig_path = f'{UHOME}/pe.audio.sys/config/config.yml'
    with open(pconfig_path, 'r') as f:
        pconfig = yaml.safe_load(f)

    if not pconfig["loudspeaker"] == LSPKNAME:
        print(f'\nCannot check SOUND CARD OUTS from the current `{pconfig_path}`\n')
        return

    if pconfig["jack"]["backend"] != 'alsa':
        print(f'\nCannot check SOUND CARD OUTS for {pconfig["jack"]["backend"]}`\n')
        return

    alsa_device = pconfig["jack"]["device"]
    if not ',' in alsa_device:
        alsa_device += ',0'

    channels = 0

    try:

        cmd = f'aplay -D {alsa_device} --channels=2 --dump-hw-params ' + \
              '/usr/share/sounds/alsa/Noise.wav 1>/tmp/aplay_dump_hw_params 2>&1'

        call(cmd, shell=True)

        with open('/tmp/aplay_dump_hw_params', 'r') as f:
            tmp = f.read()

        tmp = tmp.split('\n')


        for line in tmp:
            if 'CHANNELS' in line:
                line = line.split(':')[-1].replace('[', '').replace(']', '')
                n = line.split()[-1]
                if n:
                    channels = int(n)

    except:
        print(f'\nCannot check SOUND CARD OUTS for {pconfig["jack"]["backend"]} ' + \
               'with aplay --dump-hw-params`\n')

    if not channels:
        print(f'\nCannot check {alsa_device} SOUND CARD OUTS, may be in use?\n')

    return channels


if __name__ == '__main__':

    disable_dump    = False
    force           = False
    cmdline_flength = ''


    if len( sys.argv ) > 1:
        LSPKNAME = sys.argv[1]
    else:
        print(__doc__)
        sys.exit()

    for opc in sys.argv[2:]:

        if '-nodump' in opc:
            disable_dump = True

        elif '-force' in opc:
            force = True

        elif '-p' in opc:
            PORT = int( opc.split('=')[-1] )

        else:
            print(__doc__)
            sys.exit()

    print()


    LSPKFOLDER = f'{UHOME}/pe.audio.sys/loudspeakers/{LSPKNAME}'

    LSPKFILES = []
    entries = pathlib.Path(LSPKFOLDER)
    for entry in entries.iterdir():
        LSPKFILES.append(entry.name)

    update_eq_bands()

    read_config()

    main()
