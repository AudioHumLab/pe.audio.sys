#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

""" A libresport interface module for players.py
    librespot is a Spotify Connect client:
    https://github.com/librespot-org/librespot
"""
import sys
import os
import subprocess as sp
import json

UHOME = os.path.expanduser("~")
MAINFOLDER = f'{UHOME}/pe.audio.sys'

sys.path.append(f'{MAINFOLDER}/share/miscel')
from miscel import time_sec2mmss, Fmt


def librespot_control(cmd, arg=''):
    """ (i) This is a fake control
        input:  a fake command
        output: the result is fixed for playlists and random mode,
                we can only retrive the player state from librespot printouts
    """
    if cmd == 'get_playlists':
        return []

    elif cmd == 'random':
        return 'n/a'

    elif 'state' in cmd:

        state = 'stop'
        try:
            with open(f'{MAINFOLDER}/.librespot_events', 'r') as f:
                lines = f.readlines()[-10:]

                # For the playing state (play/paused/stop) we get the last line
                for line in lines[::-1]:

                    # 'state' field
                    if '"PLAYER_EVENT"' in line:
                        envvars = '{' + line.split('{')[1]
                        state = json.loads(envvars)["PLAYER_EVENT"].lower()

                        if 'play' in state:
                            state = 'play'
                        elif 'paus' in state:
                            state = 'pause'
                        elif 'stop' in state:
                            state = 'stop'
                        else:
                            state = 'play'

                        break
        except:
            pass

        return state


def librespot_meta(md):
    """ Input:  blank md dict
        Output: metadata dict derived from librespot printouts
        I/O:    .librespot_events (r) - librespot redirected printouts
    """

    # Unfortunately librespot only prints out the title metadata,
    # nor artist neither album.
    # More info can be retrieved from the spotify web, but it is needed
    # to register for getting a privative and unique http request token
    # for authentication.

    # Gets librespot bitrate from librespot running process:
    try:
        tmp = sp.check_output('pgrep -fa bin/librespot'.split()).decode()
        # /bin/librespot ... --bitrate 320 ...
        librespot_bitrate = tmp.split('--bitrate')[1].split()[0].strip()
    except:
        librespot_bitrate = ''


    # Fixed metadata
    md['player'] = 'librespot'
    md['bitrate'] = librespot_bitrate
    md["format"]  = '44100:16:2'

    # Trying to complete metadata fields:
    try:
        # librespot messages are redirected to .librespot_events,
        # so we will search for the latest useful messages,  backwards
        # from the end of the events file:
        # ...
        # [2024-06-19T11:07:44Z INFO  librespot_playback::player] Loading <Shipbuilding - Remastered in 1998> with Spotify URI <spotify:track:7iG5yQkIIrd39mYWU2vT2b>
        # [2024-06-19T11:07:44Z INFO  librespot_playback::player] <Shipbuilding - Remastered in 1998> (184293 ms) loaded
        # [2024-06-19T11:07:44Z INFO  librespot::player_event_handler] Running ["/home/paudio/pe.audio.sys/share/plugins/librespot/bind_ports.sh"] with environment variables {"TRACK_ID": "7iG5yQkIIrd39mYWU2vT2b", "POSITION_MS": "0", "DURATION_MS": "184293", "PLAYER_EVENT": "playing"}
        # [2024-06-19T11:07:48Z INFO  librespot::player_event_handler] Running ["/home/paudio/pe.audio.sys/share/plugins/librespot/bind_ports.sh"] with environment variables {"POSITION_MS": "3336", "TRACK_ID": "7iG5yQkIIrd39mYWU2vT2b", "PLAYER_EVENT": "paused", "DURATION_MS": "184293"}
        # ...


        # player_event_handler  Only occurs when pausing/play/stop because nobody else pulls librespot
        #                       to update the "POSITION_MS" field, so we do not update this md field

        with open(f'{MAINFOLDER}/.librespot_events', 'r') as f:
            lines = f.readlines()[-30:]

            # Iterate over the lines of messages. Will do backwards,
            # because first line is the one containing " Loading "
            for line in lines[::-1]:

                # 'file' field
                if '] Loading <' in line:
                    # Rust cargo format:
                    md['file'] = line.split('Spotify URI <')[-1] \
                                      .split('>\n')[0]
                    break

                # 'title' field
                if line.endswith("loaded\n"):
                    # Rust cargo format:
                    if 'player] <' in line:
                        md['title'] = line.split('player] <')[-1] \
                                          .split('> (')[0]
                    # former loaded message format:
                    else:
                        md['title'] = line.split('player: Track "')[-1] \
                                          .split('" loaded')[0]
                # 'time_tot' field
                if '"DURATION_MS"' in line:
                    envvars = '{' + line.split('{')[1]
                    dur_ms = float(json.loads(envvars)["DURATION_MS"])
                    md['time_tot'] = time_sec2mmss(dur_ms/1000)

    except Exception as e:
        print(f'{Fmt.RED}(librespot.py) {str(e)}{Fmt.END}')


    return md
