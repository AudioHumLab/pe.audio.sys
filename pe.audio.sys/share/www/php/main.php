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

    include 'comms.php';


    ///////////////////////////   MAIN: ///////////////////////////////
    // listen to http request then returns results via standard output

    /*  http://php.net/manual/en/reserved.variables.request.php
        PHP server side receives associative arrays, i.e. dictionaries, through by the
        GET o PUT methods from the client side XMLHttpRequest (usually javascript).
        The array is what appears after 'functions.php?.......', examples:

            "GET", "main.php?command=level -15"
            "GET", "main.php?command=aux amp_switch on"
            "GET", "main.php?command=player stop"
    */

    //echo send_cmd('state', 'peaudiosys'); // DEBUG

    // HTTPRequest ---> PHP
    $command = $_REQUEST["command"];

    // PHP ---> App server side
    if ( strpos($command, "restart_")===0 or strpos($command, "amp_")===0 ) {

        echo send_cmd($command, 'peaudiosys_ctrl');

    } else {

        echo send_cmd($command, 'peaudiosys');

    }
?>
