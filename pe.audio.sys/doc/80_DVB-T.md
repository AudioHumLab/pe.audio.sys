# 0. NOTICE
This file is an UPDATED COPY from the former project **FIRtro** at https://github.com/AudioHumLab/FIRtro


# 1. HW

## HW para CD audio

Necesitaremos un lector de CD o DVD, interno o externo.

## HW para DVB-T Radio (TDT)

Podemos usar un pincho USB receptor de DVB-T como por ejemplo:

- AverMedia AverTV Volar HD2, USB `https://github.com/OpenELEC/dvb-firmware/blob/master/firmware/dvb-usb-it9135-02.fw`

- (VER NOTA) NPG Real HDTV Nano 3D `http://www.npgtech.com/multimedia/24-categoria-productos/multimedia/51-real-hdtv-nano-3d.html`

![NPG](https://github.com/Rsantct/pe.audio.sys/blob/master/pe.audio.sys/doc/images/NPG%20HDTV%20Nano%203D.jpg)

- Hauppauge WinTv-soloHD (obtener el firmware del fabricante https://www.hauppauge.com/pages/support/support_linux.html) ok 2025-feb

(i) IMPORTANTE: estas tarjetas necesitan un firmware, ver:

`https://github.com/OpenELEC/dvb-firmware/blob/master/firmware`

Los archivos de FW de estas dos tarjetas se han incluido en el repositorio de FIRtro `custom/firmware`.

Podemos hacer un enlace o copiarlo en `/lib/firmware` para que sea reconocido por nuestro sistema Linux:

    sudo ln -s /home/firtro/custom/firmware/dvb_nova_12mhz_b0.inp /lib/firmware/

### Problemas NPG Real HDTV Nano

A partir de Ubuntu 24.04 con kernel 6.xx, ocurren XRUNS y problemas en el kernel (dmesg, journalctl)

    feb 16 10:18:00 salon64 kernel: ------------[ cut here ]------------
    feb 16 10:18:00 salon64 kernel: invalid sysfs_emit_at: buf:00000000c5a69535 at:0
    feb 16 10:18:00 salon64 kernel: WARNING: CPU: 3 PID: 0 at fs/sysfs/file.c:777 sysfs_emit_at+0x64/0xd0
    ...
    feb 16 10:18:00 salon64 kernel:  smsdvb_print_dvb_stats+0x4d/0x490 [smsdvb]
    feb 16 10:18:00 salon64 kernel:  smsdvb_update_dvb_stats+0x2c/0x280 [smsdvb]
    feb 16 10:18:00 salon64 kernel:  smsdvb_onresponse+0x1fd/0x660 [smsdvb]
    feb 16 10:18:00 salon64 kernel:  smscore_onresponse+0x94/0x520 [smsmdtv]
    feb 16 10:18:00 salon64 kernel:  ? dma_unmap_page_attrs+0x1a4/0x210
    feb 16 10:18:00 salon64 kernel:  smsusb_onresponse+0x117/0x220 [smsusb]
    ...
    feb 16 10:18:00 salon64 kernel: ---[ end trace 0000000000000000 ]---

Según pruebas realizadas parece ser que `firmware/dvb_nova_12mhz_b0.inp` no es compatible con kernel 6.xx


# 2. Módulos del kernel para DVB

Comprobaremos si ya está cargado el módulo smsdvb:

    $ lsmod | grep dvb
    smsdvb                 10135  0 
    dvb_core               81168  1 smsdvb
    smsmdtv                35301  2 smsdvb,smsusb

Si fuera necesario habría que indicarlo en el archivo `/etc/modules` de carga de módulos del sistema:

    sudo echo '# Carga el modulo para tarjetas DVB' >> /etc/modules
    sudo echo 'smsdvb' >> /etc/modules

Al pinchar el receptor TDT en un puerto usb podremos comprobar que el sistema lo reconoce:

    $ dmesg | tail
    [ 9339.333046] usb 1-1.5: New USB device found, idVendor=187f, idProduct=0201
    [ 9339.333088] usb 1-1.5: New USB device strings: Mfr=1, Product=2, SerialNumber=0
    [ 9339.333107] usb 1-1.5: Product: MDTV Receiver
    [ 9339.333123] usb 1-1.5: Manufacturer: MDTV Receiver
    [ 9339.334971] smsusb:smsusb_probe: board id=3, interface number 0
    [ 9339.826931] DVB: registering new adapter (Siano Nova B Digital Receiver)
    [ 9339.828030] usb 1-1.5: DVB: registering adapter 0 frontend 0 (Siano Mobile Digital MDTV Receiver)...
    [ 9339.828408] smsdvb:smsdvb_hotplug: DVB interface registered.
    [ 9339.828426] smsmdtv:smscore_init_ir: IR port has not been detected
    [ 9339.828441] smsusb:smsusb_probe: Device initialized with return code 0


# 3. SW reproductor `mplayer`

    sudo apt-get install mplayer

Optamos por **mplayer** en lugar de **mplayer2** ya que este último ha quedado sin mantenimiento.

Configuración de usuario:

    mkdir /home/firtro/.mplayer
    nano /home/firtro/.mplayer/config


        # Write your default config options here!
        
        # NOTA: mplayer automáticamente resamplea si es necesario, ademas la Fs se controla en initfirtro.py
        # Resample the sound to 44100Hz
        #af=resample=44100:0:2
        
        # NOTAS para FIRtro2
        # - El nombre de puerto en jack depende del perfil (tdt/cdda)
        # - No indicamos puertos de destino, para que no se autoconece en jack
        #   al arrancar o al resintonizar aunque no esté seleccionado como entrada.
        ao=jack:name=mplayer:noconnect
        
        [tdt]
        ao=jack:name=mplayer_tdt:noconnect
        
        [cdda]
        ao=jack:name=mplayer_tdt:noconnect
        

Crear los archivos especiales fifo que servirán para enviar órdenes a mplayer:

    mkfifo /home/firtro/cdda_fifo
    mkfifo /home/firtro/tdt_fifo

# 4. SW: aplicaciones para DVB

    sudo apt-get install dvb-apps w-scan


## 4.1. Escaneo de los canales DVB-T

Buscamos canales y los guardamos en un archivo

    w_scan -ft -cES -M > /home/firtro/.mplayer/channels.conf

Notas:  

    X = czap/tzap/xine channels.conf
    x = "initial tuning data" for Scan
    G = Gstreamer dvbsrc Plugin
    k = channels.dvb for Kaffeine
    L = VLC xspf playlist (experimental)
    M = mplayer format, similar to X

Más info: http://linuxtv.org/wiki/index.php/W_scan

## 4.2. Reproducción de un canal

Normalmente reproduciremos los canales con los scripts que se explican en la Guía del usuario. Podemos 
probar la reproducción de forma manual:

    mplayer dvb://'Radio Nacional'

# 5. Observaciones sobre formatos de audio en DVB-T Radio (TDT)

Es posible percibir un volumen distinto resintonizando la misma emisora.

A veces mplayer sintoniza la misma emisora pero toma distintos PID por una mecanismo que no conocemos. Cada PID viene con un formato de audio distinto y mplayer usa un decoder distinto. Eso puede resultar en que 2 ch montados en A52 (Dolby multicanal) se oirán más bajo que si van montados en MPA.

Ejemplo: el archivo de emisoras escaneadas `.mplayer/channels.conf` tiene dos PID (penúltimo campo) en la emisora "Radio Clasica HQ"

`Radio Clasica HQ:634000000:INVERSION_AUTO:BANDWIDTH_8_MHZ:FEC_AUTO:FEC_AUTO:QAM_AUTO:TRANSMISSION_MODE_AUTO:GUARD_INTERVAL_AUTO:HIERARCHY_AUTO:0:2012+2010:40005`

En esta emisora los PID disponibles son 2012 + 2010, veamos como la sintoniza en dos ocasiones:

- En el siguiente caso podría usar ffmpeg o mpg123, eso es configurable, y usa mpg123:
```
NO VIDEO! AUDIO MPA(pid=2010) NO SUBS (yet)!  PROGRAM N. 0
===========================================================
Opening audio decoder: [mpg123] MPEG 1.0/2.0/2.5 layers I, II, III
AUDIO: 48000 Hz, 2 ch, s16le, 192.0 kbit/12.50% (ratio: 24000->192000)
Selected audio codec: [mpg123] afm: mpg123 (MPEG 1.0/2.0/2.5 layers I, II, III)

```

- En el siguiente caso solo es posible usar ffmpeg:

```
NO VIDEO! AUDIO A52(pid=2012) NO SUBS (yet)!  PROGRAM N. 0
===========================================================
Opening audio decoder: [ffmpeg] FFmpeg/libavcodec audio decoders
libavcodec version 56.60.100 (external)
AUDIO: 48000 Hz, 2 ch, floatle, 320.0 kbit/10.42% (ratio: 40000->384000)
Selected audio codec: [ffac3] afm: ffmpeg (FFmpeg AC-3)
```


Una solución es duplicar la emisora en `.mplayer/channels.conf`, con otro nombre significativo, pero dejando un solo PID en cada línea para luego poder seleccionar la emisora usando el PID que queramos:

`Radio Clasica HQ:634000000:INVERSION_AUTO:BANDWIDTH_8_MHZ:FEC_AUTO:FEC_AUTO:QAM_AUTO:TRANSMISSION_MODE_AUTO:GUARD_INTERVAL_AUTO:HIERARCHY_AUTO:0:2010:40005`

`Radio Clasica Dolby:634000000:INVERSION_AUTO:BANDWIDTH_8_MHZ:FEC_AUTO:FEC_AUTO:QAM_AUTO:TRANSMISSION_MODE_AUTO:GUARD_INTERVAL_AUTO:HIERARCHY_AUTO:0:2012:40005`

# 6. Grabar a un archivo

Preparamos un script, ver por ejemplo **`~/bin/peaudiosys_dvb-t_record.sh.sh`**

Y programamos la grabación en nuestro **`crontab`**, por ejemplo:


    # m h  dom mon dow   command
    
    # DAS RHEINGOLD     28-jul  18:00 - 20:35
    40 17   28  7   *     /home/paudio/bin/peaudiosys_dvb-t_record.sh
    55 20   28  7   *     /home/paudio/bin/peaudiosys_dvb-t_record.sh --stop
    ...
    ...


