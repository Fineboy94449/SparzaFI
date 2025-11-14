# Chat Feature Documentation

## Overview
A complete real-time messaging system has been added to SparzaFI, allowing users to communicate directly with sellers and other users.

## Features Implemented

### 1. Backend API Endpoints
Located in `chat/routes.py`:

- **GET `/chat/conversations`** - Get all conversations for the current user
- **GET `/chat/conversations/<id>/messages`** - Get all messages in a specific conversation
- **POST `/chat/messages`** - Send a new message (creates conversation if needed)
- **GET `/chat/unread-count`** - Get count of unread messages for current user

### 2. Database Schema
The existing database schema already includes the necessary tables:

- **`conversations`** - Stores one-on-one conversations between users
  - `user1_id`, `user2_id` - The two participants (always stored with lower ID first)
  - `last_message_at` - Timestamp of the last message

- **`messages`** - Stores individual messages
  - `conversation_id` - Links to the conversation
  - `sender_id`, `recipient_id` - Message participants
  - `message_text` - The message content
  - `is_read`, `read_at` - Read status tracking

- **`notifications`** - Automatic notifications for new messages

### 3. User Interface
Located in `shared/templates/chat_component.html`:

- **Floating chat button** - Fixed bottom-right corner with unread badge
- **Chat modal** - Slide-up modal with conversations list and message view
- **Conversations list** - Shows all active conversations
- **Message view** - Real-time message display with auto-scroll
- **Input controls** - Send messages with Enter key or button

### 4. JavaScript Functionality
Located in `static/js/main.js`:

- **Auto-polling** - Checks for new messages every 3 seconds when conversation is open
- **Unread count** - Updates every 10 seconds in the background
- **Message formatting** - Automatic timestamp formatting and HTML escaping
- **Global function** - `startChatWith(userId, userEmail)` can be called from anywhere

## How to Use

### For Users
1. **Start a conversation:**
   - Visit a seller's profile page
   - Click the "💬 Contact Seller" button
   - Type and send your message

2. **View conversations:**
   - Click the chat button (💬) in the bottom-right corner
   - See all your active conversations
   - Click on a conversation to view messages

3. **Send messages:**
   - Type in the input field
   - Press Enter or click "Send"
   - Messages appear instantly

### For Developers

#### Start a chat from JavaScript:
```javascript
// Start a chat with a specific user
startChatWith(userId, userEmail);
```

#### Add chat button to any page:
```html
{% if session.get('user') and session.user.get('id') != other_user_id %}
<button onclick="startChatWith({{ other_user_id }}, '{{ other_user_email }}')"
        class="btn btn-outline">
    💬 Contact User
</button>
{% endif %}
```

#### API Usage:
```javascript
// Get conversations
const response = await fetch('/chat/conversations');
const conversations = await response.json();

// Send a message
const response = await fetch('/chat/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        recipient_id: userId,
        content: messageText
    })
});
```

## Security Features

1. **Authentication required** - All endpoints require user login
2. **Authorization checks** - Users can only view their own conversations
3. **HTML escaping** - Messages are escaped to prevent XSS attacks
4. **SQL injection protection** - Parameterized queries throughout

## Styling

The chat interface automatically adapts to your theme (light/dark mode):
- Uses CSS variables from `base.html`
- Responsive design for mobile devices
- Smooth animations and transitions
- Unread message badge with notification count

## Testing

To test the chat feature:

1. **Start the application:**
   ```bash
   python3 app.py
   ```

2. **Login as two different users:**
   - User 1: buyer1@test.com / buyerpass
   - User 2: thandi@sparzafi.com / sellerpass

3. **Send messages:**
   - As User 1, visit a seller's page
   - Click "Contact Seller"
   - Send a message
   - Login as User 2 to see the message

## File Structure

```
SparzaFI/
├── chat/
│   ├── __init__.py          # Blueprint initialization
│   └── routes.py            # API endpoints and logic
├── shared/templates/
│   ├── base.html            # Updated to include chat component
│   └── chat_component.html  # Chat UI component
├── seller/templates/
│   └── seller_detail.html   # Updated with contact button
├── static/js/
│   └── main.js              # Chat JavaScript functionality
└── app.py                   # Updated to register chat blueprint
```

## Future Enhancements

Potential improvements for the chat system:

1. **WebSocket support** - Real-time updates without polling (using Flask-SocketIO)
2. **File attachments** - Share images and documents
3. **Read receipts** - Show when messages are seen
4. **Typing indicators** - Show when other user is typing
5. **Message search** - Search through conversation history
6. **Message deletion** - Delete or edit sent messages
7. **Emoji picker** - Built-in emoji selector
8. **Group chats** - Support for multi-user conversations
9. **Push notifications** - Browser notifications for new messages
10. **Message pagination** - Load older messages on scroll

## Troubleshooting

### Chat button not appearing:
- Ensure you're logged in
- Check browser console for JavaScript errors
- Verify `main.js` is loading correctly

### Messages not sending:
- Check network tab for API errors
- Verify authentication is working
- Check server logs for backend errors

### Real-time updates not working:
- Polling is set to 3 seconds - check network requests
- Verify `/chat/unread-count` endpoint is accessible
- Check JavaScript console for errors

## Support

For issues or questions about the chat feature, check:
1. Browser console for JavaScript errors
2. Server logs for backend errors
3. Network tab for API request/response details

## Credits

Chat feature implemented following Flask best practices:
- Blueprint architecture for modularity
- Session-based authentication
- SQLite with parameterized queries
- Responsive CSS with theme support
- Progressive enhancement for JavaScript
