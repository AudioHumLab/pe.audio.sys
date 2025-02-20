## ACHTUNG:

First of all it is strongly recommended that your Linux distro has Python3 version >= 3.6,
so try to upgrade your Linux before continue.

## Your Linux enviroment and packages:

See here: 

https://github.com/AudioHumLab/FIRtro/wiki/04a-Instalación-de-Linux-y-paquetes-de-SW

### Usually it is enough:

- add the **`paudio`** user to your system, this is optional because you can run the **pe.audio.sys** system under **ANY USER ACCOUNT** if you want so.

    `sudo adduser paudio`

- then integrate the user which will run pe.audio.sys into convenient groups:

    `sudo usermod -a -G cdrom,audio,video,plugdev YourUserHere`
    
- also for serial access stuff (usbrelay, IR, etc):

    `sudo usermod -a -G dialout YourUserHere`

Unlike `FIRtro` or `pre.di.c` **enviroment settings**, here it is no longer needed to point the PYTHONPATH environment variable to your `pe.audio.sys` directories. So, no special user profile is needed here.


## Tuning `nano` and `less`

Please use spaces for tab indenting:

    $ cp /etc/nanorc ~/.nanorc
    $ nano ~/.nanorc

        ## Use this tab size instead of the default; it must be greater than 0.
        set tabsize 4

        ## Convert typed tabs to spaces.
        set tabstospaces

        ## Snip whitespace at the end of lines when justifying or hard-wrapping.
        set trimblanks

The last one will trim blank spaces at line endings when you justify (Ctrl-J or ESC-J)

To enable `less` to highlight source code and formatted text (bold, etc), please include this at the end of your `~/.profile`

    export LESSOPEN='| /usr/share/source-highlight/src-hilite-lesspipe.sh %s'
    export LESS=' -R'


## Headless machine (no desktop)

Update your `~/.profile`:

    export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket


Enable your user to access the sound card under the dbus system enviroment:

```
sudo nano /etc/dbus-1/system-local.conf
```

```
<busconfig>
    <policy user="YourUserHere">
        <allow own="org.freedesktop.ReserveDevice1.Audio0"/>
        <allow own="org.freedesktop.ReserveDevice1.Audio1"/>
        <allow own="org.freedesktop.ReserveDevice1.Audio2"/>
        <allow own="org.freedesktop.ReserveDevice1.Audio3"/>
    </policy>
</busconfig>
```
    
```
sudo service dbus restart
```
    

## Main packages

Also install the following packages on your linux installation:

```
sudo apt update && sudo apt upgrade
```

```
sudo apt install jackd2 brutefir alsa-utils libasound2-dev libasound2-plugins \
                 libjack-jackd2-dev libsamplerate0 libsamplerate0-dev \
                 mpd mpc gmpc ncmpcpp mplayer cdtool zita-ajbridge zita-njbridge \
                 apache2 libapache2-mod-php php-yaml mc jq anacron \
                 source-highlight git netcat-openbsd
```

(i) `netcat` seems to be a legacy package. If you have Debian version < 12 _bookworm_, please use `netcat`. If `nc` does not work for you, try instead `netcat-traditional`.

You **MUST** be vigilant during the installation to answer YES when asked for enable **"real time" for JACK**.

(i) We have chosen to install Midnight Commander `mc` because it is a helpful console based file browser. The comand line tool `jq` can be useful to read json files from command line. `anacron` supports daily automatic updates of pe.audio.sys.

Obsolete (only if you plan to use PEQ based in Ecasound), but we are planing to use CamillaDSP for this (work in progress)
```
    sudo apt install ecasound ecatools python3-ecasound ladspa-sdk fil-plugins 
```

**Disable default MPD setup:**

Recent MPD packages does not load the MPD as a system service, so you may not need to disable it.

    $ pgrep -f mpd

Only if needed, you must disable it:

    sudo systemctl stop mpd.socket
    sudo systemctl disable mpd.socket
    sudo systemctl stop mpd.service
    sudo systemctl disable mpd.service
    sudo systemctl --global stop mpd.socket
    sudo systemctl --global disable mpd.socket
    sudo systemctl --global stop mpd.service
    sudo systemctl --global disable mpd.service


## Python3 packages

Please refer to the doc file here: [02_Python 3.md](./02_Python%203.md)


## Special permission for your user to reboot the machine

If so, you can set it by running **`EDITOR=nano sudo visudo`**, then add the following:

    # 'myUSER' user can reboot the machine:
    myUSER          ALL=NOPASSWD:/sbin/reboot

