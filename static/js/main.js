/**
 * SparzaFI Chat Functionality
 * Real-time messaging between users
 */

// Chat state
let chatState = {
    currentConversationId: null,
    currentRecipientId: null,
    currentRecipientEmail: null,
    pollingInterval: null,
    unreadInterval: null
};

document.addEventListener('DOMContentLoaded', function() {
    // Only initialize chat if user is logged in
    const openChatBtn = document.getElementById('open-chat-btn');
    if (!openChatBtn) return;

    // Elements
    const chatModal = document.getElementById('chat-modal');
    const closeChatBtn = document.getElementById('close-chat');
    const conversationsList = document.getElementById('chat-conversations-list');
    const messagesView = document.getElementById('chat-messages-view');
    const messagesContainer = document.getElementById('chat-messages-container');
    const messageInput = document.getElementById('chat-message-input');
    const sendBtn = document.getElementById('send-message-btn');
    const backBtn = document.getElementById('back-to-conversations');
    const chatTitle = document.getElementById('chat-title');
    const inputContainer = document.getElementById('chat-input-container');

    // Event Listeners
    openChatBtn.addEventListener('click', openChat);
    closeChatBtn.addEventListener('click', closeChat);
    sendBtn.addEventListener('click', sendMessage);
    backBtn.addEventListener('click', backToConversations);

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Start polling for unread count
    startUnreadPolling();

    // Core Functions
    function openChat() {
        chatModal.style.display = 'flex';
        loadConversations();
    }

    function closeChat() {
        chatModal.style.display = 'none';
        stopPolling();
        backToConversations();
    }

    function backToConversations() {
        conversationsList.style.display = 'block';
        messagesView.style.display = 'none';
        inputContainer.style.display = 'none';
        backBtn.style.display = 'none';
        chatTitle.textContent = 'Messages';
        chatState.currentConversationId = null;
        chatState.currentRecipientId = null;
        chatState.currentRecipientEmail = null;
        stopPolling();
    }

    async function loadConversations() {
        conversationsList.innerHTML = '<div class="chat-loading">Loading conversations...</div>';

        try {
            const response = await fetch('/chat/conversations');
            if (!response.ok) throw new Error('Failed to load conversations');

            const conversations = await response.json();

            if (conversations.length === 0) {
                conversationsList.innerHTML = '<div class="chat-empty">No conversations yet. Start chatting with sellers!</div>';
                return;
            }

            conversationsList.innerHTML = '';
            conversations.forEach(conv => {
                const convElement = document.createElement('div');
                convElement.className = 'chat-conversation-item';

                const timeStr = conv.last_message_at
                    ? formatTimestamp(conv.last_message_at)
                    : formatTimestamp(conv.created_at);

                convElement.innerHTML = `
                    <div class="chat-conversation-email">${conv.other_user_email}</div>
                    <div class="chat-conversation-time">${timeStr}</div>
                `;

                convElement.onclick = () => openConversation(conv.id, conv.other_user_id, conv.other_user_email);
                conversationsList.appendChild(convElement);
            });
        } catch (error) {
            console.error('Error loading conversations:', error);
            conversationsList.innerHTML = '<div class="chat-empty">Error loading conversations. Please try again.</div>';
        }
    }

    async function openConversation(conversationId, recipientId, recipientEmail) {
        chatState.currentConversationId = conversationId;
        chatState.currentRecipientId = recipientId;
        chatState.currentRecipientEmail = recipientEmail;

        conversationsList.style.display = 'none';
        messagesView.style.display = 'flex';
        inputContainer.style.display = 'flex';
        backBtn.style.display = 'block';
        chatTitle.textContent = recipientEmail;

        await loadMessages();

        // Start polling for new messages
        stopPolling();
        chatState.pollingInterval = setInterval(loadMessages, 3000);
    }

    async function loadMessages() {
        if (!chatState.currentConversationId) return;

        try {
            const response = await fetch(`/chat/conversations/${chatState.currentConversationId}/messages`);
            if (!response.ok) throw new Error('Failed to load messages');

            const messages = await response.json();

            messagesContainer.innerHTML = '';
            messages.forEach(msg => {
                const msgElement = document.createElement('div');
                const isSent = msg.sender_email === getCurrentUserEmail();
                msgElement.className = `chat-message ${isSent ? 'chat-message-sent' : 'chat-message-received'}`;

                msgElement.innerHTML = `
                    ${!isSent ? `<div class="chat-message-sender">${msg.sender_email}</div>` : ''}
                    <div class="chat-message-content">${escapeHtml(msg.content)}</div>
                    <div class="chat-message-time">${formatTimestamp(msg.timestamp)}</div>
                `;

                messagesContainer.appendChild(msgElement);
            });

            // Scroll to bottom
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            // Update unread count
            updateUnreadCount();
        } catch (error) {
            console.error('Error loading messages:', error);
        }
    }

    async function sendMessage() {
        const content = messageInput.value.trim();
        if (!content || !chatState.currentRecipientId) return;

        sendBtn.disabled = true;

        try {
            const response = await fetch('/chat/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recipient_id: chatState.currentRecipientId,
                    content: content
                })
            });

            if (!response.ok) throw new Error('Failed to send message');

            const data = await response.json();

            // If this was a new conversation, update the state
            if (!chatState.currentConversationId) {
                chatState.currentConversationId = data.conversation_id;
            }

            messageInput.value = '';
            await loadMessages();
        } catch (error) {
            console.error('Error sending message:', error);
            alert('Failed to send message. Please try again.');
        } finally {
            sendBtn.disabled = false;
            messageInput.focus();
        }
    }

    function stopPolling() {
        if (chatState.pollingInterval) {
            clearInterval(chatState.pollingInterval);
            chatState.pollingInterval = null;
        }
    }

    async function updateUnreadCount() {
        try {
            const response = await fetch('/chat/unread-count');
            if (!response.ok) return;

            const data = await response.json();
            const badge = document.getElementById('chat-unread-badge');

            if (data.unread_count > 0) {
                badge.textContent = data.unread_count > 99 ? '99+' : data.unread_count;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        } catch (error) {
            console.error('Error updating unread count:', error);
        }
    }

    function startUnreadPolling() {
        updateUnreadCount();
        chatState.unreadInterval = setInterval(updateUnreadCount, 10000); // Every 10 seconds
    }

    // Utility Functions
    function formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        return date.toLocaleDateString();
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function getCurrentUserEmail() {
        // This is a placeholder - in production, this should come from the session
        const userEmailElement = document.querySelector('.dropdown-header strong + p');
        if (userEmailElement) {
            const emailText = userEmailElement.textContent;
            const match = emailText.match(/User:\s*(.+)/);
            if (match) return match[1].trim();
        }
        return '';
    }
});

/**
 * Global function to start a chat with a specific user
 * Can be called from anywhere in the app (e.g., seller profile page)
 * @param {number} recipientId - The ID of the user to chat with
 * @param {string} recipientEmail - The email of the user to chat with
 */
window.startChatWith = async function(recipientId, recipientEmail) {
    if (!recipientId || !recipientEmail) {
        console.error('Recipient ID and email are required');
        return;
    }

    // Open the chat modal
    const chatModal = document.getElementById('chat-modal');
    const openChatBtn = document.getElementById('open-chat-btn');

    if (!chatModal || !openChatBtn) {
        console.error('Chat components not found');
        return;
    }

    chatModal.style.display = 'flex';

    // Try to find existing conversation
    try {
        const response = await fetch('/chat/conversations');
        if (response.ok) {
            const conversations = await response.json();
            const existingConv = conversations.find(c => c.other_user_id === recipientId);

            if (existingConv) {
                // Open existing conversation
                const event = new CustomEvent('openConversation', {
                    detail: {
                        conversationId: existingConv.id,
                        recipientId: recipientId,
                        recipientEmail: recipientEmail
                    }
                });
                document.dispatchEvent(event);
            } else {
                // Create new conversation by showing input directly
                chatState.currentConversationId = null;
                chatState.currentRecipientId = recipientId;
                chatState.currentRecipientEmail = recipientEmail;

                const conversationsList = document.getElementById('chat-conversations-list');
                const messagesView = document.getElementById('chat-messages-view');
                const messagesContainer = document.getElementById('chat-messages-container');
                const inputContainer = document.getElementById('chat-input-container');
                const backBtn = document.getElementById('back-to-conversations');
                const chatTitle = document.getElementById('chat-title');

                conversationsList.style.display = 'none';
                messagesView.style.display = 'flex';
                inputContainer.style.display = 'flex';
                backBtn.style.display = 'block';
                chatTitle.textContent = recipientEmail;
                messagesContainer.innerHTML = '<div class="chat-empty">Start a conversation with ' + recipientEmail + '</div>';

                document.getElementById('chat-message-input').focus();
            }
        }
    } catch (error) {
        console.error('Error starting chat:', error);
        alert('Failed to start chat. Please try again.');
    }
};

// Listen for custom event to open conversation
document.addEventListener('openConversation', function(e) {
    const { conversationId, recipientId, recipientEmail } = e.detail;

    chatState.currentConversationId = conversationId;
    chatState.currentRecipientId = recipientId;
    chatState.currentRecipientEmail = recipientEmail;

    const conversationsList = document.getElementById('chat-conversations-list');
    const messagesView = document.getElementById('chat-messages-view');
    const inputContainer = document.getElementById('chat-input-container');
    const backBtn = document.getElementById('back-to-conversations');
    const chatTitle = document.getElementById('chat-title');

    conversationsList.style.display = 'none';
    messagesView.style.display = 'flex';
    inputContainer.style.display = 'flex';
    backBtn.style.display = 'block';
    chatTitle.textContent = recipientEmail;

    // Load messages
    (async function() {
        const messagesContainer = document.getElementById('chat-messages-container');
        try {
            const response = await fetch(`/chat/conversations/${conversationId}/messages`);
            if (!response.ok) throw new Error('Failed to load messages');

            const messages = await response.json();

            messagesContainer.innerHTML = '';
            messages.forEach(msg => {
                const msgElement = document.createElement('div');
                const currentUserEmail = getCurrentUserEmail();
                const isSent = msg.sender_email === currentUserEmail;
                msgElement.className = `chat-message ${isSent ? 'chat-message-sent' : 'chat-message-received'}`;

                msgElement.innerHTML = `
                    ${!isSent ? `<div class="chat-message-sender">${msg.sender_email}</div>` : ''}
                    <div class="chat-message-content">${escapeHtml(msg.content)}</div>
                    <div class="chat-message-time">${formatTimestamp(msg.timestamp)}</div>
                `;

                messagesContainer.appendChild(msgElement);
            });

            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } catch (error) {
            console.error('Error loading messages:', error);
        }
    })();

    // Helper functions (duplicated for scope)
    function formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        return date.toLocaleDateString();
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function getCurrentUserEmail() {
        const userEmailElement = document.querySelector('.dropdown-header strong + p');
        if (userEmailElement) {
            const emailText = userEmailElement.textContent;
            const match = emailText.match(/User:\s*(.+)/);
            if (match) return match[1].trim();
        }
        return '';
    }
});
