# 🎭 SparzaFI Demo Accounts

Welcome to the SparzaFI sandbox environment! Use these accounts to test the platform.

---

## 🛡️ Admin Account

Test admin features, user management, and platform analytics.

```
Email:    admin@sparzafi.com
Password: adminpass
```

**What you can do:**
- View admin dashboard
- Manage users and sellers
- Approve/reject verifications
- View platform analytics
- Manage delivery routes

---

## 🛍️ Seller Account - Thandi's Kitchen

Experience the seller dashboard with pre-loaded demo data.

```
Email:    thandi@sparzafi.com
Password: sellerpass
```

**What you can do:**
- View dashboard with stats (R3,740 balance, 4 pending orders)
- Confirm and manage orders
- Add/edit products
- Upload business videos (3-slot system)
- Request withdrawal
- View customer reviews (5 reviews, 4.8★ average)
- Check analytics and top products

**Pre-loaded data:**
- 5 products with sales history
- 15 completed sales (last 7 days)
- 4 pending orders in various stages
- 5 customer reviews
- 5 followers, 4 likes

---

## 👤 Buyer Accounts

Test the buyer experience - browse, shop, and track orders.

### Primary Buyer
```
Email:    buyer1@test.com
Password: buyerpass
```

### Additional Buyers
```
buyer2@test.com / buyerpass
buyer3@test.com / buyerpass
buyer4@test.com / buyerpass
```

**What you can do:**
- Browse social video marketplace
- Like and follow sellers
- Watch seller intro videos
- Add products to cart
- Complete checkout (multiple payment methods)
- Track delivery status
- Leave reviews and ratings
- Use SPZ tokens

---

## 🚚 Deliverer Account

Test the delivery driver dashboard and order fulfillment.

```
Email:    sipho.driver@sparzafi.com
Password: driverpass
```

**Alternative Deliverer:**
```
Email:    thembi.driver@sparzafi.com
Password: driverpass
```

**What you can do:**
- View available delivery jobs
- Accept delivery assignments
- Update delivery status
- Enter pickup/delivery codes
- Track earnings
- Manage delivery routes

---

## 🎯 Testing Scenarios

### Scenario 1: Complete Buyer Journey
1. Login as `buyer1@test.com`
2. Browse sellers on home page
3. Watch Thandi's Kitchen intro videos
4. Like and follow Thandi's Kitchen
5. Click "Shop" to view products
6. Add items to cart
7. Complete checkout
8. Track order status

### Scenario 2: Seller Order Management
1. Login as `thandi@sparzafi.com`
2. View pending orders (4 orders waiting)
3. Click "Confirm" on a PENDING order
4. Click "Ready for Pickup" on CONFIRMED order
5. Note the generated pickup code
6. View analytics to see best-selling products

### Scenario 3: Withdrawal Request
1. Login as seller (Thandi)
2. Go to "Earnings" tab
3. See available balance: R3,740
4. Fill withdrawal form:
   - Amount: R1,000
   - Bank: FNB
   - Account: 1234567890
   - Holder: Thandi Moloi
5. Submit request

### Scenario 4: Product Management
1. Login as seller
2. Go to "Products" tab
3. Add new product:
   - Name: Bunny Chow
   - Price: R55.00
   - Stock: 20
4. View product in grid
5. Edit or delete product

### Scenario 5: Social Features
1. Login as buyer
2. Browse home feed
3. Click play on seller videos
4. Navigate between intro/detailed/conclusion videos
5. Click heart to like seller
6. Click "Follow" button
7. Try the chat button

---

## 💡 Tips for Testing

- **Multiple users**: Open incognito windows to test different roles simultaneously
- **Payment methods**: Try COD, EFT, SnapScan (all work in demo)
- **Order statuses**: Watch orders progress through: PENDING → CONFIRMED → READY_FOR_PICKUP
- **Reviews**: Complete a purchase to leave a verified review
- **Mobile responsive**: Test on different screen sizes

---

## 🔄 Data Reset

The sandbox database is reset daily at midnight (if auto-reset is enabled).

To manually reset:
```bash
cd /home/fineboy94449/Documents/SparzaFI
rm sparzafi.db
python3 database_seed.py
python3 seed_thandi_data.py
```

---

## 🐛 Known Demo Limitations

- **Email verification**: Disabled in demo mode (all accounts pre-verified)
- **Real payments**: Not integrated (use demo payment methods)
- **Video upload**: Placeholder (shows "coming soon" message)
- **SMS notifications**: Not active in demo
- **Live chat**: Basic implementation (not real-time yet)

---

## 📞 Need Help?

If you encounter issues:
1. Try logging out and back in
2. Clear browser cache
3. Use a different browser/incognito mode
4. Check the URL is correct

---

**Happy Testing! 🎉**

This is a fully functional demo of SparzaFI - a social marketplace platform combining video storytelling with e-commerce and fintech features.
