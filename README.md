# 🧩 SparzaFI Platform

> **Formerly known as Bizzy Street** - Now rebranded as SparzaFI

SparzaFI is a comprehensive Flask-based marketplace platform that combines e-commerce, community delivery, and fintech features to empower local traders, community deliverers, and buyers through verified commerce, fair trade, and local economic inclusion.

## 🚀 Quick Start

### Running the Application

**Option 1: Flask CLI (Recommended)** ⭐
```bash
cd /home/fineboy94449/Documents/SparzaFI
source .venv/bin/activate
flask run
```

**Option 2: Quick Start Script**
```bash
cd /home/fineboy94449/Documents/SparzaFI
./scripts/run.sh
```

**Option 3: Direct Python**
```bash
cd /home/fineboy94449/Documents/SparzaFI
source .venv/bin/activate
python3 app.py
```

**Access:** http://localhost:5000

---

### Virtual Environment
```bash
source /home/fineboy94449/Documents/SparzaFI/.venv/bin/activate
```

---

## ⚙️ Core Structure

- **Framework**: Flask with Firebase Firestore database and Jinja templates
- **Database**: Firebase Firestore (Cloud NoSQL database)
- **Environment Variables**:
  - `SECRET_KEY` - Session security
  - `GOOGLE_MAPS_API_KEY` - Delivery and live tracking features
  - `FIREBASE_SERVICE_ACCOUNT` - Firebase service account credentials

---

## 🏪 Marketplace System

### Sellers Can:
- Upload profile information (name, bio, location)
- Add up to 3 videos showcasing their products or services
- Create a product catalog with price, description, and images

### Buyers Can:
- View sellers and their product catalogs
- Add items to cart
- Checkout and place orders securely

---

## 🚚 Community Delivery System

### Delivery Status Flow
```
PENDING → CONFIRMED → READY_FOR_PICKUP → PICKED_UP → IN_TRANSIT → DELIVERED → COMPLETED
```

### Deliverers
- Verified through ID, route, and transport method (motorcycle, bicycle, or walking)
- Confirm pickups and deliveries using digital verification codes
- Operate within the community delivery model, often leveraging public transport routes

### Auto-Tracking
- Each transaction creates a `delivery_tracking` record
- Both pickup and delivery verification codes are digitally generated and confirmed

---

## 💸 Fintech System (Sparza Token - SPZ)

### Sparza Token (SPZ)
A simulated digital currency for internal transactions.

- **Initial Balance**: Each new user starts with 1,000–2,000 SPZ
- **Exchange Rate**: 1 SPZ = R1.00 (mock rate)

### Key Features:
- Deposit / Withdraw / Transfer SPZ between users
- Transaction history tracking in `token_transactions` and `token_balances_history`
- API endpoints under `/api/fintech/...`
- Fintech Dashboard for balance viewing, transaction logs, and transfers

---

## 👩🏾‍💼 User Roles

| Role | Permissions |
|------|------------|
| **Admin** | Full control over moderation, verification, analytics, and compliance |
| **Seller** | Manage listings, confirm orders, view sales and earnings |
| **Deliverer** | Manage community deliveries and verify pickup/delivery codes |
| **Buyer** | Browse marketplace, purchase items, and track orders |

---

## 📊 Admin Tools

- Manage verifications, moderation, and user audit logs
- Admin dashboard with system statistics (sellers, transactions, revenue)
- Role-based access control for enhanced security
- Content moderation and compliance management

---

## 🧠 Security and Logic

- **Password Security**: SHA256 + salt hashing
- **KYC Verification**: Required for sellers and deliverers
- **Authentication**: Secure session-based with decorators (`@login_required`, `@seller_required`, etc.)
- **Authorization**: Strong logic layer to prevent unauthorized actions

---

## ⚙️ Main Features

✅ Marketplace feed with verified sellers and products
✅ Order placement, delivery, and confirmation system
✅ Simulated fintech ecosystem using Sparza Token (SPZ)
✅ Token transfers and transaction explorer
✅ Admin, seller, buyer, and deliverer dashboards
✅ Auto-seeding for demo users and sample data

---

## 🧍‍♂️ User Features

### 1. Seller Verification Dashboard
- Upload ID and proof of address for verification
- Admin reviews and approves submissions
- Approved sellers get a ✅ **Verified Seller** badge

### 2. Wallet-to-Cash Gateway
- Convert Sparza Token (SPZ) to Rand value for withdrawals
- Mock exchange rate: 1 SPZ = R1.00
- Simulated "Withdraw to Bank" option with pending status

### 3. Profile Customization
- Upload profile pictures and banners (sellers and deliverers)
- Buyers can follow sellers for product notifications

### 4. Messaging & Notifications
- Direct buyer–seller chat
- Email/SMS notifications for:
  - Order updates
  - Delivery confirmations
  - New followers or messages

---

## 🛒 Marketplace Features

### 5. Smart Product Search
- Search with filters for category, price range, location, and verified sellers
- SQL query example:
  ```sql
  SELECT * FROM products WHERE name LIKE ? AND price BETWEEN ? AND ?;
  ```

### 6. Seller Analytics Dashboard
- Visual performance reports (Chart.js or Recharts)
- Daily/Monthly sales trends
- Top-selling products
- Customer feedback summary

### 7. Ratings & Reviews System
- Buyers can rate sellers and leave text reviews
- Seller profiles show average rating and feedback history

### 8. Discount & Promotion Codes
- Sellers can generate promotional codes (e.g., `SPARZA10` for 10% off)
- Codes stored in `promotions` table
- Automatically applied during checkout

---

## 🚚 Delivery & Deliverer System

### 9. Live Delivery Map Tracking (Optional)
- Google Maps API integration
- Real-time deliverer movement tracking
- Distance updates for buyers ("Deliverer is 2 km away")

### 10. Deliverer Earnings History
- View earnings by day, week, or month

### 11. Deliverer Leaderboard
- Gamified leaderboard showing top-rated or most active deliverers

---

## 💸 Fintech System Features

### 12. Peer-to-Peer Wallet
- Mock EFT top-up system
- Wallet balance view
- QR code payments
- Transaction log

### 13. Referral Rewards
- Earn 5 SPZ for each friend signup using referral link
- Tracked in dedicated referral table

### 14. Digital Seller Badges
- Achievements like "Top Seller of the Month"
- Future blockchain-based NFT support (mocked locally)

---

## 🧠 Admin Features

### 15. Admin Analytics Dashboard
- Interactive charts showing:
  - Total sales per category
  - Delivery success rate
  - SPZ token circulation and wallet distribution
- Export data to CSV or PDF

### 16. Automated Content Moderation
- Flags inappropriate content or language
- Suspicious posts go to admin review queue

### 17. Tax and Compliance Management
- Auto-calculates VAT for South African sellers
- Export consolidated VAT reports for compliance

---

## 🌍 Community Features

### 18. Local Pickup Points
- Designated pickup/drop-off hubs linked to public transport or community centers
- Buyers select preferred pickup location during checkout

### 19. Community Feed / Announcements
- Admin or verified sellers post public updates
- Example: "Weekend Special – 15% off all groceries!"
- Promotes local engagement and seasonal campaigns

### 20. Loyalty Program
- Buyers earn Sparza Points (convertible to SPZ) for each completed order
- Rewards automatically credited after successful purchases

---

## ⚙️ Technical & Backend Improvements

### 21. JWT Authentication API
- Secure token-based login for future mobile apps or React frontend

### 22. Email Verification on Signup
- Send verification and password reset emails through Flask-Mail

### 23. Error Logging & Monitoring
- Log errors in database table
- Send admin alerts for system failures or slow performance

### 24. Multi-language Support
- Full support for English, isiZulu, and isiXhosa via Flask-Babel

### 25. Dark/Light Mode
- Save user theme preferences in profile settings

---

## 📁 Project Structure

SparzaFI follows a clean, modular architecture with organized directories:

```
SparzaFI main app/
├── admin/              # Admin dashboard and management
├── api/                # RESTful API endpoints
├── auth/               # Authentication & authorization
├── chat/               # Real-time chat system
├── deliverer/          # Deliverer management
├── marketplace/        # Main marketplace features
├── seller/             # Seller dashboard and tools
├── user/               # User account management
├── transaction_explorer/  # Transaction analytics
├── shared/             # Shared utilities and components
│
├── docs/               # All documentation
├── scripts/            # Utility and maintenance scripts
├── tests/              # Comprehensive test suite
│
├── static/             # CSS, JS, images, fonts
├── templates/          # Jinja2 HTML templates
│
├── app.py              # Main application entry
├── config.py           # Configuration
├── firebase_*.py       # Firebase integration
└── requirements.txt    # Python dependencies
```

**For detailed structure:** See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

**Quick Links:**
- 📖 [Documentation Index](docs/README.md)
- 🔧 [Scripts Guide](scripts/README.md)
- ✅ [Testing Guide](tests/README.md)
- 🚀 [Quick Start Guide](docs/QUICK_START.md)
- 🔥 [Firebase Setup](docs/FIREBASE_INTEGRATION_GUIDE.md)

---

## 🎯 Development Roadmap

### Phase 1: Foundation & Restructuring (Week 1-2)
- [x] Reorganize into Blueprint structure
- [x] Create config.py
- [x] Set up folder structure
- [x] Extract shared components

### Phase 2: Core User Experience (Week 3-4)
- [ ] Smart Product Search (#5)
- [ ] Profile Customization (#3)
- [ ] Ratings & Reviews (#7)
- [ ] Seller Verification Dashboard (#1)

### Phase 3: Enhanced Marketplace (Week 5-6)
- [ ] Seller Analytics Dashboard (#6)
- [ ] Discount Codes (#8)
- [ ] Driver Earnings History (#10)
- [ ] Local Pickup Points (#18)

### Phase 4: Fintech Features (Week 7-8)
- [ ] Wallet-to-Cash Gateway (#2)
- [ ] Referral Rewards (#13)
- [ ] Loyalty Program (#20)
- [ ] Peer-to-Peer Marketplace Wallet (#12)

### Phase 5: Communication & Community (Week 9-10)
- [ ] Messaging System (#4)
- [ ] Email/SMS Notifications (#4)
- [ ] Community Feed (#19)

### Phase 6: Admin & Technical (Week 11-12)
- [ ] Admin Analytics (#15)
- [ ] JWT Authentication API (#21)
- [ ] Email Verification (#22)
- [ ] Error Logging (#23)

---

## 🤝 Contributing

SparzaFI is designed to empower local communities through verified commerce, fair trade, and local economic inclusion. Contributions are welcome!

---

## 📄 License

[Specify your license here]

---

## 📞 Contact

[Add contact information]

---

**SparzaFI** - Empowering local traders, community deliverers, and buyers through verified commerce, fair trade, and local economic inclusion. ✅
# SparzaFI
