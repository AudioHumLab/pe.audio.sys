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

import socket
import ipaddress
import os
import jack
from json import loads as json_loads
from time import sleep
import subprocess as sp
import yaml
import configparser


UHOME = os.path.expanduser("~")
MAINFOLDER  = f'{UHOME}/pe.audio.sys'

# Some nice ANSI formats for printouts
# (PLEASE KEEP THIS class AT THE VERY BEGINNING)
class Fmt:
    """
    # CREDITS: https://github.com/adoxa/ansicon/blob/master/sequences.txt

    0         all attributes off
    1         bold (foreground is intense)
    4         underline (background is intense)
    5         blink (background is intense)
    7         reverse video
    8         concealed (foreground becomes background)
    22        bold off (foreground is not intense)
    24        underline off (background is not intense)
    25        blink off (background is not intense)
    27        normal video
    28        concealed off
    30        foreground black
    31        foreground red
    32        foreground green
    33        foreground yellow
    34        foreground blue
    35        foreground magenta
    36        foreground cyan
    37        foreground white
    38;2;#        foreground based on index (0-255)
    38;5;#;#;#    foreground based on RGB
    39        default foreground (using current intensity)
    40        background black
    41        background red
    42        background green
    43        background yellow
    44        background blue
    45        background magenta
    46        background cyan
    47        background white
    48;2;#        background based on index (0-255)
    48;5;#;#;#    background based on RGB
    49        default background (using current intensity)
    90        foreground bright black
    91        foreground bright red
    92        foreground bright green
    93        foreground bright yellow
    94        foreground bright blue
    95        foreground bright magenta
    96        foreground bright cyan
    97        foreground bright white
    100       background bright black
    101       background bright red
    102       background bright green
    103       background bright yellow
    104       background bright blue
    105       background bright magenta
    106       background bright cyan
    107       background bright white
    """

    BLACK           = '\033[30m'
    RED             = '\033[31m'
    GREEN           = '\033[32m'
    YELLOW          = '\033[33m'
    BLUE            = '\033[34m'
    MAGENTA         = '\033[35m'
    CYAN            = '\033[36m'
    WHITE           = '\033[37m'

    BRIGHTBLACK     = '\033[90m'
    BRIGHTRED       = '\033[91m'
    BRIGHTGREEN     = '\033[92m'
    BRIGHTYELLOW    = '\033[93m'
    BRIGHTBLUE      = '\033[94m'
    BRIGHTMAGENTA   = '\033[95m'
    BRIGHTCYAN      = '\033[96m'
    BRIGHTWHITE     = '\033[97m'

    BOLD        = '\033[1m'
    UNDERLINE   = '\033[4m'
    BLINK       = '\033[5m'
    END         = '\033[0m'


# CONFIG & SERVER ADDRESSING
with open(f'{MAINFOLDER}/config.yml', 'r') as f:
    CONFIG = yaml.safe_load(f)
try:
    SRV_HOST, SRV_PORT = CONFIG['peaudiosys_address'], CONFIG['peaudiosys_port']
except:
    print(f'{Fmt.RED}(share.miscel) ERROR reading address/port in '
          f'\'config.yml\'{Fmt.END}')
    exit()

# COMMON USE VARIABLES FROM 'config.yml'
LOUDSPEAKER     = CONFIG['loudspeaker']
LSPK_FOLDER     = f'{MAINFOLDER}/loudspeakers/{LOUDSPEAKER}'
if 'amp_manager' in CONFIG:
    AMP_MANAGER =  CONFIG['amp_manager']
else:
    AMP_MANAGER =  ''


# Retrieve loudspeaker's filters FS from its Brutefir configuration
def get_Bfir_sample_rate():
    """ Retrieve loudspeaker's filters FS from its 'brutefir_config' file,
        or from '.brutefir_defaults' file
    """
    FS = 0

    for fname in (f'{LSPK_FOLDER}/brutefir_config',
                  f'{UHOME}/.brutefir_defaults'):
        with open(fname, 'r') as f:
            lines = f.readlines()
        for l in lines:
            if 'sampling_rate:' in l and l.strip()[0] != '#':
                try:
                    FS = int([x for x in l.replace(';', '').split()
                                         if x.isdigit() ][0])
                except:
                    pass
        if FS:
            break   # stops searching if found under lskp folder

    if not FS:
        raise ValueError('unable to find Brutefir sample_rate')

    if 'brutefir_defaults' in fname:
        print(f'{Fmt.RED}{Fmt.BOLD}'
              f'(miscel.py) *** USING .brutefir_defaults SAMPLE RATE ***'
              f'{Fmt.END}')

    return FS


# Checks for JACK process to be running
def jack_is_running():
    try:
        sp.check_output('jack_lsp >/dev/null 2>&1'.split())
        return True
    except sp.CalledProcessError:
        return False


# Sets a peaudiosys parameter as per a given pattern, useful for user macros.
def set_as_pattern(param, pattern, sender='miscel', verbose=False):
    """ Sets a peaudiosys parameter as per a given pattern.
        This applies only for 'xo', 'drc' and 'target'
    """
    result = ''

    if param not in ('xo', 'drc', 'target'):
        return "parameter mus be 'xo', 'drc' or 'target'"

    sets = send_cmd(f'get_{param}_sets')

    try:
        sets = json_loads( sets )
    except:
        return result

    for setName in sets:

        if pattern in setName:
            result = send_cmd( f'set_{param} {setName}',
                               sender=sender, verbose=verbose )
            break

    return result


# Waiting for jack ports to be available
def wait4ports(pattern):
    """ Waits for jack ports to be available
    """
    JC = jack.Client('miscel', no_start_server=True)
    n = 20  # 10 sec
    while n:
        if len( JC.get_ports( pattern ) ) >= 2:
            break
        n -= 1
        sleep(0.5)
    JC.close()
    if n:
        return True
    else:
        return False


# Send a command to a peaudiosys server
def send_cmd( cmd, sender='', verbose=False, timeout=60,
              host=SRV_HOST, port=SRV_PORT ):
    """ send commands to a pe.audio.sys server
    """
    # (i) socket timeout 60 because Brutefir can need some time
    #     in slow machines after powersave shot it down.

    if not sender:
        sender = 'share.miscel'

    # Default answer: "no answer from ...."
    ans = f'no answer from {host}:{port}'

    # (i) We prefer high-level socket function 'create_connection()',
    #     rather than low level 'settimeout() + connect()'
    try:
        with socket.create_connection( (host, port), timeout=timeout ) as s:
            s.send( cmd.encode() )
            if verbose:
                print( f'{Fmt.BLUE}({sender}) Tx: \'{cmd}\'{Fmt.END}' )
            ans = ''
            while True:
                tmp = s.recv(1024).decode()
                if not tmp:
                    break
                ans += tmp
            if verbose:
                print( f'{Fmt.BLUE}({sender}) Rx: \'{ans}\'{Fmt.END}' )
            s.close()

    except Exception as e:
        if verbose:
            print( f'{Fmt.RED}({sender}) {host}:{port} {e} {Fmt.END}' )

    return ans


# Checks the Mplayer config file
def check_Mplayer_config_file(profile='istreams'):
    """ Checks the Mplayer config file
    """
    cpath = f'{UHOME}/.mplayer/config'

    # This never happens because Mplayer autodumps an empty .mplayer/config file
    if not os.path.exists(cpath):
        return f'ERROR Mplayer config file not found'

    mplayercfg = configparser.ConfigParser()
    try:
        mplayercfg.read( cpath )
    except:
        return f'ERROR bad Mplayer config file'

    if not profile in mplayercfg:
        return f'ERROR Mplayer profile \'{profile}\' not found'
    if 'ao' in mplayercfg[profile] and \
        mplayercfg[profile]['ao'].strip()[:9] == 'jack:name':
        return 'ok'
    else:
        return f'ERROR bad Mplayer profile \'{profile}\''


# Auxiliary to detect the Spotify Client in use: desktop or librespot
def detect_spotify_client(timeout=10):
    """ the timeout will wait some seconds for the client to be running
    """
    result = ''

    # early return if no Spotify script is used:
    if not any( 'spo' in x.lower() for x in CONFIG['scripts'] ):
        return result

    tries = timeout
    while tries:
        try:
            sp.check_output( 'pgrep -f Spotify'.split() )
            result = 'desktop'
        except:
            pass
        try:
            sp.check_output( 'pgrep -f librespot'.split() )
            result = 'librespot'
        except:
            pass
        if result:
            return result
        else:
            tries -= 1
            sleep(1)

    return result


# Kill previous instaces of a process
def kill_bill(pid=0):
    """ Killing previous instances of a process as per its <pid>.
        This is mainly used from start.py.
    """

    if not pid:
        print( f'{Fmt.BOLD}(miscel) ERROR kill_bill() needs <pid> '
               f'(process own pid) as argument{Fmt.END}' )
        return

    # Retrieving the process string that identifies the given pid
    tmp = ''
    try:
        tmp = sp.check_output( f'ps -p {pid} -o command='.split() ).decode()
        # e.g. "python3 pe.audio.sys/start.py all"
    except:
        print( f'{Fmt.BOLD}(miscel) ERROR kill_bill() cannot found pid: {pid} ' )
        return

    # As per this is always used from python3 programs, will remove python3
    # and arguments
    # e.g. "python3 pe.audio.sys/start.py all"  -->  "pe.audio.sys/start.py"
    processString = tmp.replace('python3', '').strip().split()[0]

    # List processes like this one
    rawpids = []
    cmd =   f'ps -eo etimes,pid,cmd' + \
            f' | grep "{processString}"' + \
            f' | grep -v grep'
    try:
        rawpids = sp.check_output(cmd, shell=True).decode().split('\n')
    except sp.CalledProcessError:
        pass
    # Discard blanks and strip spaces:
    rawpids = [ x.strip().replace('\n', '') for x in rawpids if x ]
    # A 'rawpid' element has 3 fields 1st:etimes 2nd:pid 3th:comand_string

    # Removing the own pid
    for rawpid in rawpids:
        if rawpid.split()[1] == str(pid):
            rawpids.remove(rawpid)

    # Just display the processes to be killed, if any.
    print('-' * 21 + f' (miscel) killing \'{processString}\' running before me ' \
           + '-' * 21)
    for rawpid in rawpids:
        print(rawpid)
    print('-' * 80)

    if not rawpids:
        return

    # Extracting just the 'pid' at 2ndfield [1]:
    pids = [ x.split()[1] for x in rawpids ]

    # Killing the remaining pids, if any:
    for pid in pids:
        print(f'(miscel) killing old \'{processString}\' processes:', pid)
        sp.Popen(f'kill -KILL {pid}'.split())
        sleep(.1)
    sleep(.5)


# Gets the selected source from a pe.audio.sys server at <addr>
def get_source_from_remote(addr):
    """ Gets the selected source from a pe.audio.sys server at <addr>
    """
    source = ''
    ans = send_cmd('state', timeout=.5, host=addr)
    if 'no answer' in ans:
        return source
    try:
        source = json_loads(ans)["input"]
    except:
        pass
    return source


# Read the last line from a large file, efficiently.
def read_last_line(filename=''):
    # source:
    # https://stackoverflow.com/questions/46258499/read-the-last-line-of-a-file-in-python
    # For large files it would be more efficient to seek to the end of the file,
    # and move backwards to find a newline.
    # Note that the file has to be opened in binary mode, otherwise,
    # it will be impossible to seek from the end.

    if not filename:
        return ''

    try:
        with open(filename, 'rb') as f:
            f.seek(-2, os.SEEK_END)
            while f.read(1) != b'\n':
                f.seek(-2, os.SEEK_CUR)
            last_line = f.readline().decode()
        return last_line.strip()

    except:
        return ''


# Validate if a given string is a valid IP address
def is_IP(s):
    try:
        ipaddress.ip_address(s)
        return True
    except:
        return False


# Aux to get my own IP address
def get_my_ip():
    try:
        tmp = sp.check_output( 'hostname --all-ip-addresses'.split() ).decode()
        return tmp.split()[0]
    except:
        return ''
