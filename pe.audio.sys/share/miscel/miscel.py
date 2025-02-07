#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

""" This module provides common usage functions
"""

import  socket
import  ipaddress
from    json import loads as json_loads, dumps as json_dumps
from    time import sleep
from    datetime import datetime
import  subprocess as sp
import  configparser
import  os
import  threading
import  psutil
import  inspect
import  shlex
import  jack

from    config      import  *
from    fmt         import  Fmt
from    sound_cards import  release_cards_from_pulseaudio


# --- MPD auxiliary

def get_running_mpd_config_path():

    result = f'{UHOME}/.mpdconf'

    # Example: [{'pid': 12430, 'cmdline': ['mpd', '/home/paudio/.mpdconf.local']}]
    mpd_processes = get_pid_cmdline('mpd')

    # If more tan one, raise an Exception
    if len(mpd_processes) > 1:

        msg = 'More than ONE `mpd` process is running'
        print(f'{Fmt.BOLD}(start) msg{Fmt.END}')
        raise Exception(msg)

    elif len(mpd_processes) == 1:

        # mpd [options] [conf_file]: it is always the last parameter
        if len( mpd_processes[0]['cmdline'] ) > 1:
            result = mpd_processes[0]['cmdline'][-1]

    else:
        msg = 'mpd process NOT detected'
        print(f'{Fmt.RED}(start) msg{Fmt.END}')

    return result


def read_mpd_config(mpd_config_path=''):
    """ mpd clients CANNOT access to MPD.config(),
        so them needs to rely in reading the mpd config file

        If no `mpd_config_path` is given, then will look for
        the one used by the running MPD process.
    """

    def strip(x):
        """ removes " for config values
        """

        if type(x) != str:
            return x

        if x[0] == '"' and x[-1] == '"':
            return x[1:-1]


    config = {'port': 6600, 'playlist_directory': f'{UHOME}/.config/mpd/playlists'}


    if not mpd_config_path:
        mpd_config_path = get_running_mpd_config_path()


    with open(mpd_config_path, 'r') as f:

        lexer = shlex.shlex(f)
        lexer.wordchars += ".-/" # Important for file paths etc.

        section = None

        while True:

            try:
                token = lexer.get_token()
                if not token:
                    break  # End of file
                if token == '{':
                    continue
                if token == '}':
                    section = None
                    continue
                next_token = lexer.get_token()
                if next_token == '{':
                    section = token
                    config.setdefault(section, {})
                    continue
                if next_token:
                    if next_token.lower() in ("yes", "true", "1"):
                        next_token = True
                    elif next_token.lower() in ("no", "false", "0"):
                        next_token = False
                    if section:
                        config[section][token] = strip(next_token)
                    else:
                        config[token] = strip(next_token)

            except ValueError:
                print(f"Error parsing line {lexer.lineno}: {lexer.error_leader()}")
                return {}

            except EOFError: # shlex sometimes raises EOFError
                break

    return config


# --- pe.audio.sys common usage functions:

def detect_USB_DAC(cname):
    """ Check if the provided card name is available,
        and if it is USB type.
    """
    result = False
    tmp = sp.check_output('aplay -l'.split()).decode().strip().split('\n')
    for line in tmp:
        if cname in line and 'USB' in line.upper():
            result = True
    return result


def load_extra_cards(config=CONFIG, channels=2):
    """ This launch resamplers that connects extra sound cards into Jack
        (void)
    """
    jc = config["jack"]
    if ('external_cards' not in jc) or (not jc["external_cards"]):
        return

    ext_cards = jc["external_cards"]

    for card, params in ext_cards.items():
        jack_name = card
        device    = params['device']
        resampler = params['resampler']

        if ('resamplingQ' in params) and (params['resamplingQ']):
            quality = params['resamplingQ']
        else:
            quality = ''

        if ('misc_params' in params) and (params['misc_params']):
            misc = params['misc_params']
        else:
            misc = ''

        if (not quality) and ('zita' in resampler):
                quality == 'auto'

        cmd = f'{resampler} -d {device} -j {jack_name} -c {channels}'

        if quality:
            cmd += f' -q {quality}'

        if misc:
            cmd += f' {misc}'

        if 'zita' in resampler:
            cmd = cmd.replace("-q", "-Q")

        print(f'(start) loading resampled extra card: {card}')
        sp.Popen(cmd, shell=True, stdout=sys.stdout, stderr=sys.stderr)


def start_jack_stuff(config=CONFIG):
    """ runs jackd with configured options, jack loops and extrernal cards ports
        (void)
    """
    warnings = ''

    jc = config['jack']

    # silent (no Xrun messages)
    if ('silent' in jc) and (jc["silent"] == True):
        jOpts = f'-R --silent -d {jc["backend"]}'
    else:
        jOpts = f'-R -d {jc["backend"]}'

    # default period and nperiod
    if ('period' not in jc) or not jc["period"]:
        jc["period"] = 1024
    if ('nperiods' not in jc) or not jc["nperiods"]:
        jc["nperiods"] = 2

    if jc["backend"] != 'dummy':
        jBkndOpts  = f'-d {jc["device"]} -p {jc["period"]} -n {jc["nperiods"]}'
    else:
        jBkndOpts  = f'-p {jc["period"]}'

    # set FS
    jBkndOpts += f' -r {CONFIG["sample_rate"]}'

    # other backend options (config.yml)
    if ('miscel' in jc) and (jc["miscel"]):
        jBkndOpts += f' {jc["miscel"]}'

    # Use 'softmode' for ALSA backend even if not configured under 'miscel:'
    # (i) This does not disable Xrun printouts if any occurs (see man page)
    if ('alsa' in jOpts) and ('-s' not in jBkndOpts):
        jBkndOpts += ' --softmode'

    # Firewire: reset the Firewire Bus and run ffado-dbus-server
    if jc["backend"] == 'firewire':
        print(f'{Fmt.BOLD}(start) resetting the FIREWIRE BUS, sorry for users '
              f'using other FW things :-|{Fmt.END}')
        sp.Popen('ffado-test BusReset'.split())
        sleep(1)
        print(f'{Fmt.BLUE}(start) running FIREWIRE DBUS SERVER ...{Fmt.END}')
        sp.Popen('killall -KILL ffado-dbus-server', shell=True)
        sp.Popen('ffado-dbus-server 1>/dev/null 2>&1', shell=True)
        sleep(2)

    # Pulseaudio
    if 'pulseaudio' in sp.check_output("pgrep -fl pulseaudio", shell=True).decode():
        release_cards_from_pulseaudio()

    # Launch JACKD process
    with open(f'{LOG_FOLDER}/jackd.log', 'w') as jlog:
        sp.Popen(f'jackd {jOpts} {jBkndOpts}', shell=True,
                        stdout=jlog,
                        stderr=jlog)

    # Will check if JACK ports are available
    sleep(1)
    tries = 10
    while tries:
        if jack_lsp():
            print(f'{Fmt.BOLD}{Fmt.BLUE}(start) JACKD STARTED{Fmt.END}')
            break
        print(f'(start) waiting for jackd ' + '.' * tries)
        sleep(.5)
        tries -= 1
    # Still will wait a few, convenient for fast CPUs
    sleep(.5)

    if not tries:
        # JACK FAILED :-/
        warnings += ' JACKD FAILED.'

    else:
        # Adding EXTRA SOUND CARDS resampled into jack, aka 'external_cards'
        load_extra_cards()

        # Emerging JACKLOOPS (external daemon)
        run_jloops()
        if not check_jloops():
            warnings += ' JACKLOOPS FAILED.'

    if warnings:
        return warnings.strip()
    else:
        return 'done'


def run_jloops():
    """ Jack loops launcher
        (void)
    """
    # Jack loops launcher external daemon
    sp.Popen(f'{MAINFOLDER}/share/services/preamp_mod/jloops_daemon.py', shell=True)


def check_jloops(config=CONFIG):
    """ Jack loops check
        (bool)
    """

    loop_names = ['pre_in_loop']

    for source in config['sources']:
        pname = config['sources'][source]['jack_pname']
        if 'loop' in pname and pname not in loop_names:  # avoids duplicates
            loop_names.append( pname )

    cfg_loops = []

    for loop_name in loop_names:
            cfg_loops.append( f'{loop_name}:input_1' )
            cfg_loops.append( f'{loop_name}:input_2' )
            cfg_loops.append( f'{loop_name}:output_1' )
            cfg_loops.append( f'{loop_name}:output_2' )

    if not cfg_loops:
        return True

    # Waiting 5 s for all loops to be spawned
    tries = 25
    with jack.Client(name='tmp', no_start_server=True) as jc:

        while tries:
            j_loops = jc.get_ports('loop')
            if len(j_loops) == len(cfg_loops):
                break
            tries -= 1
            sleep(.2)

    sleep(.1)   # safest

    if tries:
        print(f'{Fmt.BLUE}JACK LOOPS RUNNING{Fmt.END}')
        return True
    else:
        print(f'{Fmt.BOLD}JACK LOOPS FAILED{Fmt.END}')
        return False


def jack_lsp():
    """ checks for jackd ports to be accesible
        (bool)
    """
    try:
        sp.check_output( 'jack_lsp 1>/dev/null 2>&1'.split() )
        return True
    except:
        return False


def peaudiosys_server_is_running(timeout=30):
    """ (bool)
    """

    stack = inspect.stack()

    caller = ''

    # We need at least 2 frames in the stack
    if len(stack) >= 2:

        # The caller is the 2nd index
        caller_frame = stack[1]
        tmp_modu = os.path.basename(caller_frame.filename)
        tmp_func = caller_frame.function

        if tmp_modu:
            caller += tmp_modu.replace('.py', '')

        if caller and tmp_func != '<module>':
            caller += '.' + tmp_func


    print(f'{Fmt.BLUE}({caller}) waiting for the server to be alive ...{Fmt.END}')

    period = 0.5
    tries = int(timeout / period)
    while tries:

        # Expected response from server.py peaudiosys
        ans = send_cmd('state')
        if 'loudspeaker' in ans:
            break

        sleep(.5)
        tries -= 1

    if tries:
        print(f'{Fmt.BLUE}({caller}) server.py peaudiosys is RUNNING{Fmt.END}')
        return True

    else:
        print(f'{Fmt.BOLD}({caller}) server.py peaudiosys NOT RUNNING{Fmt.END}')
        return False


def manage_amp_switch(mode):

    def get_amp_state():
        result = 'n/a'
        try:
            with open( f'{AMP_STATE_PATH}', 'r') as f:
                tmp =  f.read().strip()
            if tmp.lower() in ('0', 'off'):
                result = 'off'
            elif tmp.lower() in ('1', 'on'):
                result = 'on'
        except:
            pass
        return result


    def set_amp_state(mode):
        if 'amp_manager' in CONFIG:
            AMP_MANAGER     = CONFIG['amp_manager']
        else:
            return '(aux) amp_manager not configured'
        print( f'(aux) running \'{AMP_MANAGER.split("/")[-1]} {mode}\'' )
        sp.Popen( f'{AMP_MANAGER} {mode}', shell=True )
        sleep(1)
        return get_amp_state()


    def wait4_convolver_on():
        cmax = 30
        while True:
            conv_on = read_state_from_disk()["convolver_runs"]
            if conv_on == True:
                sleep(3)
                send_cmd('aux warning clear', timeout=1)
                break
            cmax -= 1
            if not cmax:
                send_cmd('aux warning clear', timeout=1)
                break
            sleep(1)


    new_state  = '';

    if mode == 'state':
        result = get_amp_state()

    elif mode == 'toggle':
        cur_state = get_amp_state()
        # if unknown state, this switch defaults to 'on'
        new_state = {'on': 'off', 'off': 'on'}.get( cur_state, 'on' )

    elif mode in ('on', 'off'):
        new_state = mode

    else:
        result = '(aux) bad amp_switch option'


    if new_state:

        # Clear last_macro info whenever the amp is switched
        send_cmd('aux run_macro clear_last_macro')

        # Set the new amp switch mode
        result = set_amp_state( new_state )


    if new_state == 'on':

        # Wake up the convolver if sleeping:
        send_cmd('aux warning set ( waking up ... )', timeout=1)
        sleep(1)
        send_cmd('preamp convolver on', timeout=1)
        job = threading.Thread(target=wait4_convolver_on)
        job.start()

    # Optional: as per <config.yml>
    if new_state == 'off':

        # STOP the current PLAYER:
        if 'amp_off_stops_player' in CONFIG and CONFIG['amp_off_stops_player']:
            curr_input = read_state_from_disk()['input']
            if not curr_input.startswith('remote'):
                send_cmd('player pause', timeout=1)

        # SHUTDOWN the COMPUTER:
        if 'amp_off_shutdown' in CONFIG and CONFIG['amp_off_shutdown']:
            sp.Popen(f'eject {CONFIG["cdrom_device"]}', shell=True)
            sleep(3)
            sp.Popen('sudo poweroff',  shell=True)

    return result


def calc_gain( state ):
    """ Calculates the gain from:   level,
                                    ref_level_gain
                                    source gain offset
        (float)
    """

    gain    = state["level"] + float(CONFIG["ref_level_gain"]) \
                             - state["lu_offset"]
    # Adding here the specific source gain:
    if state["input"] != 'none':
        try:
            gain += float( CONFIG["sources"][state["input"]]["gain"] )
        except:
            pass

    return gain


def get_loudness_monitor():

        result = read_json_from_file(LDMON_PATH)

        if not result:
            if 'LU_reset_scope' in CONFIG:
                result = {'LU_I': 0.0, 'LU_M':0.0,
                          'scope': CONFIG["LU_reset_scope"]}
            else:
                result = {'LU_I': 0.0, 'LU_M':0.0,
                          'scope': 'album'}

        return result


def read_bf_config_port():
    """ Default port: 3000
    """

    bfport = 3000

    with open(BFCFG_PATH, 'r') as f:
        lines = f.readlines()

    for l in lines:
        if 'port:' in l and l.strip()[0] != '#':
            try:
                bfport = int([x for x in l.replace(';', '').split()
                                     if x.isdigit() ][0])
            except:
                pass

    return bfport


def read_bf_config_fs():
    """ Reads the sampling rate configured in Brutefir
            - from         brutefir_config    (the loudspeaker config file),
            - or from   ~/.brutefir_defaults  (the default config file).
        (int)
    """
    FS = 0

    for fname in ( BFCFG_PATH, BFDEF_PATH ):
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
        print(f'{Fmt.RED}'
              f'(miscel.py) (i) USING .brutefir_defaults SAMPLE RATE'
              f'{Fmt.END}')

    return FS


def get_peq_in_use():
    """ Finds out the PEQ (parametic eq) filename (w/o extension) used by an inserted
        Ecasound sound processor, if included inside config.yml plugins section.
        (filepath: string)
    """
    for item in CONFIG["plugins"]:
        if type(item) == dict and 'ecasound_peq.py' in item.keys():
            return item["ecasound_peq.py"].replace('.peq', '')
    return 'none'


def get_macros(only_web_macros=True):
    """ Returns the list of executable files under the macros folder.
        By default the list is restricted to web macros kinf of files: "NN_xxxxxx"
    """
    macro_files = []

    with os.scandir( f'{MACROS_FOLDER}' ) as entries:

        for entrie in entries:
            fname = entrie.name

            # Only executables files
            if os.path.isfile(f'{MACROS_FOLDER}/{fname}') and \
               os.access(f'{MACROS_FOLDER}/{fname}', os.X_OK):

                # Web macros are the ones named NN_xxxxxx
                if only_web_macros:
                    if fname.split('_')[0].isdigit():
                        macro_files.append(fname)
                else:
                    macro_files.append(fname)

    macro_files.sort()

    # (i) The web page needs a sorted list (numeric sorting only if NN_xxxxxx items)
    if only_web_macros:
        macro_files.sort( key=lambda x: int(x.split('_')[0]) )

    return macro_files


def get_remote_selected_source(addr, port=9990):
    """ Gets the selected source from a remote pe.audio.sys server at <addr:port>
        (string)
    """
    remote_source = ''
    remote_state = send_cmd('state', host=addr, port=port, timeout=1)
    try:
        remote_source = json_loads(remote_state)["input"]
    except:
        pass
    return remote_source


def get_remote_source_addr_port(sname):
    """ Gets the IP:CTRLPORT as configured under 'jack_pname' in a
        remoteXXXXX kind of configured source.
    """
    addr = ''
    port = 9990
    try:
        jpname = CONFIG["sources"][sname]["jack_pname"]
        tmp_addr = jpname.split(':')[0]
        tmp_port = jpname.split(':')[-1]
        if is_IP(tmp_addr):
            addr = tmp_addr
        else:
            print(f'(miscel.py) source: \'{source}\' address: \'{tmp_addr}\' is NOT valid')
        if tmp_port.isdigit():
            port = int(tmp_port)
    except Exception as e:
        print(f'(miscel.py) ERROR reading source: {str(e)}')

    return addr, port


def get_remote_sources():
    ''' Retrieves the remoteXXXXXX sources found under the 'sources:' section
        inside config.yml.

        Returns a list of tuples (srcName,srcIP,srcCtrlPort)
    '''
    # On a 'remote.....' named source, it is expected to have
    # an IP address kind of in its jack_pname field:
    #   jack_pname:  IP:CTRLPORT
    # so this way we can query the remote sender to run 'zita-j2n'

    remotes = []
    for source in CONFIG["sources"]:
        if 'remote' in source:
            addr, port = get_remote_source_addr_port(source)
            remotes.append( (source, addr, port) )

    if remotes:
        print(f'(miscel.py) (i) found remote sources: {[x[0] for x in remotes]}')

    return remotes


def get_remote_zita_params(rem_src_name):
    """ Getting remote source zita parameters (IP, ctrlport, zitaUDP)
    """
    raddr, cport, zport = '', 9900, 65000

    # IP, CTRL_PORT
    raddr, cport = get_remote_source_addr_port(rem_src_name)

    # The ZITA's UDP PORT was assigned at the start.
    try:
        with open(f'{MAINFOLDER}/.zita_link_ports', 'r') as f:
            zports = json_loads( f.read() )
            zport  = zports[rem_src_name]['udpport']
    except Exception as e:
        print( f'(miscel.py) ERROR with .zita_link_ports: {str(e)}' )

    return raddr, cport, zport


def remote_zita_restart(raddr, ctrl_port, zita_port):
    """
        Restarting zita-j2n on the multiroom sender's end,
        pointing to our ip.

        (i) The sender will run zita_j2n only when a receiver request it
    """
    zargs     = json_dumps( (get_my_ip(), zita_port, 'start') )
    remotecmd = f'aux zita_j2n {zargs}'
    result = send_cmd(remotecmd, host=raddr, port=ctrl_port)
    print(f'(miscel.py) SENDING TO REMOTE: {remotecmd}')
    return result


def local_zita_restart(raddr, udp_port, buff_size):
    """
        Run zita-n2j listen ports on the multiroom receiver's end.

        (i) Will log zita process printouts under LOG_FOLDER
    """

    zitajname = f'zita_n2j_{ raddr.split(".")[-1] }'
    zitacmd   = f'zita-n2j --jname {zitajname} --buff {buff_size} {get_my_ip()} {udp_port}'

    # Assign ALIAS to ports to be able to switch by using
    # the IP port name of a remoteXXXX input in config.yml
    #
    with open(f'{LOG_FOLDER}/{zitajname}.log', 'w') as zitalog:

        # Ignore if zita-njbridge is not available
        try:
            sp.Popen( zitacmd.split(), stdout=zitalog, stderr=zitalog )
            wait4ports(zitajname, 3)
            sp.Popen( f'jack_alias {zitajname}:out_1 {raddr}:out_1'.split() )
            sp.Popen( f'jack_alias {zitajname}:out_2 {raddr}:out_2'.split() )
            print(f'(miscel.py) RUNNING LOCAL: {zitacmd}, LOGGING under {LOG_FOLDER}')

        except Exception as e:
            print(f'(miscel.py) ERROR: {e}, you may want run it for a remote source?')


def wait4ports( pattern, timeout=10 ):
    """ Waits for jack ports with name *pattern* to be available.
        Default timeout 10 s
        (bool)
    """
    n = timeout * 2
    while n:
        tmp = sp.check_output(['jack_lsp', pattern]).decode().split()
        if len( tmp ) >= 2:
            break
        n -= 1
        sleep(0.5)
    if n:
        return True
    else:
        return False


def send_cmd( cmd, sender='', verbose=False, timeout=60,
              host='127.0.0.1', port=CONFIG['peaudiosys_port'] ):
    """
        Sends a command to a pe.audio.sys server.
        Returns a string about the execution response or an error if so.
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
                print( f'{Fmt.BLUE}(send_cmd) ({sender}) Tx: \'{cmd}\'{Fmt.END}' )

            ans = ''

            while True:

                tmp = s.recv(1024)

                if not tmp:
                    break

                ans += tmp.decode()

            if verbose:
                print( f'{Fmt.BLUE}(send_cmd) ({sender}) Rx: \'{ans}\'{Fmt.END}' )

            s.close()

    except Exception as e:

        ans = str(e)

        if verbose:
            print( f'{Fmt.RED}(send_cmd) ({sender}) {host}:{port} \'{ans}\' {Fmt.END}' )

    return ans


def check_Mplayer_config_file(profile='istreams'):
    """ Checks the Mplayer config file
        (result: string)
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


def detect_spotify_client():
    """ Detects the Spotify Client in use: 'desktop' or 'librespot'
        (string)
    """
    result = ''

    # If using librespot
    try:
        sp.check_output( f'pgrep -u {USER} -f librespot'.split() )
        result = 'librespot'
    except:
        pass

    # If using plugins/spotify_monitor.py while running a Spotify Desktop client
    try:
        sp.check_output( f'pgrep -u {USER} -f spotify_monitor'.split() )
        result = 'desktop'
    except:
        pass

    return result


def read_state_from_disk():
    """ wrapper for reading the state dict
        (dictionary)
    """
    return read_json_from_file(STATE_PATH)


def read_metadata_from_disk():
    """ wrapper for reading the playing metadata dict
        (dictionary)
    """
    return read_json_from_file(PLAYER_META_PATH)


def read_cdda_meta_from_disk():
    """ wrapper for reading the cdda metadata dict from disk
        (dictionary)
    """

    result = read_json_from_file( CDDA_META_PATH )

    if not result:
        result = CDDA_META_TEMPLATE.copy()

    return result


def read_json_from_file(fpath, timeout=2):
    """ Some json files cannot be ready to read in first run,
        so let's retry
        Returns: a JSON dictionary
    """

    if fpath == STATE_PATH:
        d = {'input':'none', 'level':'0.0'}
    else:
        d = {}

    period = 0.25
    tries = int(timeout / period)
    while tries:
        try:
            with open(fpath, 'r') as f:
                d = json_loads(f.read())
            break
        except:
            tries -= 1
            sleep(period)

    if not tries:
        print(f'{Fmt.RED}(miscel.py) Cannot read `{fpath}`{Fmt.END}')

    elif not d:
        print(f'{Fmt.RED}(miscel.py) Void JSON in `{fpath}`{Fmt.END}')

    return d


# --- Generic purpose functions:

def get_pid_cmdline(process_name=''):
    """ gets all the pid and cmdline of the given process name
    """

    pids = []

    for proc in psutil.process_iter():
        try:
            if proc.name() == process_name:
                pids.append( {'pid': proc.pid, 'cmdline': proc.cmdline() } )
        except:
            pass

    return pids


def process_is_running(process_name):
    # Iterate through all running processes
    for proc in psutil.process_iter(['cmdline']):
        try:
            # (i) proc.info['cmdline']) is a list of command line args
            cmdline = ' '.join( proc.info['cmdline'] )
            # Match process name (case-insensitive)
            if process_name.lower() in cmdline.lower():
                return True
        except:
            pass
    return False


def kill_bill(pid=0):
    """ Kill any previous instance of the given PID

        returns: '' or a 'string with any error'
    """

    if not pid:
        return 'a pid is needed'

    try:
        process = psutil.Process(pid)
        pid_cmdline = os.path.basename( process.cmdline()[1] )

    except psutil.NoSuchProcess:
        return 'no such process'

    except psutil.AccessDenied:
        return 'access denied'

    except Exception as e:
        return f'error: {str(e)}'

    errors = ''

    for proc in psutil.process_iter():

        try:
            if proc.name() == "python.exe" or proc.name() == "python3":

                for cmdline in proc.cmdline():

                    if pid_cmdline in cmdline:

                        # Avoids harakiri
                        if proc.pid != pid:
                            print(f"Killing {cmdline} PID: {proc.pid}")
                            proc.kill()

        except Exception as e:
            errors += f'{str(e)}\n'

    return errors


def read_last_line(filename=''):
    """ Read the last line from a large file, efficiently.
        (string)
    """
    # credits:
    # https://stackoverflow.com/questions/46258499/read-the-last-line-of-a-file-in-python
    # For large files it would be more efficient to seek to the end of the file,
    # and move backwards to find a newline.
    # Note that the file has to be opened in binary mode, otherwise,
    # it will be impossible to seek from the end.
    #
    # https://python-reference.readthedocs.io/en/latest/docs/file/seek.html
    # f.seek( offset, whence )

    if not filename:
        return ''

    try:
        with open(filename, 'rb') as f:
            f.seek(-2, os.SEEK_END)             # Go to -2 bytes from file end

            while f.read(1) != b'\n':           # Repeat reading until find \n
                f.seek(-2, os.SEEK_CUR)

            last_line = f.readline().decode()   # readline reads until \n

        return last_line.strip()

    except:
        return ''


def read_last_lines(filename='', nlines=1):
    """ Read the last N lines from a large file, efficiently.
        (list of strings)
    """
    # credits:
    # https://stackoverflow.com/questions/46258499/read-the-last-line-of-a-file-in-python
    # For large files it would be more efficient to seek to the end of the file,
    # and move backwards to find a newline.
    # Note that the file has to be opened in binary mode, otherwise,
    # it will be impossible to seek from the end.
    #
    # https://python-reference.readthedocs.io/en/latest/docs/file/seek.html
    # f.seek( offset, whence )

    if not filename:
        return ['']

    try:
        with open(filename, 'rb') as f:
            f.seek(-2, os.SEEK_END)

            c = nlines
            while c:
                if f.read(1) == b'\n':
                    c -= 1
                f.seek(-2, os.SEEK_CUR)

            lines = f.read().decode()[2:].replace('\r', '').split('\n')

        return [x.strip() for x in lines if x]

    except:
        return ['']


def force_to_flush_file(fname='', content=''):
    """ A tool to flush some special temporary files
        (!) BE CAREFUL WITH THIS
        (result: string)
    """
    bare_fname = fname.replace(f'{MAINFOLDER}/', '')

    if 'pe.audio.sys' not in fname:
        return f'NOT allowed flushing outside pe.audio.sys'

    if bare_fname.replace(MAINFOLDER, '').count('/') >= 1:
        return f'NOT allowed flushing deeper than \'{MAINFOLDER}\''

    if not bare_fname.startswith('.'):
        return f'ONLY allowed flushing dot-hidden files'

    # It is possible to fail while the file is updating :-/
    times = 5
    while times:
        try:
            with open( fname, 'w') as f:
                f.write(content)
            return 'done'
        except:
            times -= 1
        sleep(.2)
    return 'ERROR flushing \'fname\''


def is_IP(s):
    """ Validate if a given string is a valid IP address
        (bool)
    """
    if type(s) == str:
         try:
             ipaddress.ip_address(s)
             return True
         except:
             return False
    else:
         return False


def get_my_ip():
    """ retrieves the own IP address
        (string)
    """
    try:
        tmp = sp.check_output( 'hostname --all-ip-addresses'.split() ).decode()
        return tmp.split()[0]
    except:
        return ''


def get_timestamp():
    """ the timestamp string, example: '2025-01-02T08:58:59'
    """
    return datetime.now().isoformat(timespec='seconds')


def time_diff(t1, t2):
    """ input:   <strings> 'MM:SS'
        returns: <int>  the difference in seconds or <string> Error
    """
    try:
        s1 = int(t1[:2]) * 60 + int(t1[-2:])
    except Exception as e:
        return str(e)

    try:
        s2 = int(t2[:2]) * 60 + int(t2[-2:])
    except Exception as e:
        return str(e)

    return s2 - s1


def time_sec2mmss(s, mode=':'):
    """ Format a given float (seconds)

        to      "MM:SS"
        or to   "MMmSSs"    if mode != ':'

        (string)
    """
    m = int(s // 60)
    s = int(s % 60)

    if mode == ':':
        return f'{str(m).rjust(2,"0")}:{str(s).rjust(2,"0")}'

    else:
        return f'{str(m).rjust(2,"0")}m{str(s).rjust(2,"0")}s'


def time_sec2hhmmss(x):
    """ Format a given float (seconds) to "hh:mm:ss"
        (string)
    """
    # x must be float
    h = int( x / 3600 )         # hours
    x = int( round(x % 3600) )  # updating x to reamining seconds
    m = int( x / 60 )           # minutes from the new x
    s = int( round(x % 60) )    # and seconds
    return f'{h:0>2}:{m:0>2}:{s:0>2}'


def time_msec2mmsscc(msec=0, string=''):
    """ Convert milliseconds <--> string MM:SS.CC

        Give me only one parameter: number or string
    """

    if msec and string:
        return 'Error converting msec'

    elif msec:

        sec  = msec / 1e3
        mm   = f'{sec // 60:.0f}'.zfill(2)
        ss   = f'{sec %  60:.2f}'.zfill(5)

        return f'{mm}:{ss}'

    elif string:

        mm   = int( string.split(':')[0] )
        sscc =      string.split(':')[1]
        ss   = int( sscc.split('.')[0]   )
        cc   = int( sscc.split('.')[1]   )

        millisec = mm * 60 * 1000 + ss * 1000 + cc * 10

        return millisec

