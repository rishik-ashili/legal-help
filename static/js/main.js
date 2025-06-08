document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chat-container');
    const textInput = document.getElementById('text-input');
    const sendBtn = document.getElementById('send-btn');
    const recordBtn = document.getElementById('record-btn');
    const fillFormBtn = document.getElementById('fill-form-btn');

    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;

    function renderFirForm(firData) {
        let formHtml = '<div class="fir-form-container">';
        formHtml += '<h3>Demonstration First Information Report</h3>';
        
        firData.forEach(item => {
            const valueClass = /[a-zA-Z]/.test(item.value) ? 'english' : '';
            formHtml += `
                <div class="fir-form-item">
                    <span class="label">${item.label}</span>
                    <span class="value ${valueClass}">${item.value}</span>
                </div>
            `;
        });

        formHtml += '</div>';
        return formHtml;
    }

    function addMessage(sender, messageData) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', `${sender}-message`);

        let content = '';
        if (sender === 'user') {
            content = messageData;
        } else { // Bot message
            let englishResponse = messageData.english_response;
            let hindiResponse = messageData.hindi_response;
            
            // --- THIS IS THE NEW PART FOR HANDLING THE FIR FORM ---
            const jsonRegex = /```json\s*([\s\S]*?)\s*```/;
            const jsonMatch = englishResponse.match(jsonRegex);

            if (jsonMatch && jsonMatch[1]) {
                try {
                    const firJson = JSON.parse(jsonMatch[1]);
                    // Render the form and replace the JSON block with it
                    const formHtml = renderFirForm(firJson.fir_data);
                    englishResponse = englishResponse.replace(jsonRegex, formHtml);
                    // Also remove it from the Hindi response to avoid showing raw JSON
                    hindiResponse = hindiResponse.replace(jsonRegex, "");
                } catch (e) {
                    console.error("Failed to parse FIR JSON:", e);
                    // If parsing fails, just display the raw text
                }
            }
            
            // Format markdown and newlines
            englishResponse = englishResponse.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
            hindiResponse = hindiResponse.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');

            // Separate the disclaimer
            const disclaimerRegex = /---<br><strong>Disclaimer:([\s\S]*)/;
            if (englishResponse.match(disclaimerRegex)) {
                const parts = englishResponse.split(disclaimerRegex);
                englishResponse = parts[0] + `<div class="disclaimer"><strong>Disclaimer:</strong>${parts[1]}</div>`;
            }

            content = `<div class="english-text">${englishResponse}</div>`;
            if (hindiResponse) {
                content += `<div class="hindi-text">${hindiResponse}</div>`;
            }
            if (messageData.audio_response) {
                const audioSrc = `data:audio/wav;base64,${messageData.audio_response}`;
                content += `<audio controls src="${audioSrc}"></audio>`;
            }
        }

        messageElement.innerHTML = content;
        chatContainer.appendChild(messageElement);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // --- Loading Indicator (No changes) ---
    function showLoadingIndicator() {
        const loadingElement = document.createElement('div');
        loadingElement.classList.add('message', 'bot-message', 'loading-indicator');
        loadingElement.id = 'loading';
        loadingElement.textContent = 'Thinking';
        chatContainer.appendChild(loadingElement);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function hideLoadingIndicator() {
        const loadingElement = document.getElementById('loading');
        if (loadingElement) {
            loadingElement.remove();
        }
    }
    
    // --- Send data to server (No changes) ---
    async function sendMessageToServer(data) {
        showLoadingIndicator();
        const formData = new FormData();
        if (typeof data === 'string') {
            formData.append('text_input', data);
        } else {
            formData.append('audio_data', data, 'recording.webm');
        }

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                body: formData,
            });
            hideLoadingIndicator();
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const result = await response.json();
            addMessage('bot', result);
        } catch (error)
        {
            hideLoadingIndicator();
            addMessage('bot', { english_response: 'Error: Could not connect to the server.', hindi_response: '' });
            console.error('Error:', error);
        }
    }

    // --- Event Listeners (No changes) ---
    sendBtn.addEventListener('click', () => {
        const text = textInput.value.trim();
        if (text) {
            addMessage('user', text);
            sendMessageToServer(text);
            textInput.value = '';
        }
    });

    textInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendBtn.click();
        }
    });

    fillFormBtn.addEventListener('click', () => {
        const commandText = "Fill FIR Form";
        addMessage('user', commandText);
        sendMessageToServer(commandText);
    });

    recordBtn.addEventListener('click', () => {
        if (!isRecording) {
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
                    mediaRecorder.start();
                    isRecording = true;
                    recordBtn.classList.add('recording');
                    recordBtn.innerHTML = '<i class="fas fa-stop"></i>';
                    audioChunks = [];

                    mediaRecorder.addEventListener('dataavailable', event => {
                        audioChunks.push(event.data);
                    });

                    mediaRecorder.addEventListener('stop', () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                        addMessage('user', '[Voice Message]');
                        sendMessageToServer(audioBlob);
                        stream.getTracks().forEach(track => track.stop());
                    });
                }).catch(err => {
                    console.error("Error accessing microphone:", err);
                    addMessage('bot', { english_response: "Error: Could not access the microphone. Please grant permission.", hindi_response: ""});
                });
        } else {
            mediaRecorder.stop();
            isRecording = false;
            recordBtn.classList.remove('recording');
            recordBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        }
    });

    addMessage('bot', {
        english_response: "Hello! I am Nyay Sahayak, your AI legal advisor. How can I assist you with Indian law today? You can also click 'Fill Form' to start a demonstration of filling an FIR.",
        hindi_response: "नमस्ते! मैं न्याय सहायक हूँ, आपका एआई कानूनी सलाहकार। मैं आज भारतीय कानून के साथ आपकी सहायता कैसे कर सकता हूँ? आप एफआईआर भरने का प्रदर्शन शुरू करने के लिए 'फॉर्म भरें' पर भी क्लिक कर सकते हैं।",
        audio_response: null
    });
});