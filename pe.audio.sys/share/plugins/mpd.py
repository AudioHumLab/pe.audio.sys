#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

"""
    A simple user session MPD launcher

    usage:  mpd.py   start | stop

    Notice:

        Some Desktop autostarts MPD when user logins, because of the packaged file:
            /etc/xdg/autostart/mpd.desktop
        If so, please set "X-GNOME-Autostart-enabled=false" inside this file.

"""
import sys
import os
from subprocess import Popen, call, check_output
from time import sleep
from getpass import getuser

UHOME = os.path.expanduser("~")
sys.path.append(f'{UHOME}/pe.audio.sys/share/miscel')

from miscel import read_mpd_config


def get_mpd_config_path():
    """ If the default MPD config file wants to use a mounted filesystem,
        this checks for it to be available, and if necessary will generate
        an alternative file .mpdconf.local

        returns: the .mpdconf path to run MPD with.
    """

    def do_mpd_conf_local():
        """ Makes a copy of .mpdconf but using a local `playlist_directory`
        """

        new_mpd_conf_path = MPD_CONF_PATH + '.local'

        new_local_pl_dir = f'{UHOME}/.config/mpd/playlists'

        with open(MPD_CONF_PATH, 'r') as f:
            mpdconfiglines = f.read().split('\n')

        for i, line in enumerate(mpdconfiglines):
            if 'playlist_directory' in line and line.strip()[0] != '#':
                mpdconfiglines[i] = f'playlist_directory      "{new_local_pl_dir}"'

        os.makedirs(new_local_pl_dir, exist_ok=True)

        with open(new_mpd_conf_path, 'w') as f:
            for line in mpdconfiglines:
                f.write( line + '\n' )


    MPD_CONF_PATH = f'{UHOME}/.mpdconf'

    MPD_PL_DIR  = read_mpd_config(MPD_CONF_PATH)["playlist_directory"]

    if not os.path.isdir( MPD_PL_DIR ):

        do_mpd_conf_local()
        MPD_CONF_PATH += '.local'

    return MPD_CONF_PATH


def check_systemd_service():
    """ Some mpd packages enables MPD user systemd units, when upgraded
    """
    try:
        # Any --value xxxx, even if non existent, will return "inactive"
        tmp = check_output("systemctl --user show -p ActiveState --value mpd.service",
                            shell=True).decode().strip()
    except Exception as e:
        tmp = ''
        print('(mpd.py)', e)

    if tmp == 'active':
        print('(mpd.py)', 'disabling systemd MPD service')
        tmp =  "systemctl --user stop mpd.socket &&"
        tmp += "systemctl --user stop mpd.service &&"
        tmp += "systemctl --user disable mpd.socket &&"
        tmp += "systemctl --user disable mpd.service"
        call( tmp, shell=True )


def stop():
    call( ['pkill', '-u', getuser() , '-KILL', '-f', f'mpd {UHOME}/.mpdconf'] )


def start():

    check_systemd_service()

    MPD_CONF_PATH = get_mpd_config_path()

    with open('/dev/null', 'w') as fnull:
        Popen( f'mpd {MPD_CONF_PATH}'.split(), stdout=fnull, stderr=fnull )


if __name__ == '__main__':

    if sys.argv[1:]:

        if sys.argv[1] == 'stop':
            stop()
        elif sys.argv[1] == 'start':
            stop()
            start()
        else:
            print(__doc__)

    else:
        print(__doc__)
