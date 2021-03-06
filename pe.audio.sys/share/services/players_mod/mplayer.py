#!/usr/bin/env python3

# Copyright (c) 2019 Rafael Sánchez
# This file is part of 'pe.audio.sys', a PC based personal audio system.
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

""" A module to players.py to deal with playing services supported by Mplayer:
        DVB-T
        CDDA
        istreams
"""

# (i) I/O FILES MANAGED HERE:
#
# .cdda_info        'w'     CDDA album and tracks info in json format
#
# .{service}_fifo   'w'     Mplayer command input fifo,
#                           (remember to end commands with \n)
# .{service}_events 'r'     Mplayer info output is redirected here
#

#-----------------------------------------------------------------------
# Info about CDDA playing (http://www.mplayerhq.hu/DOCS/tech/slave.txt)
#
# loadfile cdda://A-B:S     load CD tracks from A to B at speed S
#
# get_property filename     get the tracks to be played as
#                           'A' (single track)
#                           or 'A-B' (range of tracks)
#
# get_property chapter      get the current track index inside
#                           the filename property (first is 0)
#
# seek_chapter 1            go to next track
# seek_chapter -1           go to prev track
#
# seek X seconds
#
# Rules:
#   - There is not a 'play' command, you must 'loadlist' or 'loadfile'
#   - 'loadlist' <playlist_file> doesn't allow smooth track changes.
#   - playback starts when 'loadfile' is issued
#   - 'pause' in Mplayer will pause-toggle
#   - 'stop' empties the loaded stuff
#   - 'seekxxxx' resumes playing
#-----------------------------------------------------------------------


import os
import sys
UHOME       = os.path.expanduser("~")
sys.path.append(f'{UHOME}/pe.audio.sys')

from share.miscel import MAINFOLDER, CONFIG
from subprocess import Popen
import json
import yaml
from time import sleep
import jack

sys.path.append( os.path.dirname(__file__) )
import cdda


ME          = __file__.split('/')[-1]


# Auxiliary function to format hh:mm:ss
def timeFmt(x):
    """ in:     x seconds   (float)
        out:    'hh:mm:ss'  (string)
    """
    # x must be float
    h = int( x / 3600 )         # hours
    x = int( round(x % 3600) )  # updating x to reamining seconds
    m = int( x / 60 )           # minutes from the new x
    s = int( round(x % 60) )    # and seconds
    return f'{h:0>2}:{m:0>2}:{s:0>2}'


# Aux to convert a given formatted time string "hh:mm:ss.cc" to seconds
def timestring2sec(t):
    s = 0.0
    t = t.split(':')
    if len(t) > 2:
        s += float( t[-3] ) * 3600
    if len(t) > 1:
        s += float( t[-2] ) * 60
    if len(t) >= 1:
        s += float( t[-1] )
    return s


# Aux function to check if Mplayer has loaded a disc
def cdda_is_loaded():
    """ input:      --
        output:     True | False
        I/O:        .cdda_fifo (w),  .cdda_events (r)
    """
    # Querying Mplayer to get the FILENAME
    # (if it results void it means no playing)
    with open(f'{MAINFOLDER}/.cdda_fifo', 'w') as f:
        f.write('get_file_name\n')
    sleep(.1)
    with open(f'{MAINFOLDER}/.cdda_events', 'r') as f:
        tmp = f.read().split('\n')
    for line in tmp[-2:]:
        if line.startswith('ANS_FILENAME='):
            return True
    return False


# Aux to load all disc tracks into Mplayer playlist
def cdda_load():
    """ input:      --
        output:     --
        I/O:        .cdda_info (w), a dict with album and tracks
    """
    print( f'({ME}) loading disk ...' )
    # Save disk info into a json file
    cdda.save_disc_metadata(device=cdda.CDROM_DEVICE,
                            fname=f'{MAINFOLDER}/.cdda_info')
    # Loading disc in Mplayer
    cmd = 'pausing loadfile \'cdda://1-100:1\''
    send_cmd(cmd, service='cdda')
    # Waiting for the disk to be loaded (usually ~ 5 sec)
    n = 15
    while n:
        if cdda_is_loaded():
            break
        print( f'({ME}) waiting for Mplayer to load disk' )
        sleep(1)
        n -= 1
    if n:
        print( f'({ME}) Mplayer disk loaded' )
    else:
        print( f'({ME}) TIMED OUT detecting Mplayer disk' )


# Aux to retrieve the current track an time info
def cdda_get_current_track():
    """ input:      ---
        output:     trackNum (int), trackPos (float)
        I/O:        .cdda_fifo (w), .cdda_events (r)
    """
    # (i) 'get_property chapter' produces cd audio gaps :-/
    #     'get_time_pos'         does not :-)
    #     When querying Mplayer, always must use the prefix
    #     'pausing_keep', otherwise pause will be released.

    def get_disc_pos():
        # 'get_time_pos': elapsed secs refered to the whole loaded.
        with open(f'{MAINFOLDER}/.cdda_fifo', 'w') as f:
            f.write( 'pausing_keep get_time_pos\n' )
        with open(f'{MAINFOLDER}/.cdda_events', 'r') as f:
            tmp = f.read().split('\n')
        for line in tmp[-10:]:
            if line.startswith('ANS_TIME_POSITION='):
                return float( line.replace('ANS_TIME_POSITION=', '')
                              .strip() )
        return 0.0

    def calc_track_and_pos(discPos):
        trackNum = 1
        cummTracksLength = 0.0
        trackPos = 0.0
        # Iterate tracks until discPos is exceeded
        while str(trackNum) in cd_info:
            trackLength = timestring2sec(cd_info[str(trackNum)]['length'])
            cummTracksLength += trackLength
            if cummTracksLength > discPos:
                trackPos = discPos - ( cummTracksLength - trackLength )
                break
            trackNum += 1
        return trackNum, trackPos

    # We need the cd_info tracks list dict
    try:
        with open(f'{MAINFOLDER}/.cdda_info', 'r') as f:
            cd_info = json.loads( f.read() )
    except:
        cd_info = cdda.cdda_info_template()

    discPos             = get_disc_pos()
    trackNum, trackPos  = calc_track_and_pos(discPos)

    # Ceiling track to the last available
    last_track = len( [ x for x in cd_info if x.isdigit() ] )
    if trackNum > last_track:
        trackNum = last_track

    return trackNum, trackPos


# Aux to disconect Mplayer jack ports from preamp ports.
def pre_connect(mode, pname=cdda.CD_CAPTURE_PORT):
    # (i) Mplayer cdda pausing becomes on strange behavior,
    #     a stutter audio frame stepping phenomena,
    #     even if a 'pausing_keep mute 1' command was issued.
    #     So will temporary disconnect jack ports
    try:
        jc = jack.Client('mplayer.py', no_start_server=True)
        sources = jc.get_ports(  pname,   is_output=True )
        sinks   = jc.get_ports( 'pre_in', is_input =True )
        if mode == 'on':
            for a, b in zip(sources, sinks):
                jc.connect(a, b)
        else:
            for a, b in zip(sources, sinks):
                jc.disconnect(a, b)
    except:
        pass
    return


# Aux to query Mplayer if paused or playing
def playing_status(service='cdda'):
    """ Mplayer status: play or pause
    """
    result = 'play'

    with open(f'{MAINFOLDER}/.{service}_fifo', 'w') as f:
        f.write( 'pausing_keep_force get_property pause\n' )

    sleep(.1)

    with open(f'{MAINFOLDER}/.{service}_events', 'r') as f:
        tmp = f.read().split('\n')
    for line in tmp[-2:]:
        if 'ANS_pause=yes' in line:
            result = 'pause'

    return result


# Aux to send Mplayer commands through by the corresponding fifo
def send_cmd(cmd, service):
    #print(f'({ME}) sending \'{cmd}\' to Mplayer (.{service}_fifo)') # DEBUG only
    with open(f'{MAINFOLDER}/.{service}_fifo', 'w') as f:
        f.write( f'{cmd}\n' )
    if cmd == 'stop':
        # Mplayer needs a while to report the actual state ANS_pause=yes
        sleep(2)


# MAIN Mplayer control (used for all Mplayer services: DVB, iSTREAMS and CD)
def mplayer_control(cmd, arg='', service=''):
    """ Sends a command to Mplayer trough by its input fifo
        input:  a command string
        result: a result string: 'play' | 'stop' | 'pause' | ''
    """

    supported_commands = (  'state',
                            'stop',
                            'pause',
                            'play',
                            'next',
                            'previous',
                            'rew',
                            'ff',
                            'play_track',
                            'eject'     )

    # (i) pe.audio.sys scripts redirects Mplayer stdout & stderr
    #     towards special files:
    #       ~/pe.audio.sys/.<service>_events
    #     so that will capture there the Mplayer's answers when
    #     a Mplayer command has been issued.
    #     Available commands: http://www.mplayerhq.hu/DOCS/tech/slave.txt

    status = playing_status(service)

    # Early return if SLAVE GETTING INFO commands:
    if cmd.startswith('get_'):
        send_cmd( cmd, service )
        return status
    # Early return if STATE or NOT SUPPORTED command:
    elif cmd == 'state'or cmd not in supported_commands:
        return status

    # Special command EJECT
    if cmd == 'eject':
        Popen( f'eject {cdda.CDROM_DEVICE}'.split() )
        # Flush .cdda_info
        with open( f'{MAINFOLDER}/.cdda_info', 'w') as f:
            f.write( json.dumps( cdda.cdda_info_template() ) )
        # Flush Mplayer playlist
        send_cmd('stop', service)
        return playing_status(service)

    # Processing ACTION commands (playback control)
    if service == 'istreams':

        # useful when playing a mp3 stream (e.g. a podcast url)
        if   cmd == 'previous':   cmd = 'seek -300 0'
        elif cmd == 'rew':        cmd = 'seek -60  0'
        elif cmd == 'ff':         cmd = 'seek +60  0'
        elif cmd == 'next':       cmd = 'seek +300 0'

        send_cmd(cmd, service)

    elif service == 'dvb':

        # (i) all this stuff is testing and not much useful
        if   cmd == 'previous':   cmd = 'tv_step_channel previous'
        elif cmd == 'rew':        cmd = 'seek_chapter -1 0'
        elif cmd == 'ff':         cmd = 'seek_chapter +1 0'
        elif cmd == 'next':       cmd = 'tv_step_channel next'

        send_cmd(cmd, service)

    elif service == 'cdda':

        if   cmd == 'previous':
            cmd = 'seek_chapter -1 0'   # 0: relative seek

        elif cmd == 'rew':
            cmd = 'seek -30 0'

        elif cmd == 'ff':
            cmd = 'seek +30 0'

        elif cmd == 'next':
            cmd = 'seek_chapter +1 0'

        elif cmd == 'stop':
            cmd = 'stop'

        elif cmd == 'pause' and status == 'play':
            cmd = 'pause'               # Mplayer will toggle to pause
            pre_connect('off')

        elif cmd == 'play':
            # Loading disc if necessary
            if not cdda_is_loaded():
                cdda_load()
            else:
                if status == 'pause':
                    cmd = 'pause'       # Mplayer will toggle to play
                else:
                    cmd = ''

        elif cmd == 'play_track':
            # Loading disc if necessary
            if not cdda_is_loaded():
                cdda_load()
            if arg.isdigit():
                curr_track = int( arg )
                chapter = int(curr_track) - 1
                cmd = f'seek_chapter {str(chapter)} 1'  # 1: absolute seek
            else:
                print( f'({ME}) BAD track {cmd[11:]}' )
                return 'bad track number'

        if cmd:
            send_cmd(cmd, service)

        status = playing_status(service)

        if status == 'play':
            pre_connect('on')

    else:
        print( f'({ME}) unknown Mplayer service \'{service}\'' )

    return status


# Aux Mplayer metadata only for the CDDA service
def cdda_meta(md):
    """ input:      a metadata blank dict
        output:     the updated one
    """
    # Getting the current track and track time position
    curr_track, trackPos = cdda_get_current_track()

    # We need the cd_info tracks list dict
    try:
        with open(f'{MAINFOLDER}/.cdda_info', 'r') as f:
            cd_info = json.loads( f.read() )
    except:
        cd_info = cdda.cdda_info_template()

    # Updating md fields:
    md['track_num'] = '1'
    md['bitrate'] = '1411'
    md['track_num'], md['time_pos'] = str(curr_track), timeFmt(trackPos)
    md['artist'] = cd_info['artist']
    md['album'] = cd_info['album']
    if md['track_num'] in cd_info.keys():
        md['title']     = cd_info[ md['track_num'] ]['title']
        md['time_tot']  = cd_info[ md['track_num'] ]['length'][:-3]
                                                    # omit decimals
    else:
        md['title'] = 'Track ' + md['track_num']
    last_track = len( [ x for x in cd_info if x.isdigit() ] )
    md['tracks_tot'] = f'{last_track}'
    return md


# MAIN Mplayer metadata
def mplayer_meta(md, service):
    """ gets metadata from Mplayer as per
        http://www.mplayerhq.hu/DOCS/tech/slave.txt

        input:      md:         a blank metadata dict,
                    service:    'cdda' or any else
        output:     the updated md dict
    """

    md['player'] = 'Mplayer'

    # (!) DIVERTING: this works only for DVB or iSTREAMS, but not for CDDA
    if service == 'cdda':
        return cdda_meta(md)

    # This is the file were Mplayer standard output has been redirected to,
    # so we can read there any answer when required to Mplayer slave daemon:
    mplayer_redirection_path = f'{MAINFOLDER}/.{service}_events'

    # Communicates to Mplayer trough by its input fifo
    # to get the current media filename and bitrate:
    mplayer_control(cmd='get_audio_bitrate', service=service)
    mplayer_control(cmd='get_file_name',     service=service)
    mplayer_control(cmd='get_time_pos',      service=service)
    mplayer_control(cmd='get_time_length',   service=service)

    # Waiting for Mplayer ANS_xxxx to be written to the output file
    sleep(.25)

    # Trying to read the ANS_xxxx from the Mplayer output file
    with open(mplayer_redirection_path, 'r') as file:
        try:
            # get last 4 lines plus the empty one when splitting
            tmp = file.read().replace('\x00', '').split('\n')[-5:]
        except:
            tmp = []

    # Flushing the Mplayer output file to avoid continue growing:
    with open(mplayer_redirection_path, 'w') as file:
        file.write('')

    # Reading the intended metadata chunks
    if len(tmp) >= 4:
    # avoiding indexes issues while no relevant metadata are available

        if 'ANS_AUDIO_BITRATE=' in tmp[0]:
            bitrate = tmp[0].split('ANS_AUDIO_BITRATE=')[1] \
                                            .split('\n')[0] \
                                            .replace("'", "")
            md['bitrate'] = bitrate.split()[0]

        if 'ANS_FILENAME=' in tmp[1]:
            # this way will return the whole url:
            #md['title'] = tmp[1].split('ANS_FILENAME=')[1]
            # this way will return just the filename:
            md['title'] = tmp[1].split('ANS_FILENAME=')[1] \
                                            .split('?')[0] \
                                            .replace("'", "")

        if 'ANS_TIME_POSITION=' in tmp[2]:
            time_pos = tmp[2].split('ANS_TIME_POSITION=')[1] \
                                             .split('\n')[0]
            md['time_pos'] = timeFmt( float( time_pos ) )

        if 'ANS_LENGTH=' in tmp[3]:
            time_tot = tmp[3].split('ANS_LENGTH=')[1].split('\n')[0]
            md['time_tot'] = timeFmt( float( time_tot ) )

    return md
