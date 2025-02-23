#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

"""
    Shows the Brutefir configuration, outputs, coeffs and filters
"""

import sys
import os
import subprocess as sp

UHOME = os.path.expanduser("~")
sys.path.append(f'{UHOME}/pe.audio.sys/share/miscel')

from    miscel  import process_is_running, Fmt
import  brutefir_mod as bf


def do_printout():

    print()
    print( f'--- Brutefir process runs:' )
    print( f'{BRUTEFIR_CONFIG_PATH}')
    print()
    print( "--- Outputs map:" )
    for output in cfg["outputsMap"]:
        print( output[0].ljust(10), '-->   ', output[1] )

    print()
    print( f'sampling_rate:    {cfg["sampling_rate"]}')
    print( f'filter_length:    {cfg["filter_length"]}')
    print( f'float_bits:       {cfg["float_bits"]}')
    print( f'output_dither:    {cfg["dither"]}')
    print( f'output_maxdelay:  {cfg["maxdelay"]}')
    print( f'outputs_delays:   {cfg["delays"]}   (at init)')
    print( Fmt.BOLD + f'                  {curr_delays_str}   (CURRENT)' + Fmt.END)

    print()
    print( "--- Coeff available:" )
    print( "                       c# coeff                    cAtten pcm_name" )
    print( "                       -- -----                    ------ --------" )
    for c in coeffs:

        cidx    = c['index'].rjust(2)
        cname   = c['name'].ljust(24)
        catt    = '{:+6.2f}'.format( float(c['atten']) )
        pcm     = c['pcm']
        cline_chunk = cidx + ' ' + cname + ' ' + catt + ' ' + pcm
        print( ' ' * 23 + cline_chunk )

    print()
    print( "--- Filters running: (totAttn sumarizes all atten found in filter)\n" )
    print( "f# filter  totAttn pol c# coeff                    cAtten pcm_name" )
    print( "-- ------  ------- --- -- -----                    ------ --------" )
    for f in filters_running:

        # 'f_num': '8', 'f_name': 'f.sw', 'coeff set': '8',
        # 'delay blocks': '0 (0 samples)',
        # 'from inputs': '', 'to outputs': '7/0.0',
        # 'from filters': '2/3.0 3/3.0', 'to filters': '', 'atten tot': 6.0

        fidx    = f['f_num'].rjust(2)

        fname   = f['f_name'].ljust(8)

        fatt    = '{:+6.2f}'.format( float(f['atten tot']) )
        if float(fatt) < 0:
            fatt = Fmt.BOLD + fatt + Fmt.END

        fpol    = str(f['pol']).rjust(2)
        if f["pol"] < 0:
            fpol = Fmt.BOLD + fpol + Fmt.END

        fline_chunk = fidx + ' ' + fname + ' ' + fatt + '  ' + fpol + ' '

        cset    = f['coeff set'].rjust(2)

        try:
            cname = [ c["name"] for c in coeffs if c['index'] == f['coeff set'] ][0]
        except:
            cname = ''
        cname   = cname.ljust(24)

        # The filter can be set to coeff: -1 (no filter), so no matches with coeffs.
        try:
            catt  = [ c["atten"] for c in coeffs if c['index'] == f['coeff set'] ][0]
            catt    = '{:+6.2f}'.format( float(catt) )
            if float(catt) < 0:
                catt = Fmt.BOLD + catt + Fmt.END
        except:
            catt = ''

        try:
            pcm   = [ c["pcm"] for c in coeffs if c['index'] == f['coeff set'] ][0]
        except:
            pcm = ''

        cline_chunk = cset + ' ' + cname + ' ' + catt + ' ' + pcm

        print( fline_chunk + cline_chunk )


    print()


if __name__ == "__main__" :

    if not process_is_running('brutefir'):
        print('brutefir process NOT running')
        sys.exit()

    # Gets the folder where brutefir has been launched
    try:
        # pwdx - report current working directory of a process
        tmp = sp.check_output( 'pwdx $(pgrep -f "brutefir brutefir_config")',
                                shell=True ).decode()
        BRUTEFIR_FOLDER = tmp.split('\n')[0].split(' ')[-1]
        BRUTEFIR_CONFIG_PATH = f'{BRUTEFIR_FOLDER}/brutefir_config'

    except:
        print( 'ERROR reading brutefir process' )
        sys.exit()


    # Reading Brutefir configuration
    cfg = bf.get_config()
    coeffs = cfg["coeffs"]

    # Reading filters_running
    filters_running = bf.get_running_filters()

    # Reading current delays
    curr_outputs = bf.get_current_outputs()
    curr_delays = []
    for o in curr_outputs:
        if o.isdigit():
            curr_delays.append( str(curr_outputs[o]["delay"]) )
    curr_delays_str = ','.join(curr_delays)

    # PRINTOUT:
    do_printout()
