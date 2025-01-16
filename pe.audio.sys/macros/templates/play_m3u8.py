#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

"""
    Plays an akamaized 'm3u8' playlist througby MPD

    Usage:  play_m3u8.py    station_name (*)

        (*) as per configured in config/istreams.yml


    This program is a loop that feeds the m3u8 chunks into the MPD playlist.
    If someone modifies the MPD playlist, then this loop will end.
"""

import  psutil
import  sys
import  os
import  yaml
import  mpd
import  m3u8
from    time import sleep
import  datetime

UHOME = os.path.expanduser("~")
sys.path.append( f'{UHOME}/pe.audio.sys/share/miscel' )

from miscel import kill_bill

MPD_PORT = 6600
LOG_PATH = f'{UHOME}/pe.audio.sys/log/play_m3u8.log'

mpdcli = mpd.MPDClient()


def mpd_connect(port=MPD_PORT):
    try:
        mpdcli.connect('localhost', port)
        return True
    except:
        return False


def mpd_ping():

    tries = 3

    while tries:

        try:
            mpdcli.ping()
            return True
        except:
            pass

        sleep(.2)
        tries -= 1

    return False


def get_m3u8_target_duration(url):
    try:
        pl =  m3u8.load(url, timeout=5)
        return pl.target_duration
    except:
        return 0


def get_m3u8_uris(url):
    try:
        pl =  m3u8.load(url, timeout=5)
        return [x.uri for x in pl.segments]
    except:
        return []


def get_url(station_name):

    def load_istreams():

        istreams_path = f'{UHOME}/pe.audio.sys/config/istreams.yml'

        try:
            with open(istreams_path, 'r') as f:
                return yaml.safe_load(f.read())
        except:
            return {}


    url = ''
    for k, v in load_istreams().items():
        if station_name == v["name"]:
            url = v["url"]
            break
    return url


def do_log(msg, to_console=True):

    now = datetime.datetime.now()
    # ISO timestamp without microseconds:
    time_stamp = now.isoformat(timespec='seconds')

    with open(LOG_PATH, 'a') as f:
        f.write(f'{time_stamp} {msg}\n')

    if to_console:
        print(msg)


if __name__ == "__main__":

    # Kills any previous instance of this loop
    kill_bill( os.getpid() )

    print()

    # Reading the desired station
    if not sys.argv[1:]:
        print(__doc__)
        sys.exit()

    station_name = sys.argv[1]

    radio_url = get_url(station_name)

    if not radio_url:
        do_log(f"'{station_name}': not found. Bye.")
        sys.exit()

    uris = get_m3u8_uris(radio_url)

    number_of_uris = len( uris )

    if not number_of_uris:
        do_log('Error reading M3U8')
        sys.exit()

    uri_root = uris[0][: uris[0].rindex('/')]

    ts_duration = get_m3u8_target_duration( radio_url )

    if not ts_duration:
        do_log(f'{station_name}: not a valid m3u8 url. Bye.')
        sys.exit()


    # Loading the M3U8 into MPD and playing it.
    do_log(f'Loading `{station_name}` into MPD playlist')

    if not mpd_connect():
        do_log('cannot connect to MPD. Bye.')
        sys.exit()

    mpdcli.clear()
    old_consume = mpdcli.status()["consume"]
    old_random  = mpdcli.status()["random"]
    mpdcli.consume(1)
    mpdcli.random(0)


    # At least 2 URIs will be kept loaded in the playlist

    loop_waiting = (number_of_uris - 2) * ts_duration

    try:

        do_log(f'MPD playing `{station_name}`')

        end_reason = ''

        # Repeat every near target duration
        while True:

            play_issued = False

            # Getting the MPD playlits, and discarding the prefix `file: `
            mpd_pl = [ x.split()[-1] for x in mpdcli.playlist() ]

            # Getting the URIs, which are changing over time
            uris = get_m3u8_uris(radio_url)

            # Exit if someone wants to play anything else
            if [ uri for uri in mpd_pl if not uri_root in uri ]:
                end_reason = 'The playing queue was modified'
                break

            for uri in uris:
                if not uri in mpd_pl:
                    mpdcli.add(uri)

            if not play_issued:
                mpdcli.play()
                play_issued = True

            if not mpd_ping():
                end_reason = 'MPD connection lost'
                break

            sleep(loop_waiting)

        if end_reason:
            do_log(f'{end_reason}')
        else:
            do_log(f'MPD playlist loop failed :-/')

    except KeyboardInterrupt:
        mpdcli.clear()
        mpdcli.consume(old_consume)
        mpdcli.random(old_random)
        do_log('\nInterrupted. Bye!')
