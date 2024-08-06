$(document).ready(function() {
    var socket = io.connect('https://' + document.domain + ':' + location.port);
    socket.on('message', function(msg) {
        console.log('Received message:', msg);
        var messages = document.getElementById('socket-messages');
        var message = document.createElement('div');
        message.className = 'alert alert-info mt-4';
        message.innerText = msg;
        messages.insertBefore(message, messages.firstChild);
    });

    socket.on('error', function(msg) {
        console.log('Received error:', msg);
        var messages = document.getElementById('socket-messages');
        var message = document.createElement('div');
        message.className = 'alert alert-danger mt-4';
        message.innerText = msg;
        messages.insertBefore(message, messages.firstChild);
    });
});