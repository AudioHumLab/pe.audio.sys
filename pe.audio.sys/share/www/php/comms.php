<?php

    /*
    Copyright (c) Rafael Sánchez
    This file is part of 'pe.audio.sys'
    'pe.audio.sys', a PC based personal audio system.
    */

    /*  This is the hidden server side php code.
        PHP will response to the client via the standard php output, for instance:
            echo $some_varible;
            echo "some_string";
            readfile("some_file_path");
    */

    $UHOME = get_home();
    //echo '---'.$HOME.'---'; // cmdline debugging

    // Gets the base folder where php code and pe.audio.sys are located
    function get_home() {
        $phpdir = getcwd();
        $pos = strpos($phpdir, 'pe.audio.sys');
        return substr($phpdir, 0, $pos-1 );
    }

    // Gets single line configured items from pe.audio.sys 'config.yml' file
    function get_config($item) {
        // to have access to variables from outside
        global $UHOME;

        $tmp = "";
        $cfile = fopen( $UHOME."/pe.audio.sys/config/config.yml", "r" )
                  or die("Unable to open file!");
        while( !feof($cfile) ) {
            $line = fgets($cfile);
            // Ignore yaml commented out lines
            if ( strpos($line, '#') === false ) {
                if ( strpos( $line, $item) !== false ) {
                    $tmp = str_replace( "\n", "", $line);
                    $tmp = str_replace( $item, "", $tmp);
                    $tmp = str_replace( ":", "", $tmp);
                    $tmp = trim($tmp);
                }
            }
        }
        fclose($cfile);
        return $tmp;
    }


    // Communicates with the "peaudiosys" TCP server.
    function send_cmd($cmd, $service='peaudiosys') {

        $address =         get_config( "peaudiosys_address" );
        $port    = intval( get_config( "peaudiosys_port"    ) );

        if ($service === 'restart'){
            $port = $port + 1;
        }

        $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
        if ($socket === false) {
            echo "socket_create() failed: " . socket_strerror(socket_last_error()) . "\n";
        }
        $result = socket_connect($socket, $address, $port);
        if ($result === false) {
            echo "socket_connect() failed: ($result) " . socket_strerror(socket_last_error($socket)) . "\n";
        }
        socket_write($socket, $cmd, strlen($cmd));
        $ans = '';
        while ( ($tmp = socket_read($socket, 1000)) !== '') {
           $ans = $ans.$tmp;
        }
        socket_close($socket);

        return $ans;
    }

?>