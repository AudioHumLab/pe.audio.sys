
## December 18, 2020: version 1.0 released

- `share/eq/*.dat` multicurve files has changed its internal arrangement
- Equal loudness related commands and parameters has changed

See the `doc/` folder for detailed information about this.

**PLEASE UPDATE:**

- your `share/eq/*.dat` multicurve files with the new ones
  provided under `share/eq/eq.sample.R20_audiotools/`

    ```
    bass_mag.dat
    bass_pha.dat
    treble_mag.dat
    treble_pha.dat
    ref_XX_loudness_mag.dat
    ref_XX_loudness_pha.dat
    ```
    
- your `config.yml`:

    ```
                        refSPL=XX       (new item)
    loud_ceil       --> eq_loud_ceil
    loudness_track  --> equal_loudness
    ```

- your `.state.yml`:

    ```
    loudness_track:  --> equal_loudness: true|false
    loudness_ref:    --> lu_offset: XX
    ```

- your `macros/` files if them issue any loudness command


## Jan 2021, version 1.0a

- New script `zita_link.py`, a LAN one-to-one audio receiver based on zita-njbridge from Fons Adriaensen, replaces former zita multicast versions, for 'remote' sources usage.

- New Bluetooth receiver: `script/pulseaudio-BT.py` and related doc/ and macros to listen to Bluetooth sources.

- New `script/node_web_server.py` replaces calling node from /etc/rc.local

- Some fixes and documentation.


## May 2021, version 1.0b

- New documentation for remote pe.audio.sys sources listening.

- New Firewire Audio Interfaces support.

## Sep 2021, version 1.0c

- New subsonic filter as optional preamp feature.

## Oct 2021, version 1.0d

- New folder layout for log & config files, **PLEASE** move your `xxx.yml` files to `pe.audio.sys/config/`, as well your `.asound.XXX` or `.ffado.GUID` files but without the leading `.`(dot)

## Dec 2021, version 1.0e

- The state file becomes json instead of yaml in order to improve parsing times about 30% faster. (See FAQ for help on converting `.state` to json)
- Playback control is forwarded to a remote pe.audio.sys when listening to remote sources.
- New warning temporary message internal facilities.
- New playlist selector for MPD, Spotify
- New track selector for CD
- New random playback control

## Jan 2022, version 1.0f

- New `config.yml` layout for jack and sound cards stuff. **PLEASE** update your `config.yml` accordingly (see `config.yml.sample`)

## Nov 2022, version 1.0g

- The multiroom LAN one-to-one audio connection based on zita-njbridge, becomes integrated, no plugin is needed.
- Web control page updated: new TONE DEFEAT, new STEREO MODE BUTTONS.
- LCD now displays temporary messages.
- Spotify Connect for headless (librespot) updated.
- `scripts` becomes `plugins` **PLEASE** update your **`config.yml`** with `plugins:` section.
- Several fixes and updates.

## Dec 2023, version 1.0h
- Optional volume control over ALSA mixer.
- Jacktrip server (host mode) pluging: receive audio by wired network from any Jacktrip (client).
- USB DAC watchdog plugin: restarts pe.audio.sys after the USB DAC changes from standby to power on mode.
- L/R channels from source to preamp can be swapped, useful for some wrong downmix to stereo soundtracks.

## Dec 2023, version 1.0i
- Human readable Brutefir configuration with `loudspeakers/<LSPK>/config.yml`
- Easiest upgrade with `bin/peaudiosys_upgrade.sh` involving downloading and updating.

## Jan 2024, version 1.0j
- Python Virtual Environment compliant as per PEP 668 for using non-Debian Python packages.
  
## Jul 2024, version 1.0k
- DVB-T volume adjustement for multichannel AC3 streams
- A macro template to playing an akamaized m3u8 stream througby MPD (some internet radios as RTVE)
- Audio format and bitrate info in control web
  
## Nov 2024, version 1.0l
- CD playback leaves Mplayer and runs with MPD.
- Web page includes wifi, temperature and fan speed info.
- New Brutefir peaks monitor plugin with a dedicated web page `http://<IP>/monitor.html`.
- Scripts to help while testing a loudspeaker design at `bin/peaudiosys_test/`.

## Jan 2025, version 2.0 beta
- 1st integration of CamillaDSP, currently only provides the optional compressor, more to coming ;-)
- New optional compressor useful for watching movies with difficult dialogue dynamics at low listening levels.

## Feb 2025, version 2.0a
- adapt to PipeWire (optional)
- update some doc about DVB-T and LCD
  
