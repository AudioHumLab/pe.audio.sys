#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

""" auxiliary services: not preamp-core neither players related
"""

#   https://watchdog.readthedocs.io/en/latest/
from watchdog.observers     import  Observer
from watchdog.events        import  FileSystemEventHandler
import  jack
import  subprocess as sp
from    time                import  sleep, ctime
import  os
import  sys
import  threading

UHOME = os.path.expanduser("~")
sys.path.append(f'{UHOME}/pe.audio.sys/share/miscel')

from    config      import  CONFIG, MAINFOLDER, MACROS_FOLDER, \
                            AMP_STATE_PATH, LDMON_PATH, LDCTRL_PATH

from    miscel      import  *

from    peq_mod     import eca_bypass, eca_load_peq


def dump_aux_info():
    """ A helper to write AUX_INFO dict to a file to be accesible
        by third party processes
    """
    # Dynamic updates
    AUX_INFO['amp']                     = manage_amp_switch( 'state' )
    AUX_INFO['loudness_monitor']        = get_loudness_monitor()
    AUX_INFO['sysmon']                  = get_sysmon('wlan0')

    # Dumping to disk
    with open(AUX_INFO_PATH, 'w') as f:
        f.write( json_dumps(AUX_INFO) )


def get_sysmon(w_iface='wlan0'):
    """ A simple reader of
            - CPU temperature
            - wireless link stattus
    """

    def get_wifi(iface='wlan0'):
        """ Returns a dict, example:

            {   'Bit-rate-Mb/s': '72.2',
                'Tx-Power': '31',
                'Quality': '61/70',
                'Signal-level': '-49'
            }
        """
        #   $ cat /proc/net/wireless
        #   Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE
        #    face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22
        #    wlan0: 0000   61.  -49.  -256        0      0      0      0      0        0


        #   $ iwconfig wlan0
        #   wlan0     IEEE 802.11  ESSID:"MOVISTAR_FC50"
        #             Mode:Managed  Frequency:2.412 GHz  Access Point: 4C:AB:F8:CB:FC:5F
        #             Bit Rate=72.2 Mb/s   Tx-Power=31 dBm
        #             Retry short limit:7   RTS thr:off   Fragment thr:off
        #             Power Management:on
        #             Link Quality=61/70  Signal level=-49 dBm
        #             Rx invalid nwid:0  Rx invalid crypt:0  Rx invalid frag:0
        #             Tx excessive retries:0  Invalid misc:0   Missed beacon:0
        #
        #   not connected here:
        #
        #   wlan0     IEEE 802.11  ESSID:off/any
        #             Mode:Managed  Access Point: Not-Associated   Tx-Power=12 dBm
        #             Retry short limit:7   RTS thr:off   Fragment thr:off
        #             Power Management:off
        #

        d = {}

        if not WIFI_DETECTED:
            return d

        try:
            tmp = sp.check_output(f'iwconfig {iface}'.split()).decode().split()

            d['iface'] = iface

            for e in tmp:
                if '=' in e:
                    k, v = e.split('=')
                    if k.lower() == 'rate':     k = 'Bit-rate-Mb/s'
                    if k.lower() == 'level':    k = 'Signal-level'
                    d[k] = v

        except Exception as e:
            print(f'(aux.py) get_wifi {str(e)}' )

        return d


    def get_temp():
        """
        """
        #   This works on Intel and ARM
        #   $ cat /sys/class/thermal/thermal_zone0/temp
        #   74136

        temp = 0.0

        try:
            tmp = sp.check_output('cat /sys/class/thermal/thermal_zone0/temp'.split()).decode()

            temp = round(int(tmp) / 1000, 1)

        except Exception as e:
            print( str(e) )

        return temp


    def get_fans_speed(get_zero_rmp=False):
        """
        """
        fans = {'fan1':'', 'fan2':'', 'fan3':'', }
        hw_dir = '/sys/class/hwmon/hwmon1'
        for i in 1,2,3:
            try:
                with open(f'{hw_dir}/fan{i}_input', 'r') as f:
                    x = f.read().strip()
                    if int(x) or get_zero_rmp:
                        fans[f"fan{i}"] = x
            except:
                pass

        return fans



    return  {   'wifi': get_wifi( w_iface),
                'temp': get_temp(),
                'fans': get_fans_speed()
            }


def get_web_config():
    """ used by the control web page client
    """

    wconfig = CONFIG['web_config']

    # Macros used by the web page
    wconfig['user_macros'] = get_macros(only_web_macros=True)

    # Main selector manages inputs or macros
    if not 'main_selector' in wconfig:
        wconfig['main_selector'] = 'inputs';
    else:
        if wconfig['main_selector'] not in ('inputs', 'macros'):
            wconfig['main_selector'] = 'inputs'

    # Adding LU_monitor_enabled
    wconfig['LU_monitor_enabled'] = True if 'loudness_monitor.py' \
                                              in CONFIG['plugins'] else False

    return wconfig


def run_macro(mname):

    if mname in get_macros():

        print( f'(aux) running macro: {mname}' )
        sp.Popen( f'"{MACROS_FOLDER}/{mname}"', shell=True)
        AUX_INFO["last_macro"] = mname
        return 'ordered'

    else:
        return 'macro not found'


def zita_j2n(args):
    """ This internal function is always issued from a multiroom receiver.

        Feeds the preamp audio to a zita-j2n port pointing to the receiver.

        args: a json tuple string "(dest, udpport, do_stop)"
    """

    dest, udpport, do_stop = json_loads(args)

    # BAD ADDRESS
    if not is_IP(dest):
        return 'bad address'

    zitajname = f'zita_j2n_{ dest.split(".")[-1] }'

    # STOP mode
    if do_stop == 'stop':
        zitapattern  = f'zita-j2n --jname {zitajname}'
        sp.Popen( ['pkill', '-KILL', '-f',  zitapattern] )
        return f'killing {zitajname}'

    # NORMAL mode
    jcli = jack.Client(name='zitatmp', no_start_server=True)
    jports = jcli.get_ports()
    result = ''
    if not [x for x in jports if zitajname in x.name]:
        zitacmd     = f'zita-j2n --jname {zitajname} {dest} {udpport}'
        with open('/dev/null', 'w') as fnull:
            sp.Popen( zitacmd.split(), stdout=fnull, stderr=fnull )

    wait4ports(zitajname, timeout=3)

    try:
        jcli.connect( 'pre_in_loop:output_1', f'{zitajname}:in_1' )
        jcli.connect( 'pre_in_loop:output_2', f'{zitajname}:in_2' )
        result = 'done'
    except Exception as e:
        result = str(e)

    jcli.close()

    return result


def peq_load(peqpath):
    """ a wrapper to load a PEQ file and updating .aux_info

        returns: 'done' or some error string
    """
    res = eca_load_peq(peqpath)

    # updatting .aux_info
    if res == 'done':
        AUX_INFO["peq_set"] = os.path.basename(peqpath).replace('.peq','')
        AUX_INFO['peq_bypassed'] = eca_bypass('get')

    return res


def peq_bypass(mode):
    """ a wrapper to manage Ecasound chains bypass
        mode:       on | off | toggle | get
        return:     [L_mode, R_mode]
    """

    newmode = eca_bypass(mode)

    AUX_INFO['peq_bypassed'] = newmode

    return f'{newmode}'


def play_url(arg):
    """ Aux for playback an url stream
    """
    # As per this function is a compound function, I have decided
    # to hold it here instead of inside the players module

    def istreams_query(url):
        """ Order the istreams daemon plugin to playback an internet stream url
        """
        error = False

        # Tune the radio station (Mplayer jack ports will dissapear for a while)
        sp.Popen( f'{MAINFOLDER}/share/plugins/istreams.py url {url}'.split() )

        # Waits a bit to Mplayer ports to dissapear from jack while loading a new stream.
        sleep(2)

        # Waiting for mplayer ports to re-emerge
        if not wait4ports( f'mplayer_istreams' ):
            print(f'(aux) ERROR jack ports \'mplayer_istreams\''
                   ' not found' )
            error = True

        if not error:
            # Switching the preamp input
            # PATCH: using timeout is needed unless send_cmd was modified
            send_cmd('preamp input istreams', 'aux play_url ...', True, 1)
            return True

        else:
            return False

    if arg.startswith('http://') or arg.startswith('https://'):
        if istreams_query(arg):
            result = 'ordered'
        else:
            result = 'failed'
    else:
        result = f'(aux) bad url: {arg}'

    return result


def manage_lu_monitor(string):
    """ Manages the loudness_monitor.py daemon through by its fifo
    """
    #   As per LDCTRL_PATH is a namedpipe (FIFO), it is needed that
    #   'loudness_monitor.py' was alive in order to release any write to it.
    #   If not alive, any f.write() to LDCTRL_PATH will HANG UP
    #   :-(
    if not process_is_running('loudness_monitor.py'):
        return 'ERROR loudness_monitor.py NOT running'
    try:
        with open(LDCTRL_PATH, 'w') as f:
            f.write(string)
        return 'ordered'
    except Exception as e:
        return f'ERROR writing .loudness_control FIFO: {str(e)}'


def warning_expire(timeout=5):
    """ Threads a timer to clear the warning message field inside .aux_info
    """
    def mytimer(timeout):
        sleep(timeout)
        AUX_INFO['warning'] = ''

    job = threading.Thread(target=mytimer, args=(timeout,))
    job.start()


def manage_warning_msg(arg):
    """ Manages the warning field under .aux_info than can be used
        from the control web page interface
    """
    args = arg.split()

    if args[0] == 'set':

        if AUX_INFO['warning']:
            result = 'warning message in use'
        else:
            AUX_INFO['warning'] = ' '.join(args[1:])
            warning_expire(timeout=60)
            result = 'done'

    elif args[0] == 'perm':

        if AUX_INFO['warning']:
            result = 'warning message in use'
        else:
            AUX_INFO['warning'] = ' '.join(args[1:])
            result = 'done'

    elif args[0] == 'clear':
        AUX_INFO['warning'] = ''
        result = 'done'

    elif args[0] == 'get':
        result = AUX_INFO['warning']

    elif args[0] == 'expire':
        if args[1:] and args[1].isdigit():
            warning_expire(timeout=int(args[1]))
            result = 'done'
        else:
            result = 'bad expire timeout'
    else:
        result = 'usage: warning set message | warning clear'

    return result


def alert_new_eq_graph(timeout=1):
    """ This sets the 'new_eq_graph' field to True for a while
        so that the web page can realize when the graph is dumped.
        This helps on slow machines because the PNG graph takes a while
        after the 'done' is received when issuing some audio command.

        (i) Dumping this to the aux_info file is not needed because web
            clients pulls this AUX_INFO run time variable not from disk.
    """
    def mytimer(timeout):
        sleep(timeout)
        AUX_INFO['new_eq_graph'] = False
    job = threading.Thread(target=mytimer, args=(timeout,))
    job.start()
    AUX_INFO['new_eq_graph'] = True
    return f'alerting for {timeout} s'


def get_bf_peaks(only_today=True):
    """ from brutefir_peaks.log
    """

    def get_peaks_header(pline):
        """ Extract output names (2 characters) from a brutefir peaks log line
            with heading spaces in order to be aligned with the below lines

                                   27   -->    +12
        Fri Sep 20 12:47:40 2024   lo.L:  5.3  mi.L:  6.2  hi.L: 10.1  lo.R:  5.4  mi.R:  5.5  hi.R: 10.1
        """

        ptail = pline[27:]

        header = ' ' * 27
        i = 0
        channel = ptail[i + 3]
        while i < len(ptail):

            # add spaces when channel changes
            if channel != ptail[i + 3]:
                header += ' ' * 3
            channel = ptail[i + 3]

            header += ptail[i:i + 12][:2] + '    '

            i += 12

        #                        LO    MI    HI        LO    MI    HI
        return header.upper()


    def remove_labels(pline):
        """ Extract output peak values from a brutefir peaks log line
            with spacing in order to be aligned with the header line.

                                   27   -->    +12
        Fri Sep 20 12:47:40 2024   lo.L:  5.3  mi.L:  6.2  hi.L: 10.1  lo.R:  5.4  mi.R:  5.5  hi.R: 10.1
        """

        pdate = pline[:27]
        ptail = pline[27:]

        values = ''
        i = 0
        ch = ptail[i + 3]
        while i < len(ptail):

            # add spaces when channel changes
            if ch != ptail[i + 3]:
                values += ' ' * 3
            ch = ptail[i + 3]

            values += ptail[i:i + 12][6:]

            i += 12

        pline = pdate + '   ' + values

        # Fri Sep 20 12:48:02 2024      1.2   2.3  10.1      5.4   5.5  10.1
        return pline


    result = { 'header': '', 'peaks': [] }

    try:
        with open(f'{LOG_FOLDER}/brutefir_peaks.log', 'r') as f:
            peaks = f.read().split('\n')
    except:
        result["header"] = 'Error reading peaks'
        return result

    # Example:
    #      0        9          20
    #   [ 'Thu Sep 19 21:05:19 2024   lo.L:  5.3  mi.L:  5.9 ...',
    #     'Thu Sep 19 21:05:33 2024   ... ....',
    #      ... ]


    # Prepare the header
    header = ''
    if peaks:
        header = get_peaks_header(peaks[0])


    # Let's keep the timestamp and values, removing the 'out.ch:' labels
    for n, pline in enumerate(peaks):
        if not pline:
            continue
        peaks[n] = remove_labels( pline )


    # removing the day, month and year and shorten the header line
    if only_today:

        header = header[13:]

        #           10        20
        #           |         |
        # Fri Sep 20 12:48:02 2024
        today = ctime()

        peaks = [x[11:19] + '  ' + x[27:] for x in peaks
                         if  x[:10]   == today[:10]
                         and x[20:24] == today[20:24] ]


    result["header"] = header
    result["peaks"]  = peaks

    return result


def get_help():
    """ List of end user available commands
    """
    cmds = ['amp_switch', 'get_macros', 'run_macro', 'play_url',
            'reset_loudness_monitor', 'reset_lu_monitor' ,
            'set_loudness_monitor_scope', 'set_lu_monitor_scope',
            'get_loudness_monitor', 'get_lu_monitor', 'info', 'warning']
    return ', '.join( cmds )


# Handler class to do actions when a file change occurs.
class files_event_handler(FileSystemEventHandler):
    """ will do something when <wanted_path> file changes
    """
    # (i) This is an inherited class from the imported one 'FileSystemEventHandler',
    #     which provides the 'event' propiertie.
    #     Here we expand the class with our custom parameter 'wanted_path'.

    def __init__(self, wanted_path=''):
        self.wanted_path = wanted_path

    def on_modified(self, event):
        # DEBUG
        #print( f'(aux) event type: {event.event_type}, file: {event.src_path}' )
        if event.src_path == self.wanted_path:
            dump_aux_info()


# auto-started when loading this module
def init():

    def wifi_detect():

        try:
            tmp = sp.check_output(f'ifconfig'.split()).decode().split()
            if 'wlan' in tmp:
                print(f'{Fmt.GREEN}(aux.py) wifi detected{Fmt.END}')
                return True
            else:
                print(f'{Fmt.GRAY}(aux.py) wifi NOT detected{Fmt.END}')
                return False

        except Exception as e:
            print(f'(aux.py) wifi_detect {str(e)}' )
            return False


    global AUX_INFO, WIFI_DETECTED

    WIFI_DETECTED = wifi_detect()

    AUX_INFO = {    'amp':                  'off',
                    'loudness_monitor':     0.0,
                    'last_macro':           '',
                    'warning':              '',
                    'peq_set':              get_peq_in_use(),
                    'peq_bypassed':         eca_bypass('get')
                }

    # First update
    dump_aux_info()

    # Starts a WATCHDOG to observe file changes
    #   https://watchdog.readthedocs.io/en/latest/
    #   https://stackoverflow.com/questions/18599339/
    #   python-watchdog-monitoring-file-for-changes
    #   Use recursive=True to observe also subfolders
    #   Even observing recursively the CPU load is negligible,
    #   but we prefer to observe to a single folder.

    # Will observe for changes in AMP_STATE_PATH:
    observer1 = Observer()
    observer1.schedule( files_event_handler(AMP_STATE_PATH),
                        path=os.path.dirname(AMP_STATE_PATH),
                        recursive=False )
    observer1.start()

    # Will observe for changes in LDMON_PATH:
    observer2 = Observer()
    observer1.schedule( files_event_handler(LDMON_PATH),
                        path=os.path.dirname(LDMON_PATH),
                        recursive=False )
    observer2.start()


# Interface function for this module
def do( cmd, arg=None ):
    """ input:  command [, arg]
        output: an execution result string
    """

    cmd = cmd.lower()


    # Dump AUX_INFO is NOT needed
    if   cmd == 'peak_monitor_running':
        result = process_is_running('peak_monitor.py')

    elif cmd == 'get_bf_today_peaks':
        result = get_bf_peaks(only_today=True)

    elif cmd == 'get_macros':
        result = get_macros()

    elif cmd == 'play_url':
        result = play_url(arg)

    elif cmd == 'reset_loudness_monitor' or cmd == 'reset_lu_monitor':
        result = manage_lu_monitor('reset')

    elif cmd == 'set_loudness_monitor_scope' or cmd == 'set_lu_monitor_scope':
        result = manage_lu_monitor(f'scope={arg}')

    elif cmd == 'get_loudness_monitor' or cmd == 'get_lu_monitor':
        result = get_loudness_monitor()

    elif cmd == 'info':
        result = AUX_INFO

    elif cmd == 'zita_j2n':
        result = zita_j2n(arg)

    elif cmd == 'get_web_config':
        result = get_web_config()

    elif cmd == 'help':
        result = get_help()


    # Dump AUX_INFO is needed
    else:

        if   cmd == 'amp_switch':
            result = manage_amp_switch(arg)

        elif cmd == 'run_macro':
            result = run_macro(arg)

        elif cmd == 'peq_bypass':
            result = peq_bypass(arg)

        elif cmd == 'peq_load':
            result = peq_load(arg)

        elif cmd == 'warning':
            result = manage_warning_msg(arg)

        elif cmd == 'alert_new_eq_graph':
            result = alert_new_eq_graph()

        else:
            return f'(aux) bad command \'{cmd}\''

        dump_aux_info()


    return result


# Will AUTO-START init() when loading this module
init()
