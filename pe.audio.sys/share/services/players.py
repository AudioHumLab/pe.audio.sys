#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

""" Controls and retrieve metadata info from the current player.
"""

# (i) I/O FILES MANAGED HERE:
#
# .state            'r'     pe.audio.sys state file
#
# .player_metadata  'w'     Stores the current player metadata
#

import  os
import  sys
import  threading
from    socket      import gethostname
from    time        import sleep
import  json
from    subprocess  import Popen, run


UHOME = os.path.expanduser("~")
sys.path.append(f'{UHOME}/pe.audio.sys/share/miscel')


from  config                        import  CONFIG, MAINFOLDER,         \
                                            PLAYER_META_PATH,           \
                                            PLAYER_METATEMPLATE,        \
                                            CDDA_META_PATH,             \
                                            CDDA_META_TEMPLATE

from  miscel                        import  detect_spotify_client,      \
                                            read_state_from_disk,       \
                                            read_cdda_meta_from_disk,   \
                                            read_mpd_config,            \
                                            send_cmd, is_IP, Fmt

from  players_mod.mpd_mod           import  mpd_control,                \
                                            mpd_meta,                   \
                                            mpd_playlist,               \
                                            mpd_playlists,              \
                                            mpd_get_cd_track_nums,      \
                                            mpd_cdda_in_playlist

from  players_mod.mplayer           import  mplayer_control,            \
                                            mplayer_get_meta,           \
                                            mplayer_playlists

from  players_mod.librespot         import  librespot_control,          \
                                            librespot_meta

from  players_mod.spotify_desktop   import  spotify_control,            \
                                            spotify_meta,               \
                                            spotify_playlists


## Getting sources list
SOURCES = CONFIG["sources"]

## Spotify client detection
SPOTIFY_CLIENT = detect_spotify_client()

# The runtime metadata variable and the loop refresh period in seconds
CURRENT_MD          = PLAYER_METATEMPLATE.copy()
MD_REFRESH_PERIOD   = 2


def clear_cdda_stuff():

        # Clearing MPD cd playlist
        if mpd_cdda_in_playlist(all_or_any='any'):
            print(f'{Fmt.GRAY}(players.py) Clearing MPD playlist{Fmt.END}')
            run( 'mpc stop'.split()  )
            sleep(.2)
            run( 'mpc clear'.split() )
            sleep(1)

        # blank pe.audio.sys/.cdda_metadata
        print(f'{Fmt.GRAY}(players.py) clearing `{CDDA_META_PATH}`{Fmt.END}')
        with open(CDDA_META_PATH, 'w') as f:
            f.write( json.dumps(CDDA_META_TEMPLATE.copy()) )

        # delete MPD cdda playlist files (M3U/PLS)
        MPD_PL_DIR  = read_mpd_config()["playlist_directory"]

        if not os.path.isdir( MPD_PL_DIR ):

            msg = f'directory NOT available `{MPD_PL_DIR}`, fallback to `~/.config/mpd/playlists`'
            print(f'{Fmt.BOLD}(players.py) {msg}{Fmt.END}')

            send_cmd(f'aux warning clear', verbose=True, timeout=1)
            send_cmd(f'aux warning set {msg}', verbose=True, timeout=1)

            MPD_PL_DIR  = f'{UHOME}/.config/mpd/playlists'

        CD_PL_PATH = f'{MPD_PL_DIR}/cdda_*'

        print(f'{Fmt.GRAY}(players.py) clearing `{CD_PL_PATH}`{Fmt.END}')
        Popen( f'rm -f {CD_PL_PATH}', shell=True )



def remote_get_meta(host, port=9990):
    """ Get metadata from a remote pe.audio.sys system
    """
    try:
        tmp = send_cmd( cmd='player get_meta',
                        host=host, port=port, timeout=1)
        md = json.loads(tmp)
    except:
        md = PLAYER_METATEMPLATE.copy()
    return md


def remote_player_control( cmd, arg, host, port=9990):
    """ Controls the playback on a remote pe.audio.sys system
    """
    # short timeout for remote LAN machine conn failure
    timeout = .5
    rem_state = send_cmd( cmd=f'player {cmd} {arg}',
                          host=host, port=port, timeout=timeout)
    return rem_state


def get_meta():
    """ Returns a dictionary with the current track metadata
        including the involved source player
    """
    md = PLAYER_METATEMPLATE.copy()

    source      = read_state_from_disk()['input']
    source_port = read_state_from_disk()['input_port']

    if 'librespot' in source or 'spotify' in source.lower():

        if SPOTIFY_CLIENT == 'desktop':
            md = spotify_meta(md)

        elif SPOTIFY_CLIENT == 'librespot':
            md = librespot_meta(md)

        # source is spotify like but no client running has been detected:
        else:
            md['player'] = 'Spotify'

    elif 'mpd' in source.lower():
        md = mpd_meta(md)

    elif source == 'istreams':
        md = mplayer_get_meta(md, service='istreams')

    elif source == 'tdt' or 'dvb' in source:
        md = mplayer_get_meta(md, service='dvb')

    elif 'cd' in source:
        #md = mplayer_get_meta(md, service='cdda')
        md = mpd_meta(md)

    elif source.startswith('remote'):

        # For a 'remote.....' named source, it is expected to have
        # an IP address kind of in its jack_pname field:
        #   jack_pname:  X.X.X.X:PPPP
        # so this way we can query metadata from the remote address.
        host = SOURCES[source]["jack_pname"].split(':')[0]
        port = SOURCES[source]["jack_pname"].split(':')[-1]
        if is_IP(host):
            if not port.isdigit():
                port = 9990
            md = remote_get_meta( host, port )

    # If there is no artist, let's use the source name
    if not md['artist']:
        md['artist'] = f'- {source.upper()} -'

    return md


def playback_control(cmd, arg=''):
    """ Controls the playback, depending on the involved source player.
        returns: 'stop' | 'play' | 'pause'
    """

    def  check_mpd_playlist_is_cd():
        """ If the MPD playlist is NOT a CD kind of
            will load the CD playlist.
        """
        if not mpd_cdda_in_playlist('all'):

            mpd_playlists('clear_playlist')
            mpd_playlists('load_playlist',  f'cdda_{gethostname()}')


    result = 'stop'
    source = read_state_from_disk()['input']

    if 'mpd' in source.lower():
        result = mpd_control(cmd, arg)

    elif source.lower() == 'spotify':

        if   SPOTIFY_CLIENT == 'desktop':
            result = spotify_control(cmd, arg)

        elif SPOTIFY_CLIENT == 'librespot':
            result = librespot_control(cmd)

        else:
            result = 'stop'

    elif 'tdt' in source or 'dvb' in source:
        result = mplayer_control(cmd=cmd, service='dvb')

    elif source in ['istreams', 'iradio']:
        result = mplayer_control(cmd=cmd, service='istreams')

    elif source == 'cd':
        check_mpd_playlist_is_cd()
        result = mpd_control(cmd, arg)

    elif source.startswith('remote'):
        # For a 'remote.....' named source, it is expected to have
        # an IP address kind of in its jack_pname field:
        #   jack_pname:  X.X.X.X:PPPP
        # so this way we can query metadata from the remote address.
        host = SOURCES[source]["jack_pname"].split(':')[0]
        port = SOURCES[source]["jack_pname"].split(':')[-1]

        # (i) we assume that the remote pe.audio.sys listen at standard 9990 port
        if is_IP(host):
            if not port.isdigit():
                port = 9990
            result = remote_player_control( cmd=cmd, arg=arg, host=host, port=port )

    return result


def playlists_control(cmd, arg):
    """ Manage playlists.
        (i) Currently only works with: Spotify Desktop, MPD.
    """
    result = []
    source      = read_state_from_disk()['input']
    source_port = read_state_from_disk()['input_port']

    if 'mpd' in source or 'mpd' in source_port:

        if cmd == 'get_playlist':
            result = mpd_playlist()

        elif cmd == 'get_cd_track_nums':
            result = mpd_get_cd_track_nums()

        else:
            result = mpd_playlists(cmd, arg)

    elif source == 'spotify':

        if   SPOTIFY_CLIENT == 'desktop':
            result = spotify_playlists(cmd, arg)

    # 2024.11 not in use
    elif source == 'cd' and 'mplayer' in source_port:
        result = mplayer_playlists(cmd=cmd, arg=arg, service='cdda')

    return result


def random_control(arg):
    """ Controls the random/shuffle playback mode
        (i) Currently only works with: MPD
    """
    result = 'n/a'
    source = read_state_from_disk()['input']

    if source == 'mpd':
        result = mpd_control('random', arg)

    elif source == 'spotify':

        if   SPOTIFY_CLIENT == 'desktop':
            result = spotify_control('random', arg)
        elif SPOTIFY_CLIENT == 'librespot':
            result = librespot_control('random', arg)

    return result


def get_all_info():
    """ A wrapper to get all playback related info at once,
        useful for web control clients querying
    """
    return {
            'state':        playback_control( 'state' ),
            'random_mode':  random_control('get'),
            'metadata':     CURRENT_MD,
            'discid':       read_cdda_meta_from_disk()['discid']
            }


# Autoexec when loading this module
def loop_getting_metadata():
    """ This init function will thread the storing metadata LOOP FOREVER
    """

    def store_meta_loop(period=2):

        global CURRENT_MD

        while True:

            # Update the global runtime variable CURRENT_MD
            CURRENT_MD = get_meta()

            # Save metadata to disk file.
            with open(PLAYER_META_PATH, 'w') as f:
                f.write( json.dumps( CURRENT_MD ) )

            # Wait for period
            sleep(period)

    # Loop storing metadata
    period = MD_REFRESH_PERIOD
    meta_loop = threading.Thread( target=store_meta_loop, args=(period,) )
    meta_loop.start()


# Main interface function for this module
def do(cmd, arg):
    """ Entry interface function for a parent server.py listener.
        - in:   a command phrase
        - out:  a string result (dicts are json dumped)
    """

    result = f'(players.py) error with {cmd} {arg}'

    if cmd in ( 'state', 'stop', 'pause', 'play', 'next', 'previous',
                'rew', 'ff', 'play_track'):
        result = playback_control( cmd, arg )

    elif cmd == 'volume':
        result = playback_control( cmd, arg )

    elif cmd == 'random_mode':
        result = random_control(arg)

    elif cmd == 'get_meta':
        result = CURRENT_MD

    elif cmd == 'get_all_info':
        result = get_all_info()

    elif cmd == 'get_cd_track_nums':
        result = playlists_control( cmd, arg )

    elif '_playlist' in cmd:
        result = playlists_control( cmd, arg )

    # (i) Must be a clean eject
    elif cmd == 'eject':

        print(f'{Fmt.MAGENTA}(players.py) ejecting disc...{Fmt.END}')
        clear_cdda_stuff()
        Popen( 'eject'.split() )
        result = 'ordered'
        sleep(1)

    else:
        result = f'(players) unknown command \'{cmd}\''

    return result


# Autoexec when loading this module
loop_getting_metadata()
