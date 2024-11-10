#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

""" A Spotify Desktop client interface module for players.py
"""

from    time        import sleep
from    subprocess  import check_output
import  yaml
import  json
from    pydbus      import SessionBus
import  logging
import  os
import  sys
UHOME = os.path.expanduser("~")
sys.path.append(f'{UHOME}/pe.audio.sys/share/miscel')

from    miscel  import MAINFOLDER, time_sec2mmss, Fmt


# (i) AUDIO FORMAT IS HARDWIRED pending on how to retrieve it from the desktop client.
SPOTIFY_BITRATE = '320'
SPOTIFY_FORMAT  = '44100:16:2'

# USER PLAYLISTS
plist_file = f'{MAINFOLDER}/config/spotify_plists.yml'
PLAYLISTS = {}
if os.path.exists(plist_file):
    try:
        PLAYLISTS = yaml.safe_load(open(plist_file, 'r'))
        tmp = f'READ \'{plist_file}\''
    except:
        tmp = f'ERROR reading \'{plist_file}\''
        print(f'(spotify_desktop.py) {tmp}')
    logging.info(tmp)


def spotibus_connect():
    """ The DBUS INTERFACE with the Spotify Desktop client.

        You can browse it also by command line tool:
        $ mdbus2 org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2

        (bool)
    """
    global spotibus

    spotibus = None
    tries = 3
    while tries:
        try:
            # SessionBus will work if D-Bus has an available X11 $DISPLAY
            bus      = SessionBus()
            spotibus = bus.get( 'org.mpris.MediaPlayer2.spotify',
                                '/org/mpris/MediaPlayer2' )
            logging.info(f'spotibus OK')
            return True
        except Exception as e:
            logging.info(f'spotibus FAILED: {e}')
            tries -= 1
            sleep(.1)
    return False


def set_shuffle(mode):
    """ Try to use the external tool 'playerctl' to manage shuffle because
        MPRIS can only read shuffle mode, not manage it.

        (i) Anyway, the command line tool 'playerctl' has a shuffle method
            BUT it does not work with Spotify Desktop :-(

        (string)
    """
    mode = { 'on':'On', 'off':'Off' }[mode]
    try:
        ans = check_output( f'playerctl shuffle {mode}'.split() ).decode()
        ans = { 'on':'on', 'off':'off', 'On':'on', 'Off':'off' }[ans]
    except:
        ans = 'off'
    return ans


def spotify_playlists(cmd, arg=''):
    """ Manage playlists
        (string)
    """

    # try reconnecting if SessionBus was lost for some reason
    try:
        spotibus.CanControl
    except:
        spotibus_connect()
    if not spotibus:
        return 'ERROR connecting to spotify'

    if cmd == 'load_playlist':
        if PLAYLISTS:
            if arg in PLAYLISTS:
                spotibus.OpenUri( PLAYLISTS[arg] )
                result = 'ordered'
            else:
                result = 'ERROR: playlist not found'
        else:
            result = 'ERROR: Spotify playlist not available'

    elif cmd == 'get_playlists':
        result = json.dumps( list( PLAYLISTS.keys() ) )

    else:
        result = 'bad command'

    return result


def spotify_control(cmd, arg=''):
    """ Controls the Spotify Desktop player
        input:  a command string
        output: the resulting status string
        (string)
    """
    result = 'not connected'

    # try reconnecting if SessionBus was lost for some reason
    try:
        spotibus.CanControl
    except:
        spotibus_connect()
    if not spotibus:
        return result

    try:
        if   cmd == 'state':
            pass

        elif cmd == 'play':
            spotibus.Play()

        elif cmd == 'pause':
            spotibus.Pause()

        elif cmd == 'next':
            spotibus.Next()

        elif cmd == 'previous':
            spotibus.Previous()

        # MPRIS Shuffle is an only-readable property.
        # (https://specifications.freedesktop.org/mpris-spec/latest/Player_Interface.html)
        elif cmd == 'random':

            if arg in ('get', ''):
                return spotibus.Shuffle

            elif arg in ('on', 'off'):
                set_shuffle(arg)
                return spotibus.Shuffle

            else:
                return f'error with \'random {arg}\''

        elif cmd == 'volume':

            if arg:
                spotibus.Volume = float(arg)

            else:
                return str( round(spotibus.Volume, 2) )


        result = {  'Playing':  'play',
                    'Paused':   'pause',
                    'Stopped':  'stop' } [spotibus.PlaybackStatus]

    except:
        pass

    return result


def spotify_meta(md):
    """ Analize the MPRIS metadata info from spotibus.Metadata
        Input:      blank md dict
        Output:     Spotify metadata dict
        (dictionary)
    """

    # Fixed metadata
    md['player']  = 'Spotify Desktop Client'
    md['bitrate'] = SPOTIFY_BITRATE
    md["format"]  = SPOTIFY_FORMAT

    # try reconnecting if SessionBus was lost for some reason
    try:
        spotibus.CanControl
    except:
        spotibus_connect()
    if not spotibus:
        return md

    try:
        tmp = spotibus.Metadata
        # Example:
        # {
        # "mpris:trackid": "spotify:track:5UmNPIwZitB26cYXQiEzdP",
        # "mpris:length": 376386000,
        # "mpris:artUrl": "https://open.spotify.com/image/798d9b9cf2b63624c8c6cc191a3db75dd82dbcb9",
        # "xesam:album": "Doble Vivo (+ Solo Que la Una/Con Cordes del Mon)",
        # "xesam:albumArtist": ["Kiko Veneno"],
        # "xesam:artist": ["Kiko Veneno"],
        # "xesam:autoRating": 0.1,
        # "xesam:discNumber": 1,
        # "xesam:title": "Ser\u00e9 Mec\u00e1nico por Ti - En Directo",
        # "xesam:trackNumber": 3,
        # "xesam:url": "https://open.spotify.com/track/5UmNPIwZitB26cYXQiEzdP"
        # }

        # regular fields:
        for k in ('artist', 'album', 'title'):
            value = tmp[ f'xesam:{k}']
            if type(value) == list:
                md[k] = ' '.join(value)
            elif type(value) == str:
                md[k] = value

        # track_num:
        md['track_num'] = tmp["xesam:trackNumber"]

        # time lenght:
        md['time_tot'] = time_sec2mmss( tmp["mpris:length"] / 1e6 )

        # loaded file
        md["file"] = tmp["mpris:trackid"]
        #md["file"] = tmp["xesam:url"]

    except Exception as e:
        print(f'{Fmt.RED}(spotify_desktop.py) {str(e)}{Fmt.END}')

    return md


def init():
    """ (void)
    """

    logfname = f'{MAINFOLDER}/log/spotify_desktop.log'
    logging.basicConfig(filename=logfname, filemode='w', level=logging.INFO)

    spotibus_connect()


# autoexec on loading this module
init()
