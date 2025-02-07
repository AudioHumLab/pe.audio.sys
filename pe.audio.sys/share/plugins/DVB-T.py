#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

"""
    Start or stop Mplayer for DVB-T playback.

    Also used to change on the fly the played stream.

    DVB-T tuned channels are ussually stored at
        ~/.mplayer/channels.conf

    User settings (presets) can be configured at
        pe.audio.sys/config/DVB-T.yml

    Usage:    DVB-T.py  start   [ <preset_num> | <channel_name> ]
                        stop
                        preset  <preset_num>
                        name    <channel_name>


    Notice:
    When loading a new stream, Mplayer jack ports will dissapear for a while,
    so you'll need to wait for Mplayer ports to re-emerge before switching
    the preamp input.


    VOLUME MANAGEMENT
    http://www.mplayerhq.hu/DOCS/HTML/en/MPlayer.html#advaudio-volume

    Mplayer SLAVE MODE
    http://www.mplayerhq.hu/DOCS/tech/slave.txt

"""

""" Example of ERROR in Mplayer printout:

        DVB CONFIGURATION IS EMPTY, exit

    This is CONFUSING, because the real problem was that the DVB card was not detected
    (wrong USB connection, see dmesg or journalctrl)
"""


""" Examples of Mplayer printouts when playing DVB-T radio channels

rafax@salon64:~$ mplayer -nolirc -ao alsa "dvb://Radio Clasica HQ MPA"
MPlayer 1.4 (Debian), built with gcc-11 (C) 2000-2019 MPlayer Team

Playing dvb://Radio Clasica HQ MPA.
dvb_tune Freq: 634000000
TS file format detected.
NO VIDEO! AUDIO MPA(pid=2010) NO SUBS (yet)!  PROGRAM N. 0
==========================================================================
Opening audio decoder: [mpg123] MPEG 1.0/2.0/2.5 layers I, II, III
AUDIO: 48000 Hz, 2 ch, s16le, 160.0 kbit/10.42% (ratio: 20000->192000)
Selected audio codec: [mpg123] afm: mpg123 (MPEG 1.0/2.0/2.5 layers I, II, III)
==========================================================================
AO: [alsa] 48000Hz 2ch s16le (2 bytes per sample)
Video: no video
Starting playback...
A:17726.5 ( 4:55:26.4) of -0.8 (unknown) ??,?%
[AO_ALSA] Write error: Broken pipe
[AO_ALSA] Trying to reset soundcard.
A:17737.3 ( 4:55:37.3) of -0.8 (unknown) 13.8%


MPlayer interrupted by signal 2 in module: decode_audio
dvb_streaming_read, attempt N. 6 failed with errno 4 when reading 24 bytes
A:17737.4 ( 4:55:37.4) of -0.8 (unknown) 13.9%

Exiting... (Quit)


rafax@salon64:~$ mplayer -nolirc -ao alsa "dvb://Radio Clasica HQ A52"
MPlayer 1.4 (Debian), built with gcc-11 (C) 2000-2019 MPlayer Team

Playing dvb://Radio Clasica HQ A52.
dvb_tune Freq: 634000000
TS file format detected.
NO VIDEO! AUDIO A52(pid=2012) NO SUBS (yet)!  PROGRAM N. 0
==========================================================================
Opening audio decoder: [ffmpeg] FFmpeg/libavcodec audio decoders
libavcodec version 58.134.100 (external)
AUDIO: 48000 Hz, 2 ch, floatle, 256.0 kbit/8.33% (ratio: 32000->384000)
Selected audio codec: [ffac3] afm: ffmpeg (FFmpeg AC-3)
==========================================================================
AO: [alsa] 48000Hz 2ch floatle (4 bytes per sample)
Video: no video
Starting playback...
A:17840.4 ( 4:57:20.4) of -0.6 (unknown) 69.5%


MPlayer interrupted by signal 2 in module: decode_audio
dvb_streaming_read, attempt N. 6 failed with errno 4 when reading 776 bytes
A:17840.5 ( 4:57:20.5) of -0.6 (unknown) 69.8%

Exiting... (Quit)
"""

from    pathlib import Path
from    time    import sleep
from    subprocess import Popen, call, check_output
import  yaml
import  sys
import  os

UHOME       = os.path.expanduser("~")
MAINFOLDER  = f'{UHOME}/pe.audio.sys'
sys.path.append(f'{MAINFOLDER}/share/miscel')

from miscel import wait4ports, check_Mplayer_config_file, Fmt, USER


CHANNELS_PATH   = f'{UHOME}/.mplayer/channels.conf'
PRESETS_PATH    = f'{MAINFOLDER}/config/DVB-T.yml'
REDIR_PATH      = f'{MAINFOLDER}/.dvb_events'
INPUT_FIFO      = f'{MAINFOLDER}/.dvb_fifo'


# (i) STREAM LEVEL management
#     '-softvol-max 400' alows to amplify 12 dB for AC3 encoded streams, see
#     above examples. Then later, we can issue a slave mode volume command.
MPLAYER_OPTIONS = '-quiet -nolirc -slave -idle -softvol -softvol-max 400'


def select_by_preset(pnum):
    """ loads a stream by its presets file number id """

    try:
        channel_name = PRESETS[pnum]['name']
        select_by_name(channel_name)

    except:
        tmp = f'(DVB-T.py) error with preset # {pnum}'
        print(f'{Fmt.BOLD}{tmp}{Fmt.END}')
        sys.exit()


def select_by_name(channel_name):
    """ loads a stream by its channel.conf name """


    def get_volume():
        """ Boost 12 dB if 'codec' is AC3 kind of as per the PRESETS user file.
        """

        volume = 0

        for pnum in PRESETS:

            if PRESETS[pnum]['name'] == channel_name:
                if 'codec' in  PRESETS[pnum] and PRESETS[pnum]['codec']:
                    if 'ac3' in  PRESETS[pnum]['codec'].lower():
                        volume = 400 # 12 dB in percent
                break

        return volume


    # Searching the channel_name in channels file
    try:
        check_output( ['grep', channel_name, CHANNELS_PATH] ).decode()

    except:
        print( f"(DVB-T.py) Channel NOT found: '{channel_name}'" )
        sys.exit()


    # Loading the DVB-T station
    try:

        # The whole address after 'loadfile' needs to be SINGLE quoted to load properly
        command = f"loadfile 'dvb://{channel_name}'"

        with open( INPUT_FIFO, 'w') as f:
            f.write( f"{command}\n" )

        print( f"(DVB-T.py) issued: {command}" )


        # Optional VOLUME for multichannel codec 'ffac3'
        volume = get_volume()

        if volume:

            # see Mplayer docs: slave.txt
            command = f"volume {volume} 1"

            with open( INPUT_FIFO, 'w') as f:
                f.write( f"{command}\n" )

            print( f"(DVB-T.py) issued: {command}" )


    except:

        print( f"(DVB-T.py) failed to load '{channel_name}'" )
        sys.exit()


    # Wait a bit for the new Mplayer ports to emerge (informational only)
    sleep(2)
    if wait4ports('mplayer_dvb', 5):
        print( f"(DVB-T.py) Mplayer JACK ports emerged" )
    else:
        print( f"(DVB-T.py) Mplayer JACK ports NOT available" )


def start():

    cmd = f'mplayer {MPLAYER_OPTIONS} -profile dvb -input file={INPUT_FIFO}'

    # (i) The "redir" file grows about 200K per hour while running mplayer
    with open(REDIR_PATH, 'w') as f:
        # clearing the file for this session
        f.write('')
        Popen( cmd.split(), shell=False, stdout=f, stderr=f )


def stop():
    # Killing our mplayer instance
    call( ['pkill', '-u', USER, '-KILL', '-f', 'profile dvb'] )


def do_check_files():
    """ Check the necessary files for this to work
    """

    global PRESETS

    # Input FIFO for Mplayer -slave mode
    f = Path( INPUT_FIFO )
    if not f.is_fifo():
        Popen( f'mkfifo {INPUT_FIFO}'.split() )
    del(f)

    # Mplayer config file
    tmp = check_Mplayer_config_file(profile='dvb')

    if tmp != 'ok':
        print( f'{Fmt.RED}(DVB-T.py) {tmp}{Fmt.END}' )
        sys.exit()

    # Channels file
    f = Path( CHANNELS_PATH )
    if not f.is_file():
        print( f"(DVB-T.py) ERROR reading channels file: '{CHANNELS_PATH}'" )
        sys.exit()
    del(f)

    # DVB-T presets file
    try:
        with open(PRESETS_PATH, 'r') as f:
            PRESETS = yaml.safe_load(f)
    except:
        print( f"(DVB-T.py) ERROR reading user presets file: '{PRESETS_PATH}'" )
        sys.exit()


if __name__ == '__main__':

    # Check the necessary files for this to work
    do_check_files()

    ### Reading the command line
    if sys.argv[1:]:

        opc = sys.argv[1]

        # STARTS the plugin and optionally load a preset/name
        if opc == 'start':
            start()
            if sys.argv[2:]:
                opc2 = sys.argv[2]
                if opc2.isdigit():
                    select_by_preset( int(opc2) )
                elif opc2.isalpha():
                    select_by_name(opc2)

        # STOPS all this stuff
        elif opc == 'stop':
            stop()

        # ON THE FLY changing to a preset number or rotates recent
        elif opc == 'preset':
            select_by_preset( int(sys.argv[2]) )

        # ON THE FLY changing to a preset name
        elif opc == 'name':
            select_by_name( sys.argv[2] )

        elif '-h' in opc:
            print(__doc__)
            sys.exit()

        else:
            print( '(DVB-T.py) Bad option' )

    else:
        print(__doc__)
