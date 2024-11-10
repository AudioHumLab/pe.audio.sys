#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez
# This file is part of 'pe.audio.sys'
# 'pe.audio.sys', a PC based personal audio system.

""" A module to manage CD-AUDIO
"""

import  musicbrainzngs as mz
import  json
import  sys
import  os
from    socket import gethostname
from    miscel import CONFIG, CDDA_META_PATH, CDDA_META_TEMPLATE,   \
                      CDDA_MUSICBRAINZ_PATH,                        \
                      Fmt, time_msec2mmsscc, read_mpd_config

try:
    import  discid
except Exception as e:
    print(str(e))
    print(f'{Fmt.BOLD}{Fmt.BLINK}Have you activated your Python Virtual Environment?{Fmt.END}')


UHOME = os.path.expanduser("~")

MPD_M3U_PATH = f'{ read_mpd_config()["playlist_directory"] }/cdda_{gethostname()}.m3u'
MPD_PLS_PATH = f'{ read_mpd_config()["playlist_directory"] }/cdda_{gethostname()}.pls'

if 'cdrom_device' in CONFIG:
    CDROM_DEVICE = CONFIG['cdrom_device']
else:
    CDROM_DEVICE = '/dev/cdrom'
    print(f'{Fmt.BLUE}(cdda.py) Using default \'{CDROM_DEVICE}\'{Fmt.END}')


def _get_disc_metadata(device=CDROM_DEVICE):

    def find_medium_list_idx(disc_id, medium_list_items):
        """
            Double CD sets, will have several medium-list items
            and we need to choose the one matching our disc.id
        """

        idx = 0

        for i, item in enumerate(medium_list_items):

            for dl_item in item["disc-list"]:

                if disc_id==dl_item["id"]:

                    idx = i
                    break

        return idx


    def simple_md(disc_obj):
        """ For disc not found, we can just derive the number of tracks
            and its length from the <disc_obj> object properties.
        """
        smd = CDDA_META_TEMPLATE.copy()

        smd['discid'] = disc_obj.id

        ntracks = disc_obj.last_track_num

        print( f'{Fmt.RED}(cdda.py) Unknown CD: discid `{disc_obj.id}` with {ntracks} tracks.{Fmt.END}' )

        # https://musicbrainz.org/doc/Development/XML_Web_Service/Version_2#discid
        # The toc consists of the following:
        #   First track (always 1)
        #   total number of tracks
        #   sector offset of the leadout (end of the disc
        #   a list of sector offsets for each track, beginning with track 1 (generally 150 sectors)
        #
        # Example of TOC for a 7 tracks disc:
        # disc_obj.toc_string: '1 7 235745 150 40742 77847 108042 118682 154277 191952'

        toc = disc_obj.toc_string.split()

        # A second of CD-AUDIO has 75 frames (or sectors) -wikipedia-
        track_sectors = toc[3:] + [toc[2]]
        track_sectors = [int(x) for x in track_sectors]

        for i in range(len(track_sectors)):

            if i == 0:
                continue

            trackNum = i
            trackLen = ( track_sectors[i] - track_sectors[i - 1] ) / 75

            smd["tracks"][str(trackNum)] = {'title': 'track ' + f'{trackNum}'.zfill(2),
                                 'length': time_msec2mmsscc(trackLen * 1e3)}

        return smd


    # (!) MUST clear the `tracks` values after loading the template
    md = CDDA_META_TEMPLATE.copy()
    md["tracks"] = {}

    try:
        disc_obj = discid.read(device)
        md['discid'] = disc_obj.id

    except:
        print(f'{Fmt.RED}(cdaa.py) not CDDA found{Fmt.END}')
        return md

    try:
        mz.set_useragent('tmp', '0.1', 'dummy@mail')
        mz_result = mz.get_releases_by_discid( disc_obj.id,
                                               includes=['artists', 'recordings']
                                             )
        with open(CDDA_MUSICBRAINZ_PATH, 'w') as f:
            f.write( json.dumps( mz_result ) )
        print(f'{Fmt.GRAY}(cdda.py) Full musicbrainz CD data saved to {CDDA_MUSICBRAINZ_PATH}{Fmt.END}')

    except Exception as e:

        print(f'{Fmt.BOLD}(cdda.py) Musicbrainz disc not found or bad response: {str(e)}{Fmt.END}')
        return simple_md(disc_obj)


    # most of discs are 'disc' musicbrainz kinf of
    if mz_result.get('disc'):

        print(f'{Fmt.BLUE}(cdda.py) musicbrainz got \'disc\': {disc_obj.id}{Fmt.END}' )

        mz_md = mz_result['disc']['release-list'][0]

        md['artist'] = mz_md['artist-credit-phrase']

        md['album']  = mz_md['title']

        # (!) Double CD sets, will have several medium-list
        medium_list_idx = find_medium_list_idx( disc_obj.id, mz_md['medium-list'] )

        track_list   = mz_md['medium-list'][medium_list_idx]['track-list']

    # but somo are 'cdstub' musicbrainz kind of
    elif mz_result.get('cdstub'):

        print(f'(cdda.py) musicbrainz got \'cdstub\': {disc_obj.id}' )

        mz_md = mz_result['cdstub']

        # JUST MAKE A SIMPLE MD
        return simple_md(disc)


    # Lets complete our track list structure inside the 'md' template
    for n, track in enumerate( track_list ):

        # Retrieve the track length MM:SS.CC

        # from normal 'disc':
        if 'recording' in track and 'length' in track['recording']:
            t_len = time_msec2mmsscc( float(track['recording']['length']) )

        # from some 'cdstub':
        elif 'length' in track:
            t_len = time_msec2mmsscc( float(track['length']) )

        # from some 'cdstub':
        elif 'track_or_recording_length' in track:
            t_len = time_msec2mmsscc( float(track['track_or_recording_length']) )

        else:
            t_len = time_msec2mmsscc( 0.0 )

        #  Retrieve the track title
        if 'recording' in track and 'title' in track['recording']:
            t_tit = track['recording']['title']

        elif 'title' in track:
            t_tit = track['title']

        # some track names can be prefixed with the album title, this is redundant
        if md["album"] in t_tit:

            new_t_tit = t_tit.replace(md["album"], '').strip()

            # avoid leaving blank if the track and the album titles are equals
            if new_t_tit:
                t_tit = new_t_tit

            # removing some possible prefix separators
            if t_tit[0] in (':', ',', '.'):
                t_tit = t_tit[1:].strip()

        # Retrieve the track position
        if 'position' in track and track["position"]:
            t_pos = str(track["position"])
        else:
            t_pos = str(n + 1)

        # Adding to our metadata disc structure
        md["tracks"][ t_pos ] = { 'title':  t_tit,
                                 'length': t_len }

    return md


def _save_cdda_playlist( md={} ):
    """ Saves a playlist for MPD :-)
        (PLS mode is not tested)
    """

    def make_m3u(md):

        m3u =   '#EXTM3U\n'

        for k, v in md["tracks"].items():

            durationms = time_msec2mmsscc( string=v["length"] )
            durationsec = str( int(round( durationms / 1e3, 0)) )

            m3u += '#EXTINF:'
            m3u += f'{durationsec},'
            m3u += f'{v["title"]}\n'
            m3u += f'cdda:/{CDROM_DEVICE}/{k}\n'

        return m3u


    def make_pls(md):

        pls =   '<?xml version="1.0" encoding="UTF-8"?>\n'
        pls +=  '<playlist version="1" xmlns="http://xspf.org/ns/0/">\n'
        pls +=  '  <trackList>\n'

        for k, v in md["tracks"].items():

            duration = time_msec2mmsscc( string=v["length"] )

            pls +=  '    <track>\n'
            pls += f'      <location>cdda:///{k}</location>\n'
            pls += f'      <creator>{md["artist"]}</creator>\n'
            pls += f'      <album>{md["album"]}</album>\n'
            pls += f'      <title>{v["title"]}</title>\n'
            pls += f'      <duration>{duration}</duration>\n'
            pls +=  '    </track>\n'

        pls +=  '  </trackList>\n'
        pls +=  '</playlist>\n'

        return pls


    with open(f'{MPD_M3U_PATH}', 'w') as f:
        f.write( make_m3u( md ) )
    print(f'{Fmt.BLUE}(cdda.py) MPD CD playlist saved to {MPD_M3U_PATH}{Fmt.END}')

    with open(f'{MPD_PLS_PATH}', 'w') as f:
        f.write( make_pls( md ) )
    print(f'{Fmt.BLUE}(cdda.py) MPD CD playlist saved to {MPD_PLS_PATH}{Fmt.END}')



def dump_cdda_metadata(device=CDROM_DEVICE):
    """ dump CD-Audio disc matadata to:

            pe.audio.sys/.cdda_metadata

            <MPD_playlists_folder> / cdda_<hostname>.m3u + pls
    """

    md = _get_disc_metadata(device)

    with open(CDDA_META_PATH, 'w') as f:
        f.write( json.dumps( md ) )

    if md["discid"]:

        print(f'{Fmt.BLUE}(cdda.py) CD metadata saved to {CDDA_META_PATH}{Fmt.END}')

        _save_cdda_playlist( md )



if __name__ == "__main__":

    #if sys.argv[1:] and '-d' in sys.argv[1]:
    #    dump_cdda_metadata()
    pass
