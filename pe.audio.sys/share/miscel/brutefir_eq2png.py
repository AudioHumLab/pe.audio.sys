#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

"""
    A module to dump an EQ stage graph to share/www/images/brutefir_eq.png

    In addition, command line usage is available:

        brutefir_eq2png.py [--verbose]
"""
import  sys
import  os
import  numpy as np
import  yaml
from    socket import socket

import  matplotlib
# (i) Agg is a SAFE backend to avoid "tkinter.TclError: couldn't connect to display"
#     under certain circumstances.
#     https://matplotlib.org/faq/usage_faq.html#what-is-a-backend
#     https://matplotlib.org/faq/howto_faq.html#working-with-threads
# Comment out this line if you want to test plotting under your standard backend
matplotlib.use('Agg')
import  matplotlib.pyplot as plt


UHOME    = os.path.expanduser("~")
PNG_PATH = f'{UHOME}/pe.audio.sys/share/www/images/brutefir_eq.png'

verbose     = False

# Prepare pyplot
plt.style.use('dark_background')
plt.rcParams.update({'font.size': 6})
RGBweb      = (.15, .15, .15)   # same as index.html background-color: rgb(38, 38, 38);
lineColor   = 'grey'
figHeight   = 1.5   # min 1.5 if font.size = 6
freq_limits = [20, 20000]
freq_ticks  = [20, 50, 100, 200, 500, 1e3, 2e3, 5e3, 1e4, 2e4]
freq_labels = ['20', '50', '100', '200', '500', '1K', '2K', '5K', '10K', '20K']
dB_limits   = [-9, +21]
dB_ticks    = [-6, 0, 6, 12, 18]
dB_labels   = ['-6', '0', '6', '12', '18']


def get_bf_eq():
    """ Queries Brutefir TCP service to get the current EQ magnitudes
    """
    cmd  = 'lmc eq "c.eq" info;'
    ans = ''
    with socket() as s:
        try:
            s.connect( ('localhost', 3000) )
            s.send( f'{cmd}; quit;\n'.encode() )
            while True:
                tmp = s.recv(1024)
                if not tmp:
                    break
                ans += tmp.decode()
            s.close()
        except:
            print( f'(brutefir_eq2png) unable to connect to Brutefir:3000' )

    for line in ans.split('\n'):
        if line.strip()[:5] == 'band:':
            freqs = line.split()[1:]
        if line.strip()[:4] == 'mag:':
            mags = line.split()[1:]

    return np.array(freqs).astype(float), \
           np.array(mags).astype(float)


def do_graph(freqs, magdB, is_lin_phase=False):
    """ Dupms a graph to PNG_PATH
    """
    if verbose:
        print( f'(brutefir_eq2png) working ... .. .' )

    # Customize figure and axes
    fig, ax = plt.subplots()
    fig.set_figwidth( 5 )   # 5 inches at 100dpi => 500px wide (same as DRC graph)
    fig.set_figheight( figHeight )
    fig.set_facecolor( RGBweb )
    ax.set_facecolor( RGBweb )

    if is_lin_phase:
        ax.annotate('lin-pha EQ', xy=(.46,.1), xycoords='axes fraction')

    ax.set_xscale('log')
    ax.set_xlim( freq_limits )
    ax.set_xticks( freq_ticks )
    ax.set_xticklabels( freq_labels )

    ax.set_ylim( dB_limits )
    ax.set_yticks( dB_ticks )
    ax.set_yticklabels( dB_labels )

    # ax.set_title( 'Brutefir EQ' )
    # Plot the EQ curve
    ax.plot(freqs, magdB,
            color=lineColor,
            linewidth=3
            )
    # Save to file
    plt.savefig( PNG_PATH, facecolor=RGBweb )
    if verbose:
        print( f'(brutefir_eq2png) saved: \'{fpng}\' ' )
    # (!) PLEASE comment out the safe backend Agg line before using plt.show()
    #plt.show()


if __name__ == '__main__':

    if sys.argv[1:]:
        if '-v' in sys.argv[1]:
            verbose = True
        if '-h' in sys.argv[1]:
            print(__doc__)
            exit()

    # Check bfeq_linear_phase config
    CONFIG = yaml.safe_load( open(f'{UHOME}/pe.audio.sys/config/config.yml', 'r') )
    try:
        if CONFIG['bfeq_linear_phase']:
            is_lin_phase = True
        else:
            is_lin_phase = False
    except:
        is_lin_phase = False

    freqs, magdB = get_bf_eq()
    do_graph(freqs, magdB, is_lin_phase=is_lin_phase)
