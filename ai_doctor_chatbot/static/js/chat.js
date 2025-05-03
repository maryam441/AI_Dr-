document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');

    if (chatForm) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const message = chatInput.value.trim();
            
            if (message) {
                // Add user message to chat
                addMessage(message, 'user');
                
                // Clear input
                chatInput.value = '';
                
                // Scroll to bottom
                scrollToBottom();
                
                // Simulate AI response (in a real app, this would be an AJAX call)
                setTimeout(() => {
                    addMessage("I'm processing your request...", 'ai');
                    scrollToBottom();
                }, 1000);
            }
        });
    }

    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender + '-message');
        
        const messageText = document.createElement('div');
        messageText.textContent = text;
        
        const messageTime = document.createElement('div');
        messageTime.classList.add('message-time');
        messageTime.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        messageDiv.appendChild(messageText);
        messageDiv.appendChild(messageTime);
        
        chatMessages.appendChild(messageDiv);
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Load any existing chat history
    if (chatMessages && chatMessages.dataset.history) {
        try {
            const history = JSON.parse(chatMessages.dataset.history);
            history.forEach(msg => {
                addMessage(msg.message || msg.response, msg.is_user_message ? 'user' : 'ai');
            });
            scrollToBottom();
        } catch (e) {
            console.error('Error loading chat history:', e);
        }
    }
});