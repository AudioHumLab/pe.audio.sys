#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

""" A MPD interface module for players.py
"""
import  os
import  sys
import  mpd
from    time        import sleep
import  json
from    subprocess  import Popen, run

UHOME = os.path.expanduser("~")
sys.path.append(f'{UHOME}/pe.audio.sys/share/miscel')
sys.path.append( os.path.dirname(__file__) )

from miscel import time_sec2hhmmss, time_sec2mmss, Fmt,     \
                   read_mpd_config, read_cdda_meta_from_disk,   \
                   PLAYER_METATEMPLATE

MPD_PORT                = read_mpd_config()["port"]
CDDA_MPD_PLAYLIST_PATH  = f'{UHOME}/pe.audio.sys/.cdda_mpd_playlist'
LAST_MPD_PLAYLIST_PATH  = f'{UHOME}/pe.audio.sys/.last_mpd_playlist'

c = mpd.MPDClient()


def ping_mpd():
    """ (i) Do not use ping() because some times crash:
            Got unexpected return value: <...a sringify state...>

        Use status() instead.
    """

    try:
        c.status()
        return True

    except Exception as e:

        print(f'{Fmt.GRAY}(mpd_mod.py) ERROR {str(e)}{Fmt.END}')

        try:
            print(f'{Fmt.GRAY}(mpd_mod.py) Trying to connect ... .. .{Fmt.END}')
            c.connect('localhost', MPD_PORT, timeout=30)
            print(f'{Fmt.BLUE}(mpd_mod.py) Connected to MPD{Fmt.END}')
            sleep(.1)
            return True

        except Exception as e:
            print(f'{Fmt.BOLD}(mpd_mod.py) {str(e)}{Fmt.END}')
            return False


def mpd_cdda_in_playlist(all_or_any='any'):

    result = False

    if not ping_mpd():
        print(f'{Fmt.RED}(mpd_mod.py) mpd_cdda_in_playlist not connected to MPD{Fmt.END}')
        return result

    pl = c.playlist()

    # example:
    # ['file: cdda://dev/cdrom/1',
    #  'file: cdda://dev/cdrom/2',
    #  'file: cdda://dev/cdrom/3',
    #   ... ]

    if all_or_any == 'any':
        return any( [ 'cdda:/' in x for x in pl ] )
    else:
        return all( [ 'cdda:/' in x for x in pl ] )


def mpd_get_cd_track_nums():
    """ special use for CD
    """

    result = []

    if not ping_mpd():
        print(f'{Fmt.RED}(mpd_mod.py) mpd_get_cd_track_nums not connected to MPD{Fmt.END}')
        return result

    if mpd_cdda_in_playlist('all'):
        result = c.playlist()

    # ['file: cdda://dev/cdrom/1',
    #  'file: cdda://dev/cdrom/2',
    #  ... ]

    result = [ x.split('/')[-1] for x in result ]
    # ['1', '2', '3' , ... ]

    return result


def mpd_playlist():

    result = []

    if not ping_mpd():
        print(f'{Fmt.RED}(mpd_mod.py) mpd_playlist not connected to MPD{Fmt.END}')
        return result


    try:
        tmp = c.playlistid()

        if mpd_cdda_in_playlist('all'):
            print(f'{Fmt.BLUE}(mpd_mod.py) mpd_playlist is a CD playlist{Fmt.END}')
            result = [ f'{int(x["pos"]) + 1}. {x["name"]}' for x in tmp ]

        else:
            print(f'{Fmt.RED}(mpd_mod.py) mpd_playlist is NOT a CD playlist{Fmt.END}')
            result = [ x["title"] for x in tmp ]

    except Exception as e:
        print(f'{Fmt.RED}(mpd_mod.py) mpd_playlist {str(e)}{Fmt.END}')

    return result


def mpd_playlists(cmd, arg=''):

    result = ''

    if not ping_mpd():
        print(f'{Fmt.RED}(mpd_mod.py) mpd_playlists: not connected to MPD{Fmt.END}')
        return result

    if cmd == 'get_playlists':

        # Some setups could use a mount for mpdconf playlist_directory
        try:
            result = [ x['playlist'] for x in c.listplaylists() ]

        # [52@0] {listplaylists} Failed to open /mnt/qnas/media/playlists/: No such file or directory
        except Exception as e:
            print(f'{Fmt.RED}(mpd_mod.py) error with `{cmd}` {str(e)}{Fmt.END}')


    elif cmd == 'load_playlist':

        try:
            c.load(arg)
            result = f'ordered loading `{arg}`'
        except Exception as e:
            result = f'{str(e)}'


    elif cmd == 'clear_playlist':

        try:
            c.clear()
            sleep(.2)
            result = 'playlist cleared'
        except Exception as e:
            result = f'{str(e)}'


    return result


def mpd_control( cmd, arg='', port=MPD_PORT ):
    """ Comuticates to MPD music player daemon

        Input:      a command [arg] to query to the MPD daemon

        Returns:    a playback state string ( stop | play | pause )
                    OR
                    a random mode (on/off)
    """

    if not ping_mpd():
        print(f'{Fmt.RED}(mpd_mod.py) mpd_control not connected to MPD{Fmt.END}')
        return 'stop'

    # Do execute the command
    try:
        match cmd:

            case 'state':
                pass

            case 'stop':
                c.stop()

            case 'pause':
                c.pause()

            case 'play':
                c.play()

            case 'play_track':
                c.play(int(arg) - 1)

            case 'next':
                c.next()

            case 'previous':
                c.previous()

            case 'rew':         # for REW and FF will move 30 seconds
                c.seekcur('-30')

            case 'ff':
                c.seekcur('+30')

            case 'random':

                if arg == 'on':
                    c.random(1)

                elif arg == 'off':
                    c.random(0)

                elif arg == 'toggle':
                    st = c.status()
                    if 'random' in st:
                        c.random( {'0':1, '1':0}[ st["random"] ])


    except Exception as e:
        print(f'{Fmt.RED}(mpd_mod.py) error with `{cmd}`{Fmt.END}' )
        print(f'{Fmt.RED}(mpd_mod.py) {str(e)}{Fmt.END}' )



    # (i) Must wait a bit to avoid a weird behavior after ordering a command
    sleep(.2)

    try:
        st = c.status()
    except Exception as e:
        print(f'{Fmt.RED}(mpd_mod.py) `status` no answer from MPD{Fmt.END}')
        return 'stop'

    try:

        if cmd == 'random':
            return {'0':'off', '1':'on'}[ st['random'] ]

        else:
            if 'state' in st:
                return st['state']
            else:
                return 'stop'

    except Exception as e:

        print(f"{Fmt.RED}(mpd_mod.py) mpd_control {str(e)}{Fmt.END}")

        if cmd == 'random':
            return 'off'
        else:
            return 'stop'


def mpd_meta( md=PLAYER_METATEMPLATE.copy() ):
    """ Comuticates to MPD music player daemon
        Input:      blank metadata dict
        Return:     track metadata dict
    """

    def get_bitrate_from_format(f):
        """ example '44100:16:2'
        """
        br = ''
        try:
            a,b,c = f.split(':')
            br = round(int(a) * int(b) * int(c) / 1e6, 3)
            br = str(br)
        except Exception as e:
            print(e)
        return br


    md['player'] = 'MPD'

    if not ping_mpd():
        print(f'{Fmt.RED}(mpd_mod.py) mpd_meta not connected to MPD{Fmt.END}')
        return  md

    try:
        st = c.status()
    except Exception as e:
        print(f'{Fmt.RED}(mpd_mod.py) `status` no answer from MPD{Fmt.END}')
        return md

    try:
        cs = c.currentsong()
    except Exception as e:
        print(f'{Fmt.RED}(mpd_mod.py) `currentsong` no answer from MPD{Fmt.END}')
        return md


    # (i) Not all tracks have complete currentsong() fields. Some examples:
    #
    #   {'file': 'http://192.168.1.46:49149/qobuz/track/version/1/trackId/4526528',
    #   'artist': 'Claudio Arrau',
    #   'album': 'Liszt: Piano Sonata in B Minor / Annees De Pelerinage / Ballade No. 2 / Transcendental Etude No. 10 (Arrau) (1970-1981)',
    #   'title': 'Piano Sonata in B Minor, S. 178/R. 21',
    #   'pos': '0',
    #   'id': '135'}
    #
    #   {'file': 'https://rtvelivestream.akamaized.net/rtvesec/rne/GL0/34_2024_07_11_20_11_03_113822.ts',
    #   'pos': '0',
    #   'id': '156'}


    # Skip if no currentsong is loaded
    if cs:
        if 'artist' in cs:
            md['artist']    = cs['artist']

        if 'album' in cs:
            md['album']     = cs['album']

        if 'track' in cs:
            md['track_num'] = cs['track']

        if 'title' in cs:
            md['title']     = cs['title']
        elif 'file' in cs:
            md['title']     = cs['file'].split('/')[-1]

        if 'file' in cs:
            md['file']      = cs["file"]

            if not 'album' in cs:
                # Try to put the URL site as 'album', if available
                if '//' in md['file']:
                    md['album'] = '/'.join( md['file'].split('/')[:3] )


    if 'playlistlength' in st:
        md['tracks_tot']    = st['playlistlength']

    if 'bitrate' in st:
        # playing wav/aiff/cdda files gives bitrate: '0'
        if st['bitrate'] != '0':
            md['bitrate']   = st['bitrate']  # kbps

    if 'audio' in st:
        md['format'] = st['audio']

        if not md['bitrate']:
            md['bitrate'] = get_bitrate_from_format( md['format'] )

    if 'time' in st:
        # time is given as a string 'current:total', each part in seconds
        md["time_pos"] = time_sec2mmss( int( st["time"].split(':')[0] ))
        md["time_tot"] = time_sec2mmss( int( st["time"].split(':')[1] ))


    # Special case CD audio we need to read artist and album
    # from the .cdda_metadata file previously saved to disk
    if 'file' in cs and 'cdda:/' in cs["file"]:

        curr_cd_track =  cs["file"].split('/')[-1]

        cdda_meta = read_cdda_meta_from_disk()

        md["artist"]    = cdda_meta["artist"]
        md["album"]     = cdda_meta["album"]
        md["track_num"] = curr_cd_track
        md["title"]     = cdda_meta["tracks"][curr_cd_track]["title"]


    return md

