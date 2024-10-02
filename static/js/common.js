$(document).ready(function() {
    var socket = io.connect('https://' + document.domain + ':' + location.port);
    
    socket.on('message', function(msg) {
        // console.log('Received message:', msg);
        var messages = document.getElementById('socket-messages');
        
        // Check if messages element exists
        if (messages) {
            var message = document.createElement('div');
            message.className = 'alert alert-info mt-4';
            message.innerText = msg;

            // Create close button
            var closeButton = document.createElement('button');
            closeButton.className = 'close';
            closeButton.innerHTML = '&times;';
            closeButton.onclick = function() {
                messages.removeChild(message);
            };
            message.appendChild(closeButton); // Add close button to message

            messages.insertBefore(message, messages.firstChild);
            
            // Ajout d'une animation de fondu
            setTimeout(function() {
                message.style.transition = 'opacity 1s';
                message.style.opacity = 0;
                setTimeout(function() {
                    messages.removeChild(message);
                }, 1000); // Retirer après la transition
            }, 180000); // Attendre 3 minutes avant de commencer le fondu
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

            // Create close button
            var closeButton = document.createElement('button');
            closeButton.className = 'close';
            closeButton.innerHTML = '&times;';
            closeButton.onclick = function() {
                messages.removeChild(message);
            };
            message.appendChild(closeButton); // Add close button to error message

            messages.insertBefore(message, messages.firstChild);
            
            // Ajout d'une animation de fondu
            setTimeout(function() {
                message.style.transition = 'opacity 1s';
                message.style.opacity = 0;
                setTimeout(function() {
                    messages.removeChild(message);
                }, 1000); // Retirer après la transition
            }, 180000); // Attendre 3 minutes avant de commencer le fondu
        } else {
            console.error('Element with ID "socket-messages" not found.');
        }
    });

    socket.on('console', function(msg) {
        console.log('Received console:', msg);
    });

    socket.on('success', function(msg) {
        console.log('Received success:', msg);
        var messages = document.getElementById('socket-messages');
        
        // Check if messages element exists
        if (messages) {
            var message = document.createElement('div');
            message.className = 'alert alert-success mt-4';
            message.innerText = msg;

            // Create close button
            var closeButton = document.createElement('button');
            closeButton.className = 'close';
            closeButton.innerHTML = '&times;';
            closeButton.onclick = function() {
                messages.removeChild(message);
            };
            message.appendChild(closeButton); // Add close button to success message

            messages.insertBefore(message, messages.firstChild);
            
            // Ajout d'une animation de fondu
            setTimeout(function() {
                message.style.transition = 'opacity 1s';
                message.style.opacity = 0;
                setTimeout(function() {
                    messages.removeChild(message);
                }, 1000); // Retirer après la transition
            }, 180000); // Attendre 3 minutes avant de commencer le fondu
        } else {
            console.error('Element with ID "socket-messages" not found.');
        }
    });
});

function showLoadingSpinner() {
    $('#loadingSpinner').show();
    $('#deploymentsTableContainer').hide();
}

function hideLoadingSpinner() {
    $('#loadingSpinner').hide();
    $('#deploymentsTableContainer').show();
}

function deleteLogs(url) {
    showLoadingSpinner();
    $.ajax({
        url: url,
        type: 'POST',
        success: function(response) {
            location.reload();
        },
        error: function(xhr, status, error) {
            alert('Erreur lors de la suppression des logs: ' + error);
            hideLoadingSpinner();
        }
    });
}
