$(document).ready(function() {
    var socket = io.connect('https://' + document.domain + ':' + location.port);
    
    socket.on('message', function(msg) {
        console.log('Received message:', msg);
        var messages = document.getElementById('socket-messages');
        
        // Check if messages element exists
        if (messages) {
            var message = document.createElement('div');
            message.className = 'alert alert-info mt-4';
            message.innerText = msg;
            messages.insertBefore(message, messages.firstChild);
        } else {
            console.error('Element with ID "socket-messages" not found.');
        }
    });

    socket.on('error', function(msg) {
        console.log('Received error:', msg);
        var messages = document.getElementById('socket-messages');
        
        // Check if messages element exists
        if (messages) {
            var message = document.createElement('div');
            message.className = 'alert alert-danger mt-4';
            message.innerText = msg;
            messages.insertBefore(message, messages.firstChild);
        } else {
            console.error('Element with ID "socket-messages" not found.');
        }
    });
    
    // Added error handling for socket connection
    socket.on('connect_error', function(err) {
        console.error('Socket connection error:', err);
        addMessage('Erreur de connexion au serveur.', 'danger'); // Display error message
    });
});