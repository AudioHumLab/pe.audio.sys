#!/usr/bin/env python3
"""
    ALSA cards visualizer

    usage:      peaudiosys_alsa_cards.py  [--loop] [--nouse] [pattern]

                --nouse     omits showing the process using the device
"""

import  os
import  sys
from    time import sleep
from    subprocess import check_output


class Fmt:
    """
    # Some nice ANSI formats for printouts formatting
    # CREDITS: https://github.com/adoxa/ansicon/blob/master/sequences.txt

    0           all attributes off
    1           bold (foreground is intense)
    4           underline (background is intense)
    5           blink (background is intense)
    7           reverse video
    8           concealed (foreground becomes background)
    22          bold off (foreground is not intense)
    24          underline off (background is not intense)
    25          blink off (background is not intense)
    27          normal video
    28          concealed off
    30          foreground black
    31          foreground red
    32          foreground green
    33          foreground yellow
    34          foreground blue
    35          foreground magenta
    36          foreground cyan
    37          foreground white
    38;2;#      foreground based on index (0-255)
    38;5;#;#;#  foreground based on RGB
    39          default foreground (using current intensity)
    40          background black
    41          background red
    42          background green
    43          background yellow
    44          background blue
    45          background magenta
    46          background cyan
    47          background white
    48;2;#      background based on index (0-255)
    48;5;#;#;#  background based on RGB
    49          default background (using current intensity)
    90          foreground bright black
    91          foreground bright red
    92          foreground bright green
    93          foreground bright yellow
    94          foreground bright blue
    95          foreground bright magenta
    96          foreground bright cyan
    97          foreground bright white
    100         background bright black
    101         background bright red
    102         background bright green
    103         background bright yellow
    104         background bright blue
    105         background bright magenta
    106         background bright cyan
    107         background bright white
    """

    BLACK           = '\033[30m'
    RED             = '\033[31m'
    GREEN           = '\033[32m'
    YELLOW          = '\033[33m'
    BLUE            = '\033[34m'
    MAGENTA         = '\033[35m'
    CYAN            = '\033[36m'
    WHITE           = '\033[37m'
    GRAY            = '\033[90m'

    BRIGHTBLACK     = '\033[90m'
    BRIGHTRED       = '\033[91m'
    BRIGHTGREEN     = '\033[92m'
    BRIGHTYELLOW    = '\033[93m'
    BRIGHTBLUE      = '\033[94m'
    BRIGHTMAGENTA   = '\033[95m'
    BRIGHTCYAN      = '\033[96m'
    BRIGHTWHITE     = '\033[97m'

    BOLD            = '\033[1m'
    UNDERLINE       = '\033[4m'
    BLINK           = '\033[5m'
    END             = '\033[0m'


def get_devs_snd_use():

    #   $ fuser -v /dev/snd/*
    #                        USER        PID ACCESS COMMAND
    #   /dev/snd/controlC0:  rafax     10221 F.... jackd
    #                        rafax     20655 F.... python3
    #   /dev/snd/controlC3:  rafax      1705 F.... pulseaudio
    #   /dev/snd/pcmC0D0c:   rafax     10221 F...m jackd
    #   /dev/snd/pcmC0D0p:   rafax     10221 F...m jackd
    #   /dev/snd/pcmC1D0c:   rafax     10253 F...m zita-a2j
    #   /dev/snd/pcmC3D1p:   rafax     10254 F...m zita-j2a


    d = {}

    # (!) fuser outputs to both stdout and stderr
    cmd = 'fuser -v /dev/snd/* 2>&1'

    try:
        tmp = check_output(cmd, shell=True).decode().strip()

    except Exception as e:

        # Normal behavior if none in use:
        # Command 'fuser -v /dev/snd/* 2>&1' returned non-zero exit status 1.
        if not 'returned non-zero exit status 1' in str(e):
            print(f"error with fuser: {str(e)}")

        return d

    # skip first line
    for line in tmp.split('\n')[1:]:

        if ':' in line:

            dev  = line.split(':')[0].strip()
            user = line.split()[1].strip()
            pid  = line.split()[2].strip()
            cmd  = line.split()[-1].strip()

            d[dev] = [(user, pid, cmd)]

        else:

            user = line.split()[0].strip()
            pid  = line.split()[1].strip()
            cmd  = line.split()[-1].strip()

            d[dev].append( (user, pid, cmd) )

    # Example:
    #  {'/dev/snd/controlC0': [('rafax', '10221', 'jackd'), ('rafax', '20655', 'python3')], ..., ..., ....}

    return d


def get_sound_cards():

    #   $ cat /proc/asound/cards
    #    0 [DX             ]: AV200 - Xonar DX
    #                         Asus Virtuoso 100 at 0xee00, irq 16
    #    1 [ICUSBAUDIO7D   ]: USB-Audio - ICUSBAUDIO7D
    #                         ICUSBAUDIO7D at usb-0000:00:1a.0-1.2, full speed
    #    2 [ESIROMIO       ]: USB-Audio - ESI-ROMIO
    #                         Ego Systems Inc ESI-ROMIO at usb-0000:04:00.0-1.4, full speed
    #    3 [PCH            ]: HDA-Intel - HDA Intel PCH
    #                         HDA Intel PCH at 0xfbff4000 irq 34
    #    4 [Velvet         ]: USB-Audio - E70 Velvet
    #                         Topping E70 Velvet at usb-0000:00:1a.0-1.3, high speed

    cards = []

    with open("/proc/asound/cards", "r") as f:
        lines = f.readlines()

    for l in lines:
        if "[" in l:
            index = l.split("[")[0].strip()
            name  = l.split('[')[-1].split(']')[0].strip()
            cards.append( {'index': index, 'name': name})

    # Example:
    # [('0', 'DX'), ('1', 'ICUSBAUDIO7D'), ('2', 'ESIROMIO'), ('3', 'PCH'), ('4', 'Velvet')]

    return cards


def get_card_pcms(card):

    # cat /proc/asound/CODEC/pcm0p/sub0/hw_params
    # access: MMAP_INTERLEAVED
    # format: S16_LE
    # subformat: STD
    # channels: 2
    # rate: 48000 (48000/1)
    # period_size: 4096
    # buffer_size: 12288

    pcms = {}

    c_dir = f"/proc/asound/{card['name']}"

    c_files = os.listdir(c_dir)

    for c_file in c_files:

        if c_file[:3] == "pcm":

            pcm = c_file

            pcm_items = os.listdir(c_dir + "/" + pcm)

            for pcm_item in pcm_items:

                if pcm_item[:3] == "sub":

                    state = {'access': 'CLOSED'}

                    pcm_sub = f"{pcm}/{pcm_item}"

                    with open(f"{c_dir}/{pcm_sub}/hw_params", "r") as f:
                        hw_params = f.readlines()

                    for line in hw_params:
                        if ':' in line:
                            k, v = line.strip().split(':')
                            state[k.strip()] = v.strip()

            pcms[pcm_sub] = state

    return pcms


def list_cards(pattern=''):

    def get_pcm_use(alsa_index, alsa_pcm):
        """
            example of alsa_pcm:            pcm0c/sub0
                                               ^----------------    device

            example in devs_snd_use:        /dev/snd/pcmC0D0c
                                                            ^---    type
                                                           ^----    device
                                                         ^------    card
        """

        c = alsa_index                      # card
        d = alsa_pcm.split('/')[0][-2]      # dev
        t = alsa_pcm.split('/')[0][-1]      # type (c)ap / (p)bk

        dev_id = f"/dev/snd/pcmC{c}D{d}{t}"

        if dev_id in devs_snd_use:
            return devs_snd_use[dev_id]
        else:
            return []


    if get_use:
        print(" # CARD                 PCM          ACCESS               FORMAT       CH  RATE    PER.  BUFF. USER       PID      COMMAND")
        print("------------------------------------------------------------------------------------------------------------------------------")
        #       1 ICUSBAUDIO7D         pcm0c/sub0   MMAP_INTERLEAVED     S16_LE STD    2  48000    256  512 somebody   12345    someprocess
        #       1 ICUSBAUDIO7D         pcm0p/sub0   CLOSED

        devs_snd_use = get_devs_snd_use()

    else:
        print(" # CARD                 PCM          ACCESS               FORMAT       CH  RATE    PER.  BUFF.")
        print("----------------------------------------------------------------------------------------------")
        #       1 ICUSBAUDIO7D         pcm0c/sub0   MMAP_INTERLEAVED     S16_LE STD    2  48000    256  512
        #       1 ICUSBAUDIO7D         pcm0p/sub0   CLOSED
        devs_snd_use = {}


    for card in cards:

        if not pattern.lower() in card['name'].lower():
            continue

        pcms = get_card_pcms(card)

        for pcm_name, pcm_state in pcms.items():

            COLOR = Fmt.GRAY
            COEND = Fmt.END

            c_index = c_name = bits = channels = rate = period = buff = ''

            c_index  = card['index']
            c_name   = card['name']
            access   = pcm_state['access']

            if access.lower() != 'closed':

                bits     = f"{pcm_state['format']} {pcm_state['subformat']}"
                channels = pcm_state['channels']
                rate     = pcm_state['rate'].split()[0]
                period   = pcm_state['period_size']
                buff     = pcm_state['buffer_size']

                COLOR = Fmt.BLUE

                if 'c/' in pcm_name:
                    COLOR = Fmt.MAGENTA

            user = pid = cmd = ''
            more_uses = []

            if get_use:

                uses = get_pcm_use(c_index, pcm_name)

                if uses:

                    # First use to be printed in-line (usually the only and one)
                    user, pid, cmd = uses[0]

                    # if more uses were found (rare cases)
                    for use in uses[1:]:
                        more_uses.append( use )

            # main sound device line to be printed
            print(  f"{COLOR}{c_index.rjust(2)}",
                    c_name.ljust(20),
                    pcm_name.ljust(12),
                    access.ljust(20), bits.ljust(12), channels.rjust(2),
                    rate.rjust(6), period.rjust(6), buff.rjust(6),
                    user.ljust(10), pid.ljust(8), cmd,
                    COEND)

            # extra uses of the sound device
            for mu in more_uses:
                user, pid, cmd = use
                print( f"{COLOR}{' '*94}", user.ljust(10), pid.ljust(8), cmd, COEND)


def do_loop():

    while True:

        try:
            #print("\033c")
            os.system('clear')
            list_cards(pattern)
            sleep(1)

        except:
            return


if __name__ == "__main__":

    pattern   = ''
    loop_mode = False
    get_use   = True

    for opc in sys.argv[1:]:

        if '-h' in opc:
            print(__doc__)
            sys.exit()

        elif '-l' in opc:
            loop_mode = True

        elif '-n' in opc:
            get_use = False

        else:
            pattern = opc


    cards = get_sound_cards()

    if cards:

        if loop_mode:
            do_loop()

        else:
            list_cards(pattern)

    else:
        print('NO CARDS DETECTED.')
