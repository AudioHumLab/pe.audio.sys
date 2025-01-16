
# Credits

This is based on the **FIRtro** and **pre.di.c** projects, as PC based digital preamplifier and crossover projects, designed by the pioneer **@rripio** and later alongside others contributors.


https://github.com/rripio/pre.di.c

https://github.com/AudioHumLab/FIRtro/wiki

The main software on which this project is based:

- XOVER filtering, DRC and soft EQ: the **Brutefir** convolution engine https://torger.se/anders/brutefir.html

- Audio connections: **JACK** https://jackaudio.org


Other GNU audio software we use here:

- [CamillaDSP](https://github.com/HEnquist/camilladsp), currently used for some EQ purposes.
  
- Networked audio and IIR filtering are based on **Fons Adriaensen** utilities https://kokkinizita.linuxaudio.org/linuxaudio

- For music files library playing we use **MPD** (Music Player Daemon)

- For CD, DVB-T (digital terrestial radio broadcasting) or internet streamed music we use **Mplayer**

- Former IIR filtering plugins were supported by **Ecasound** (obsolete currently)


Most of the system is written in Python3, and config files are YAML kind of, thanks @rripio.

The control of the system is based on a tcp server architecture, thanks @amr.


# Introducing pe.audio.sys

**pe.audio.sys** is a **DIY** audio project, aimed at achieving the best management for a loudspeaker system.

It is a versatile, and **fully customizable Linux platform based audio system,** providing an **user friendly interface**.

Its main feature is the management, filtering and EQ of a **multiway active loudspeaker system**. A regular passive loudspeakers can be used as well.

Full hi-fi preamplifier features are available.

In addition, you can control unlimited audio sources:

- External audio sources:

    - DVB-T radio (USB dongle)
    - Apple TV box, cable TV
    - TV
    - Analog sources (FM, vinyl, ...)
    - etc ...

- Internal audio sources:

    - CD drive
    - Internet radio
    - Spotify
    - Hard Disk mp3/flac/aiff/wav files
    - Desktop apps (i.e: Youtube, etc )


## EQ capabilities

- Loudspeaker anechoic correction
- Digital Room Correction
- Multiway crossover
- Advanced FIR filtering (optionally traditional IIR filtering)
- Target EQ curves for subjective in room responses


## System control

Simple control from your smartphone, tablet or desktop **web browser**.


<a href="url"><img src="./pe.audio.sys/doc/images/web%20inputs%20selector%20and%20macros%20buttons.png" align="center" width="400" ></a>


- Main control web features are:

    - **Calibrated volume listening** supported by an EBU R128 Loudness monitor.

    - Calibrated **equal loudness compensation curves** (ISO 226:2003 standard) for low SPL listening without loosing low and high bands perception

    - Hi-Fi preamp controls (volume, tone, balance, subsonic, stereo/mono, mute, loudness, source selector, amplifier on/off)

    - User defined presets for EQ modes and xover FIR filtering

    - User defined macro buttons for easy listening to file playlist or Spotify playlists, preferred radio stations, etc...

    - Displays metadata, bitrate and time of playback sources.

    - Playback control (pause, next, prev, etc) for integrated players (Spotify desktop, MPD daemon, CD).


- Optional control by a **remote IR**

- Optional **LCD display** for basic information and playback metadata visualization.

- A **mouse** attached to a pe.audio.sys 'black box' can be used as an easy-access **volume/mute control**.


## System maintenace

An simple script will update the whole system from GitHub, without user intervention. 


## System usage and configuration

See files and FAQ under the **`doc/`** folfer


## Loudspeaker EQ and multiway XOVER filtering

**https://github.com/rripio/DSD** is a tool to design your own FIRs (loudspeaker EQ and XOVER), from the pioneer @rripio.

We also recommend **rePhase** for FIR design.

## Room correction EQ (DRC)

Regarding room correction EQ, you can use both IIR (parametric correction) or FIR (impulse correction).

FIR DRC is supported under a reserved convolver stage on Brutefir.

IIR DRC can be implemented through by the provided Ecasound add-on script, then bypassing the convolver stage above.

The most popular software for room Eq is REW https://www.roomeqwizard.com

As experimental FIR DRC correction software you could also consider:

**https://github.com/rripio/DSC**

**https://github.com/Rsantct/DRC**



# Some sample use cases


## 'Black box' or 'Desktop' configuration

pe.audio.sys is designed to be a **'black box'** headless system, no monitor keyboard or mouse are needed at all. If needed, you can stream audio wirelessly from your smartphone or tablet to the 'black box'.

In addition, the system can be easily integrated in a **Linux Desktop with monitor, keyboard and mouse**, no special configurations are needed. This way you can listen to your favourite desktop applications as Spotify, Youtube, watching movies, etc...

My preferred system configuration is a **'headless Desktop'**, because this way you can have a Spotify Desktop application running on background, which will provide full metadata info to be displayed under the control web page or the optional LCD display, without needing an attached monitor. Anyway you can use your TV-hdmi as monitor for pe.audio.sys.


## Hard Disk music files library

MPD (Music Player Daemon) is integrated as the player for your audio files.

You can control your playback in several ways:

- Web page user defined buttons for launching favourites playlist to be played
- Web playback control buttons: next, previous, pause, ...
- A samartphone/tablet MPD app for a total control of the music library
- A desktop MPD application (regular desktop usage of mouse and keyboard)


## CD discs

You can play CD directly on your CD drive unit, or by an external CD player.

When you use the internal one drive, the CD metadata (artist, album, title) will
be displayed on the control web page or on the optional LCD display.


## Spotify

You can use your smartphone or tablet Spotify App to control the integrated Spotify player.

So the Spotify App simply controls the _Spotify connect_ client inside pe.audio.sys, but the audio stream comes directly from the
internet to your system loudspeakers.

In a desktop system, you can also use a Linux desktop Spotify application.


## Radio stations

In current days, the best audio quality radio is available from the TV terrestial broadcast network (DVB-T). You will need a DVB-T USB dongle, see details under the `/doc/90_FAQ.md` and `share/scripts/DVB-T.py`.

In addition, you can listen to Internet Radio stations or audio streams without any extra hardware, see `share/scripts/istreams.py`.

Also, a classical FM tuner can be attached via analog sound card inputs.


## Amplifier power on/off

A script is provided for you to switch a relay USB controlled socket strip.


## Multiroom audio

You can easily configure two networked pe.audio.sys loudspeaker systems to listen from each
other. 

If desired, the volume level on both can be linked.


## Switch over from my iPhone

When arriving home while listening to your favourite podcast through by your iPhone phones, you can easily
switch to listen through by your pe.audio.sys loudspeakers:

- Power on pe.audio.sys, then select source: Airplay (integrated) or Apple TV (optional external)

- On your iPhone select Airplay 'pe.audio.sys' (or 'Apple TV').


