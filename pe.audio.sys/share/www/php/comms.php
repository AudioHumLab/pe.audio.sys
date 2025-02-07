<?php

    /*
    Copyright (c) Rafael Sánchez
    This file is part of 'pe.audio.sys'
    'pe.audio.sys', a PC based personal audio system.
    */

    /* (i) needs php-yaml (available as a Debian APT package */

    $UHOME = get_home();
    // echo "UHOME: ".$UHOME."\n"; // cmdline debugging

    // Gets the base folder where php code and pe.audio.sys are located
    function get_home() {
        $phpdir = getcwd();
        $pos = strpos($phpdir, 'pe.audio.sys');
        $uhome= substr($phpdir, 0, $pos-1);
        return $uhome;
    }


    // Reads an item's value from pe.audio.sys 'config.yml' file
    function get_config($item) {

        global $UHOME;

        $config_path =  $UHOME."/pe.audio.sys/config/config.yml";

        $config = yaml_parse_file($config_path);

        return $config[$item];
    }


    // Communicates with the "peaudiosys" TCP server.
    function send_cmd($cmd, $service='peaudiosys') {

        $address =         get_config( "peaudiosys_address" );
        $port    = intval( get_config( "peaudiosys_port"    ) );

        if ($service === 'peaudiosys_ctrl'){
            $port = $port + 1;
        }

        $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
        if ($socket === false) {
            echo "(comms.php) socket_create() failed: " . socket_strerror(socket_last_error()) . "\n";
            return '';
        }

        socket_set_option($socket, SOL_SOCKET, SO_RCVTIMEO, array("sec"=>0, "usec"=>500));
        socket_set_option($socket, SOL_SOCKET, SO_SNDTIMEO, array("sec"=>0, "usec"=>500));

        $so_result = socket_connect($socket, $address, $port);
        if ($so_result === false) {
            echo "(comms.php) socket_connect() failed: ($so_result) " . socket_strerror(socket_last_error($socket)) . "\n";
            return '';
        }

        // PHP ---> App server side
        socket_write($socket, $cmd, strlen($cmd));

        // App server side ---> PHP
        $ans = '';
        while ( ($tmp = socket_read($socket, 1000)) !== '') {
           $ans = $ans.$tmp;
        }
        socket_close($socket);

        return $ans;

    }

?>
