/*
    Copyright (c) Rafael Sánchez
    This file is part of 'pe.audio.sys'
    'pe.audio.sys', a PC based personal audio system.
*/

const URL_PREFIX = '/php/main.php';
const AUTO_UPDATE_INTERVAL = 1000;

var   PEAKS_SINCE = '';


function init(){

    setInterval( page_update, AUTO_UPDATE_INTERVAL );
}


function page_update(){

    const peak_monitor_running  = JSON.parse( control_cmd('aux peak_monitor_running') );

    if (peak_monitor_running){

        const peaks = JSON.parse( control_cmd('aux get_bf_today_peaks')   );

        document.getElementById("peaks_monitor_state").innerText = 'Convolver peaks monitor is running ...'
        display_peaks(peaks);

    }else{
        document.getElementById("peaks_monitor_state").innerText = '(convolver peaks monitor is NOT running)'
        display_peaks([]);
    }
}


function display_peaks(peaks){

    if (PEAKS_SINCE){
        peaks = peaks.filter( (row) => row.slice(0,8) > PEAKS_SINCE );
    }

    let peaks_str = '';

    for (let file of peaks.reverse()){
        peaks_str += file + '\n';
    }

    document.getElementById("peaks_str").innerText = peaks_str;
}


function omd_clear_old_peaks(){

    let now = new Date();

    // example: '10:11:12'
    PEAKS_SINCE = now.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}


function control_cmd( cmd ) {
    // Communicate with the pe.audio.sys server through the php socket

    /*
    We need synchronous mode (async=false), althougt it is deprecated
    and not recommended in the main JS thread.
    https://developer.mozilla.org/en/docs/Web/API/XMLHttpRequest
    https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest/Using_XMLHttpRequest
    https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest/Synchronous_and_Asynchronous_Requests
    */


    // Encoding special chars in the value of the 'command' parameter
    const url = URL_PREFIX + '?command=' + encodeURIComponent(cmd);

    const myREQ = new XMLHttpRequest();

    // open(method, url, async_mode)
    myREQ.open("GET", url, false);
    // (i) send() is blocking because async=false, so no handlers
    //     on myREQ status changes are needed because of this.
    myREQ.send();
    let ans = myREQ.responseText;

    //console.log('httpTX: ' + cmd);
    //console.log('httpRX: ' + ans);

    if ( ans.indexOf('socket_connect\(\) failed' ) == -1 ){
        server_available = true;
        return ans;
    }else{
        server_available = false;
        return '';
    }
}


