# SparzaFI Chat System Design

## Overview
Three types of chats for different user interactions:
1. **Buyer ↔ Seller Chat** - General product inquiries
2. **Buyer ↔ Deliverer Chat** - Order tracking and delivery coordination
3. **Seller ↔ Deliverer Chat** - Pickup coordination

## Firebase Collections

### conversations
```
{
  id: "uuid",
  chat_type: "buyer_seller" | "buyer_deliverer" | "seller_deliverer",
  transaction_id: "uuid" (optional - null for buyer_seller, required for order chats),
  seller_id: "uuid" (optional - for buyer_seller and seller_deliverer),
  buyer_id: "uuid" (optional - for buyer_seller and buyer_deliverer),
  deliverer_id: "uuid" (optional - for buyer_deliverer and seller_deliverer),
  user1_id: "uuid" (backward compatibility),
  user2_id: "uuid" (backward compatibility),
  last_message_at: timestamp,
  last_message: "text preview",
  created_at: timestamp
}
```

### messages
```
{
  id: "uuid",
  conversation_id: "uuid",
  transaction_id: "uuid" (optional),
  sender_id: "uuid",
  recipient_id: "uuid",
  message_text: "string",
  is_read: boolean,
  read_at: timestamp (optional),
  created_at: timestamp,
  sender_role: "buyer" | "seller" | "deliverer"
}
```

## API Endpoints

### POST /chat/send
Send a message (supports all 3 chat types)
```json
{
  "recipient_id": "uuid",
  "message": "text",
  "transaction_id": "uuid" (optional),
  "chat_type": "buyer_seller | buyer_deliverer | seller_deliverer"
}
```

### GET /chat/history/<conversation_id>
Get messages for a conversation

### GET /chat/transaction/<transaction_id>
Get chat for a specific transaction (order-specific chats)

### POST /chat/mark_read
Mark messages as read
```json
{
  "conversation_id": "uuid"
}
```

### GET /chat/unread-count
Get unread message count for current user

## Security Rules

1. **KYC Verification Required**
   - Sellers must be KYC verified to reply
   - Deliverers must be verified to access chat
   - Buyers can always send messages

2. **Message Content Filtering**
   - Block phone numbers (patterns: +27, 0, digits)
   - Block email addresses (pattern: @)
   - Block URLs (pattern: http, www)

3. **Role-Based Access**
   - Only transaction participants can access order chats
   - Admin can view all chats for disputes

## UI Components

### Chat Window Structure
- WhatsApp/Telegram style bubbles
- Sender messages: right-aligned, blue background
- Recipient messages: left-aligned, gray background
- Timestamps for each message
- "Seen" indicator (blue tick)
- Auto-scroll to bottom
- AJAX polling every 3 seconds

### Chat Locations

1. **Buyer ↔ Seller Chat**
   - Location: Seller shop page (/seller/<handle>)
   - Floating window button (bottom right)
   - Opens modal with chat interface

2. **Buyer ↔ Deliverer Chat**
   - Location: Order tracking page (/order/<transaction_id>)
   - Embedded chat section below tracking info
   - Shows deliverer name and photo

3. **Seller ↔ Deliverer Chat**
   - Location: Deliverer dashboard Active Deliveries
   - Chat button for each active pickup/delivery
   - Shows seller name and order ID

## Implementation Files

- `/chat/routes.py` - Enhanced API endpoints
- `/chat/message_filter.py` - Phone/email blocking utility
- `/firebase_db.py` - Enhanced ConversationService and MessageService
- `/chat/templates/chat_widget.html` - Reusable chat UI component
- `/static/js/chat.js` - AJAX polling and message handling

## Testing Plan

### Round 1: Buyer ↔ Seller Chat
- Buyer can start chat from seller shop page
- Messages send successfully
- KYC check blocks unverified seller replies
- Message filtering blocks phone/email

### Round 2: Buyer ↔ Deliverer Chat
- Chat appears on order tracking page
- Linked to transaction_id
- Deliverer can see chat in dashboard
- Real-time updates via AJAX polling

### Round 3: Seller ↔ Deliverer Chat
- Chat appears for pickup coordination
- Both parties can send/receive messages
- Messages filtered for security
- Admin can view chat logs
