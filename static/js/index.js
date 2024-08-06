$(document).on('click', '.force-update-btn', function() {
    var domain = $(this).data('domain');
    // Clear all current messages
    $('#socket-messages').empty();
    $.ajax({
        type: 'POST',
        url: '{{ url_for("deployment.deploy_site") }}',
        data: JSON.stringify({domain: domain}),
        contentType: 'application/json',
        success: function(response) {
            console.log('Force update initiated for domain:', domain);
        },
        error: function(error) {
            console.log('Error initiating force update for domain:', domain);
        }
    });
});