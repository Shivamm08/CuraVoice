function sendMessage() {
    const userInputElement = document.getElementById('user-input');
    const userInput = userInputElement.value;
    const languageInput = document.getElementById('language-select').value;
    const chatBox = document.getElementById('chat-box');
    const audioPlayer = document.getElementById('audio-player');
    const audioContainer = document.getElementById('audio-container');

    // Add user input to chat box
    if (userInput.trim()) {
        chatBox.innerHTML += `<p><strong>You:</strong> ${userInput}</p>`;
        userInputElement.value = '';  // Clear input field

        // Send message to the server
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt: userInput,
                language: languageInput
            })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.response) {
                chatBox.innerHTML += `<p><strong>Bot:</strong> Failed to connect. Probable cause: ${data.error || 'Unknown'}</p>`;
            } else {
                chatBox.innerHTML += `<p><strong>Bot:</strong> ${data.response}</p>`;
                
                // Load and display audio if available
                if (data.audio) {
                    audioPlayer.src = data.audio;
                    audioPlayer.load();
                    audioContainer.style.display = 'block';  // Show the audio player
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            chatBox.innerHTML += `<p><strong>Bot:</strong> Failed to connect. Probable cause: ${error}</p>`;
        });
    }
}
