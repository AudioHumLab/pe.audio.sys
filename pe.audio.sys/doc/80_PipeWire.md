# Integration with the PipeWire desktop sound server

Modern desktops uses PipeWire, for example Ubuntu 24.04 LTS.

Pipewire does EMULATE a PulseAudio like API, in order to players Apps like Spotify to reach the PW desktop sound server.

PW runs as a user session service.

PW integrates a Jack EMULATION, BUT we will NOT use that feature. We want **pe.audio.sys** to be compatible with headless systems without PW, through by our own native JACK sound server.

We will configure PipeWire in order to auto magically emerge a couple of jack ports named `PipeWire`, here we will have all the desktop audio streams, like Spotify.

## Pipewire configuration

Install the JACK bridge: **`sudo apt install pipewire-jack`**

Prepare the following user session PipeWire setting files. You'll find a copy of these files under the `.install/` directory in this repository. These files overrides the same general settings of the base configuration `/usr/share/pipewire/pipewire.conf`


        ~/.config/pipewire/
        │
        │
        ├── pipewire.conf.d
        │   │
        │   │   1) Prepares the PipeWire <--> JACK bridge
        │   │       
        │   ├── 10-paudio-jack.conf
        │   │
        │   │   2) Sets the default sink, for BOTH, PipeWire native clients
        │   │      and Pulseaudio clients
        │   │
        │   └── 50-paudio-default-sink.conf
        │
        ├── client.conf.d
        │   │
        │   │   3) Resampling settings for PipeWire native clients
        │   │
        │   └── paudio-client.conf
        │
        │
        └── pipewire-pulse.conf.d
            │
            │   3) Resampling settings for PulseAudio clients
            │
            └── paudio-pipewire-pulse.conf

You can fine tune the resampling quality.

**Recommended:** monitor the CPU load and posible errors/xruns by running:
- `qjackctl`
- `pw-top`

## OLD Pulseaudio configurations

If you came from a `pe.audio.sys/config/config.yml` based in PulseAudio, **YOU SHOULD NOT USE** the plugin **`pulseaudio-jack-sink.py`** now.

## Spotify users

After restarting **pe.audio.sys**, you need to restart the Spotfy Desktop App in order to reconnect to the new PipeWire-Jack instance.

This is done when using `plugins/spotify_desktop.py`
