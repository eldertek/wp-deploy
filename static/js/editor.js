tinymce.init({
    selector: '#content',
    language: 'fr_FR',
    license_key: 'gpl',
    language_url: languageUrl, // Use the variable defined in the HTML
    setup: function(editor) {
        editor.on('change', function() {
            tinymce.triggerSave();
        });
    }
});

document.getElementById('articleForm').addEventListener('submit', function(event) {
    event.preventDefault();
    tinymce.triggerSave();
    if (document.getElementById('content').value.trim() === '') {
        alert('Le contenu ne peut pas être vide');
        return false;
    }
    var submitButton = document.getElementById('submitButton');
    submitButton.disabled = true;

    var formData = new FormData(document.getElementById('articleForm'));

    $.ajax({
        type: 'POST',
        url: '{{ url_for("editor.editor") }}',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            submitButton.disabled = false;
            // Clear the form fields
            document.getElementById('title').value = '';
            tinymce.get('content').setContent('');
        },
        error: function(error) {
            console.log('Erreur lors de la publication de l\'article');
            var messages = document.getElementById('messages');
            var message = document.createElement('div');
            message.className = 'alert alert-danger mt-4';
            message.innerText = 'Erreur lors de la publication de l\'article';
            messages.insertBefore(message, messages.firstChild);
            submitButton.disabled = false;
        }
    });
});