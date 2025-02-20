## Requires Python >= 3.6 (recommended >= 3.10)

### Python3 standard packages (Numpy, Jack, MPD, etc):

#### Debian packages:

    sudo apt install python3-venv python3-pip python3-dev python3-yaml python3-jack-client \
         python3-mpd python3-pydbus python3-numpy python3-scipy python3-matplotlib libffi-dev \
         python3-pyudev python3-libdiscid python3-musicbrainzngs libportaudio2 python3-watchdog \
         python3-serial python3-m3u8 python3-psutil


#### Non-Debian packages:

Some Python packages are not distributed in Debian, so let's use the official Python package manager PIP

**NOTICE:**

As per PEP 668, Python packages outside your O.S. distribution must be installed in a Python Virtual Enviroment (aka **`venv`**)

The easiest way to do this is to prepare a `venv` for your user profile, then use `pip3` inside it to install Python packages that are not included within your O.S. distribution, as for example `sounddevice` or `discid`.

Even O.S. distribution driven Python packages can be instaled separatelly in your Python `venv`, but we prefer using Debian packages when possible. So let's create a `venv` by **inheriting the system packages**:

    $ python3 -m venv --system-site-packages ~/.env

Lets activate the environment, and go working inside the `venv`:

    $ source ~/.env/bin/activate
    (.env) $

From now on we can use `pip3` to install packages not included within Debian:

    # upgrading PIP first of all
    (.env) $ python3 -m pip install --upgrade setuptools
    #
    (.env) $ pip3 install sounddevice discid


**IMPORTANT**

Please remember when running this project you must activate the Python VENV so that modules can be loaded. The provided `bin/peaudiosys_restart.sh` script will do so automatically.


### Optional to manage volume through by the sound card ALSA mixer:

More info at: `config.yml.sample`

(i) The Debian `python3-alsaaudio` package is likely to be **outdated**, so we use **pip**:

    (.env) $ pip3 install pyalsaaudio

