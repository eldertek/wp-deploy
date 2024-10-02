$(document).on('click', '.force-update-btn', function() {
    var domain = $(this).data('domain');
    // Clear all current messages
    $('#socket-messages').empty();
    $.ajax({
        type: 'POST',
        url: deploySiteUrl,
        data: JSON.stringify({domain: domain}),
        contentType: 'application/json',
        success: function(response) {
            console.log('Force update initiated for domain:', domain);
            // Display success message
            var message = $('<div class="alert alert-success mt-4">Mise à jour réussie pour le domaine: ' + domain + '</div>');
            $('#socket-messages').append(message);
            setTimeout(function() {
                message.fadeOut(1000, function() {
                    $(this).remove();
                });
            }, 5000);
        },
        error: function(error) {
            console.log('Error initiating force update for domain:', domain);
            // Display error message
            var message = $('<div class="alert alert-danger mt-4">Erreur lors de la mise à jour pour le domaine: ' + domain + '</div>');
            $('#socket-messages').append(message);
            setTimeout(function() {
                message.fadeOut(1000, function() {
                    $(this).remove();
                });
            }, 5000);
        }
    });
});
