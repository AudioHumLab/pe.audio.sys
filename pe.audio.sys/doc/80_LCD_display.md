# LCD for pe.audio.sys

<a href="url"><img src="./images/lcd%20display%20v0.1.jpg" align="center" width="340" ></a>


# Get the LCD hardware

See here:
https://github.com/AudioHumLab/FIRtro/wiki/855-Display-LCD


# The software

The recent Debian `lcdproc` packages comes precompiled **without** USB4ALL support, so DO NOT INSTALL the **lcdproc** APT package.

You'll need to get the latest release from the lcdproc repository (probably 0.5.9), see here: https://github.com/lcdproc/lcdproc/releases

    mkdir tmp
    cd tmp
    wget https://github.com/lcdproc/lcdproc/releases/download/v0.5.9/lcdproc-0.5.9.tar.gz
    tar -xzvf lcdproc-0.5.9.tar.gz

Then compile **SEE NOTE BELOW**

    sudo apt install pkg-config build-essential libncurses5-dev libusb-dev libfreetype-dev automake autoconf m4 perl

    cd lcdproc-0.5.9
    ./configure --prefix=/usr/local --enable-drivers=hd44780,curses
    make
    sudo make install

The above `--prefix=/usr/local` is not mandatory, you only need the binaries `lcdproc` `LCDd` and the drivers `hd44780.so` `curses.so`. But `/usr/local` is the standard choice.

As per above, lcdproc drivers will be located under `/usr/local/lib/lcdproc/` then you need to point to that location under `pe.audio.sys/share/plugins/lcd/LCDd.conf`:

    DriverPath=/usr/local/lib/lcdproc/

Other configuration settings are already provided in `share/plugins/lcd/LCDd.conf`

### COMPILATION WILL FAIL in recent Ubuntu distros >= 24.04 with kernel 6

I don't know the reason why, maybe some old compile directives in lcdproc 0.5.9 need to be updated.

A workaround is to compile it in another machine with an older Debian system, for instance a VM running Ubuntu 18.04.

Once compiled, simply copy all the ldcproc staff `/usr/local/.....` to your current system.


## usb4all needs USB permissions

Prepare `/etc/udev/rules.d/50-usb.rules`

    # allow access to usb devices for users in dialout group
    SUBSYSTEM=="usb", MODE="0666", GROUP="dialout"

And include your user into the `dialout` group:

    sudo usermod -G dialout -a YOURUSER

**Reboot the machine**

## Testing the LCD

(i) Please edit and uncomment the appropiate driver line for your machine arch:

    $ nano pe.audio.sys/share/plugins/lcd/LCDd.conf

Try to start the server:

    $ LCDd -c pe.audio.sys/share/plugins/lcd/LCDd.conf

Test the standard packaged client:

    $ lcdproc -f  &

    $ killall lcdproc      # to stop the show

## Enabling pe.audio.sys info to be displayed on the LDC

Enable a `- lcd.py` under the `plugins` section at `config.yml`.
