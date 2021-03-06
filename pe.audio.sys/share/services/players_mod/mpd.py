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

""" A MPD interface module for players.py
"""
import os
import mpd

UHOME = os.path.expanduser("~")
MAINFOLDER = f'{UHOME}/pe.audio.sys'


# Auxiliary function to format hh:mm:ss
def timeFmt(x):
    # x must be float
    h = int( x / 3600 )         # hours
    x = int( round(x % 3600) )  # updating x to reamining seconds
    m = int( x / 60 )           # minutes from the new x
    s = int( round(x % 60) )    # and seconds
    return f'{h:0>2}:{m:0>2}:{s:0>2}'


def curr_playlist_is_cdda( port=6600 ):
    """ returns True if the curren playlist has only cdda tracks
    """
    # :-/ the current playlist doesn't have any kind of propiertry to
    # check if the special 'cdda.m3u' is the currently loaded one.

    c = mpd.MPDClient()
    try:
        c.connect('localhost', port)
    except:
        return False

    return [x for x in c.playlist() if 'cdda' in x ] == c.playlist()


def mpd_control( query, port=6600 ):
    """ Comuticates to MPD music player daemon
        Input:      a command to query to the MPD daemon
        Return:     playback state string
    """

    def state():
        return c.status()['state']

    def stop():
        c.stop()
        return c.status()['state']

    def pause():
        c.pause()
        return c.status()['state']

    def play():
        c.play()
        return c.status()['state']

    def next():
        try:
            c.next()  # avoids error if some playlist has wrong items
        except:
            pass
        return c.status()['state']

    def previous():
        try:
            c.previous()
        except:
            pass
        return c.status()['state']

    def rew():  # for REW and FF will move 30 seconds
        c.seekcur('-30')
        return c.status()['state']

    def ff():
        c.seekcur('+30')
        return c.status()['state']

    def listplaylists():
        return [ x['playlist'] for x in c.listplaylists() ]


    c = mpd.MPDClient()
    try:
        c.connect('localhost', port)
    except:
        return 'stop'

    result = {  'state':            state,
                'stop':             stop,
                'pause':            pause,
                'play':             play,
                'next':             next,
                'previous':         previous,
                'rew':              rew,
                'ff':               ff,
                'get_playlists':    listplaylists
             }[query]()

    c.close()
    return result


def mpd_meta( md, port=6600 ):
    """ Comuticates to MPD music player daemon
        Input:      blank metadata dict
        Return:     track metadata dict
    """

    md['player'] = 'MPD'

    c = mpd.MPDClient()
    try:
        c.connect('localhost', port)
    except:
        return md

    # (i) Not all tracks have complete currentsong() fields:
    # artist, title, album, track, etc fields may NOT be provided
    # file, time, duration, pos, id           are ALWAYS provided

    # Skip if no currentsong is loaded
    if c.currentsong():
        if 'artist' in c.currentsong():
            md['artist']    = c.currentsong()['artist']

        if 'album' in c.currentsong():
            md['album']     = c.currentsong()['album']

        if 'track' in c.currentsong():
            md['track_num'] = c.currentsong()['track']

        if 'time' in c.currentsong():
            md['time_tot']  = timeFmt( float( c.currentsong()['time'] ) )

        if 'title' in c.currentsong():
            md['title']     = c.currentsong()['title']
        elif 'file' in c.currentsong():
            md['title']     = c.currentsong()['file'].split('/')[-1]

    if 'playlistlength' in c.status():
        md['tracks_tot']    = c.status()['playlistlength']

    if 'bitrate' in c.status():
        md['bitrate']       = c.status()['bitrate']  # kbps

    if 'elapsed' in c.status():
        md['time_pos']      = timeFmt( float( c.status()['elapsed'] ) )

    if 'state' in c.status():
        md['state']         = c.status()['state']

    return md
