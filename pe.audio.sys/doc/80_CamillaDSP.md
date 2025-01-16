## CamillaDSP

From version 2.0, we can use CamillaDSP, by now only used to provide an optional compressor.

The compressor is designed to facilitate the intelligibility of movies with difficult to hear  dialogues at low listening levels.

You'll need to prepare 2 packages:
1. The [CamillaDSP](https://github.com/HEnquist/camilladsp) itself
2. The Python library [PyCamillaDSP](https://github.com/HEnquist/pycamilladsp)

### 1. Install CamillaDSP with the JACK backend

CamillaDSP pre-built binaries only provides ALSA or Pulseaudio backend. We need to compile our in order to include the **JACK audio backend**.

NOTE: do not need `sudo`, just complite under your pe.audio.sys regular Linux user.

#### Get the RUST compiler

    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

#### Install compiler dependencies

    sudo apt-get install pkg-config libasound2-dev openssl libssl-dev \
                 jackd2 libjack-jackd2-dev

#### Get the CamillaDSP source code

https://github.com/HEnquist/camilladsp/releases


#### Compile

    RUSTFLAGS='-C target-feature=+neon -C target-cpu=native' \
    cargo build --release --features jack-backend

Finally, copy the binary to your `~/bin` folder, in order to be available for the pe.audio.sys scripts.

    cp target/release/camilladsp ~/bin/

MORE INFO [here](https://github.com/HEnquist/camilladsp/tree/master?tab=readme-ov-file#building)

### 2. Install the Python library PyCamillaDSP

PyCamillaDSP does not comes in a Debian/Ubuntu APT package. Then, Python packages which are not distributed in APT packages, need to be installed and executed in a "separate" Python space, i.e. a **Python Virtual Environment**. 

Details here https://github.com/HEnquist/pycamilladsp/blob/master/docs/install.md

In summary, under your home directory `/home/YOURUSER` (user level) follow as below:

    # This prepare the VENV with links to your site APT Python packages
    # ... it takes a while ...
    $ python -m venv --system-site-packages ~/.env

    # This activates the VENV
    $ source ~/.env/bin/activate
    (.env) $ _
    
    # Here you will install the NON APT Python packages:
    
    (.env) $ pip3 install sounddevice websocket_client
    (.env) $ pip3 install git+https://github.com/HEnquist/pycamilladsp.git

    
    # Deactivate is NOT necessary, only informative
    (.env) $ deactivate

    # Here you are back again in your regular environment
    $ _

**NOTICE:**

In order to use (import) the new python modules, you'll need to run `source ~/.env/bin/activate`. If not, imports will fail.

Once activated you will be able to work normally on your system, VENV is transparent.

pe.audio.sys scripts take care of this for you, automatically, so you don't need to manually activate the VENV to run pe.audio.sys.









