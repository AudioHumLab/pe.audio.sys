#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

"""
    A watchdog for USB external DAC with standby mode, e.g. a Topping DAC.

    (!) A fake jackd process may occur after the USB DAC was disconnected.

    If the USB DAC goes to standby, or if it becomes plugged off,
    the JACK server will get stuck.

    Then, this watchdog will stop pe.audio.sys. Also, as soon the USB DAC
    becomes available again, will restart pe.audio.sys.

    Usage:      peaudiosys_usb_dac_watchdog.py  start   1>/dev/null 2>&1 &

    (Use the above redirection to disconnect it from the console)

    (i) This plugin is NOT intended to be configured under the
        plugins section inside config.yml, PLEASE use a dedicated entry:

        usb_dac_watchdog = true

"""
import  subprocess as sp
import  os
import  sys
from    time     import sleep
from    datetime import datetime

UHOME = os.path.expanduser("~")
sys.path.append(f'{UHOME}/pe.audio.sys/share/miscel')

from miscel import  detect_USB_DAC, jack_lsp, CONFIG, LOG_FOLDER


CARD_NAME = CONFIG["jack"]["device"].split(':')[-1].split(',')[0]
LOGPATH   = f'{LOG_FOLDER}/usb_dac_watchdog.log'


def peaudiosys_restart():

    now = datetime.now().strftime("%Y%m%d_%H%M%S")

    with open(LOGPATH, 'w') as flog:
        flog.write(f'{now} (usb_dac_watchdog.py) RESTARTING pe.audio.sys ... .. .\n')
        flog.flush()
        sp.call(f'{UHOME}/bin/peaudiosys_restart.sh', shell=True,
                    stdout=flog, stderr=flog)


def peaudiosys_stop():

    now = datetime.now().strftime("%Y%m%d_%H%M%S")

    with open(LOGPATH, 'w') as flog:
        flog.write(f'{now} (usb_dac_watchdog.py) USB DAC \'{CARD_NAME}\' NOT detected, stopping pe.audio.sys\n')
        flog.write(f'{now} (usb_dac_watchdog.py) STOPPING pe.audio.sys ... .. .\n')
        flog.flush()
        sp.call(f'{UHOME}/bin/peaudiosys_restart.sh stop', shell=True,
                    stdout=flog, stderr=flog)


def main_loop():

    def jack_process(card_name):

        try:
            tmp = sp.check_output(f'pgrep -u {USER} -fla jackd'.split()).decode().strip()

        except:
            tmp = ''

        if card_name in tmp:
            return True

        else:
            return False


    def jack_response(card_name):

        result = False

        if jackd_process(card_name):

            if jack_lsp():
                result = True

        return result


    now = datetime.now().strftime("Y%m%d_%H%M%S")

    with open(LOGPATH, 'w') as flog:
        flog.write(f'{now} (usb_dac_watchdog.py) WATCHDOG STARTED.\n')

    while True:

        if detect_USB_DAC(CARD_NAME):

            if not jack_response(CARD_NAME):
                peaudiosys_restart()

        else:

            if jack_process(CARD_NAME):
                peaudiosys_stop()

        sleep(10)


if __name__ == "__main__":

    for opc in sys.argv[1:]:

        if 'start' in opc:
            main_loop()


    print(__doc__)
