#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

"""
    A pe.audio.sys daemon to autoplay a CD-Audio when inserted

    Usage:  autoplay_cdda.py  start | stop  &

    (needs:  udisks2, usbmount)
"""

import  os
import  sys
import  pyudev
from    time        import sleep
from    socket      import gethostname
from    subprocess  import check_output, Popen, run

UHOME = os.path.expanduser("~")
sys.path.append(f'{UHOME}/pe.audio.sys/share/miscel')

from    miscel  import send_cmd, USER, CONFIG
from    cdda    import dump_cdda_metadata


# autoplay mode: if False will only load the disc.
AUTO_PLAY = True


# To check your devices from command line:
# $ udevadm monitor
# ... ...
# UDEV  [5336.857159] change   /devices/pci0000:00/0000:00:1f.1/ata1/host0/target0:0:0/0:0:0:0/block/sr0 (block)
# UDEV  [5358.454256] change   /devices/pci0000:00/0000:00:1d.7/usb5/5-6/5-6:1.0/host4/target4:0:0/4:0:0:0/block/sr1 (block)


# Some distros as Ubuntu 18.04 LTS doesn't have
# libcdio-dev >=2.0 as required from pycdio.
#import cdio, pycdio
# (i) pycdio dependencies:
#       python-dev libcdio-dev libiso9660-dev swig pkg-config
# Workaround: lets use 'cdinfo' from 'cdtool' package (cdrom command line tools)


ME = 'autoplay_cdda'


def clear_CDDA():
    """ clear the player queue (needed only if MPD is used to play CD Audio)
    """
    if 'mpd' in CONFIG['sources']['cd']['jack_pname']:
        Popen( f'mpc clear'.split() )


def load_CDDA():

    if 'mpd' in CONFIG['sources']['cd']['jack_pname']:
        run('mpc clear'.split())
        run('mpc consume off'.split())
        run(f'mpc load cdda_{gethostname()}'.split())

    send_cmd( 'player pause', sender=ME, verbose=True )
    send_cmd( 'aux warning clear', sender=ME, verbose=True, timeout=1 )
    send_cmd( 'aux warning set disc loading ...', sender=ME, verbose=True, timeout=1 )
    send_cmd( 'aux warning expire 10', sender=ME, verbose=True, timeout=1 )
    send_cmd( 'preamp input cd', sender=ME, verbose=True )
    sleep(.5)

    # (!) Ordering 'play' will BLOCK the server while
    #     waiting for the disc to be loaded
    if AUTO_PLAY:
        send_cmd( 'player play', sender=ME, verbose=True )


def check_for_CDDA(d):

    srDevice = d.device_path.split('/')[-1]
    CDROM = f'/dev/{srDevice}'

    # Verbose if not CDDA detected
    try:
        # $ cdinfo -a # will output: no_disc | data_disc | xx:xx.xx
        tmp = check_output( f'cdinfo -a -d {CDROM}'.split() ).decode().strip()

        # CD-Audio detected
        if ':' in tmp:

            # dumping metadata to a file to be used later from the underlaying player
            dump_cdda_metadata()
            print( f'(autoplay_cdda) trying to load the CD Audio' )
            load_CDDA()

        # Data disc
        elif 'data_disc' in tmp:
            print( f'(autoplay_cdda) data disc' )
            clear_CDDA()

        # No disc
        elif 'no_disc' in tmp:
            print( f'(autoplay_cdda) no disc' )
            clear_CDDA()


    except Exception as e:
        print( f'(autoplay_cdda) {str(e)}' )
        print( f'(autoplay_cdda) This plugin needs \'cdtool\' (command line cdrom tool)' )


def stop():
    Popen( ['pkill', '-u', USER, '-KILL', '-f', 'autoplay_cdda.py start'] )


def main():
    # Main observer daemon
    context = pyudev.Context()
    umonitor = pyudev.Monitor.from_netlink(context)
    umonitor.filter_by(subsystem='block', device_type='disk')
    uobserver = pyudev.MonitorObserver( umonitor, callback=check_for_CDDA )
    uobserver.daemon = False  # set False will block the process when started.
    uobserver.start()


if __name__ == '__main__':

    if sys.argv[1:]:
        if sys.argv[1] == 'start':
            main()
        elif sys.argv[1] == 'stop':
            stop()
        else:
            print(__doc__)
    else:
        print(__doc__)
