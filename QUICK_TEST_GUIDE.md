# ⚡ Quick Test Guide - Desktop vs Bot Parity

## 🎯 Objective
Verify that Desktop app and Telegram bot produce identical results for closed store instant purchases.

---

## 📋 Prerequisites

### Database Setup
- [ ] PostgreSQL running (switchback.proxy.rlwy.net:20266)
- [ ] Test store: SellerID=21, RequireCustomerRegistration=1
- [ ] Test user: CustomerID=30, registered in store 21
- [ ] Test product: Exists in store 21 with Quantity>0
- [ ] Test images: Exist in imagestorage table

### System Setup
- [ ] Bot running (PID 25912)
- [ ] Desktop app built/ready to run
- [ ] Telegram client open
- [ ] PostgreSQL client available

---

## 🧪 Test Scenario A: Desktop App Flow

### Step 1: Launch Desktop App
```
Execute: flutter run (desktop mode)
Expected: App loads, shows store list
```

### Step 2: Login as Test Customer
```
Action: Log in with CustomerID 30
Expected: User dashboard shows
```

### Step 3: Navigate to Closed Store
```
Action: Browse products from SellerID=21
Expected: Product list displayed
```

### Step 4: Add Item to Cart
```
Action: Click "أضف للسلة" on any product
Expected: Item added, cart count increases
```

### Step 5: Open Cart
```
Action: Click "سلة المشتريات"
Expected: Cart screen shows product
```

### Step 6: Place Order
```
Action: Click "إتمام جميع الطلبات"
Expected: 
  ✅ NO delivery address dialog
  ✅ Image dialog appears
  ✅ Product photos shown (120x120)
  ✅ Success dialog appears with:
     - "تم إنزال طلبك بنجاح!"
     - Amount: "XXXX د.ع"
     - Green text: "✅ تم تطبيق المبلغ على حسابك الآجل"
  ✅ Cart becomes empty
```

### Step 7: Verify Database
```sql
-- Check order was created
SELECT * FROM Orders WHERE BuyerID=30 ORDER BY OrderID DESC LIMIT 1;
Expected:
  - Status = 'Confirmed' ✅
  - PaymentMethod = 'credit' ✅
  - FullyPaid = false ✅

-- Check credit transaction
SELECT * FROM CustomerCredit WHERE CustomerID=30 ORDER BY CreditID DESC LIMIT 1;
Expected:
  - TransactionType = 'purchase' ✅
  - Amount = [order total] ✅
  - Description contains "شراء آجل" ✅

-- Check seller notification
SELECT * FROM Messages WHERE OrderID=[order_id];
Expected:
  - MessageType = 'new_order' ✅
  - MessageText contains "مؤكد" ✅
```

---

## 🧪 Test Scenario B: Telegram Bot Flow

### Step 1: Start Chat with Bot
```
Telegram: /start
Expected: Bot responds with menu
```

### Step 2: Access Store
```
Telegram: Browse store 21
Expected: Product list displayed
```

### Step 3: Add Item
```
Telegram: Select product and quantity
Expected: Item added to cart
```

### Step 4: Checkout
```
Telegram: Click "إتمام الطلب" or equivalent
Expected:
  ✅ Bot recognizes closed store + registration
  ✅ Bot creates order immediately
  ✅ Bot sends product images
  ✅ Bot sends confirmation message:
     - "✅ تم تأكيد طلبك بنجاح!"
     - "📋 رقم الطلب: [ID]"
     - "💰 المبلغ الإجمالي: XXXX د.ع"
     - "📦 تم إضافة المبلغ إلى حسابك الآجل"
  ✅ Bot notifies seller
```

### Step 5: Verify Database (Same as Desktop)
```sql
-- Check order
SELECT * FROM Orders WHERE BuyerID=30 ORDER BY OrderID DESC LIMIT 1;
Expected: Same structure as Desktop

-- Check credit transaction
SELECT * FROM CustomerCredit WHERE CustomerID=30 ORDER BY CreditID DESC LIMIT 1;
Expected: Same as Desktop

-- Check notification
SELECT * FROM Messages WHERE OrderID=[order_id];
Expected: Same as Desktop
```

---

## 🔍 Comparison Results

### Database Records Should Match

| Table | Field | Desktop Value | Bot Value | Match |
|-------|-------|---|---|---|
| Orders | Status | 'Confirmed' | 'Confirmed' | ✅ |
| Orders | PaymentMethod | 'credit' | 'credit' | ✅ |
| Orders | FullyPaid | false | false | ✅ |
| Orders | Total | [amount] | [amount] | ✅ |
| CustomerCredit | TransactionType | 'purchase' | 'purchase' | ✅ |
| CustomerCredit | Amount | [amount] | [amount] | ✅ |
| Messages | MessageType | 'new_order' | 'new_order' | ✅ |
| Messages | Contains | 'مؤكد' | 'مؤكد' | ✅ |

### UI/UX Experience

| Aspect | Desktop | Bot | Match |
|--------|---------|-----|-------|
| No delivery dialog | ✅ Yes | ✅ Yes | ✅ |
| Immediate confirmation | ✅ Yes | ✅ Yes | ✅ |
| Shows images | ✅ Dialog | ✅ Telegram | ✅ |
| Shows amount | ✅ Yes | ✅ Yes | ✅ |
| Confirms credit applied | ✅ Yes | ✅ Yes | ✅ |
| Seller notified | ✅ Yes | ✅ Yes | ✅ |

---

## ⚠️ Troubleshooting

### Issue: No image dialog on Desktop
**Check:**
- [ ] Images exist in imagestorage table
- [ ] Product exists in Products table
- [ ] File paths are valid
**Fix:** Verify imagespath column values

### Issue: Credit not deducted
**Check:**
- [ ] addCreditTransaction() executed
- [ ] CustomerCredit table exists
- [ ] Seller exists in Sellers table
**Fix:** Check database for errors

### Issue: Delivery dialog still shows
**Check:**
- [ ] requireCustomerRegistration = 1
- [ ] User registered in CreditCustomers
- [ ] Store ID correct
**Fix:** Verify store configuration

### Issue: Seller not notified
**Check:**
- [ ] Messages table has record
- [ ] Seller has access to read messages
- [ ] Message display implemented
**Fix:** Check message delivery system

---

## ✅ Verification Checklist

### For Each Test Case
- [ ] Desktop order created correctly
- [ ] Bot order created correctly
- [ ] Database records match
- [ ] Credit amount matches
- [ ] Images displayed (Desktop) / Sent (Bot)
- [ ] Seller notified in both
- [ ] Customer confirmed in both

### Final Verification
- [ ] All database fields match
- [ ] Order IDs sequential
- [ ] Timestamps reasonable
- [ ] Amounts correct
- [ ] No error messages
- [ ] Features working as expected

---

## 📊 Test Results Template

```
Test Date: ___________
Test User: 30
Test Store: 21
Test Product: [ID] [Name]
Test Amount: XXXX د.ع

DESKTOP APP:
✅ / ❌ App launches
✅ / ❌ Login successful
✅ / ❌ Product found
✅ / ❌ Item added to cart
✅ / ❌ Order placed
✅ / ❌ No delivery dialog
✅ / ❌ Image dialog shown
✅ / ❌ Success message shown
✅ / ❌ Cart cleared

DATABASE (After Desktop):
OrderID: ___________
Status: 'Confirmed' ✅ / ❌
PaymentMethod: 'credit' ✅ / ❌
Amount: XXXX د.ع ✅ / ❌
Credit Transaction: ✅ / ❌
Seller Message: ✅ / ❌

TELEGRAM BOT:
✅ / ❌ Chat started
✅ / ❌ Store accessed
✅ / ❌ Product found
✅ / ❌ Item added
✅ / ❌ Order placed
✅ / ❌ No delivery prompt
✅ / ❌ Images received
✅ / ❌ Confirmation message
✅ / ❌ Seller notified

DATABASE (After Bot):
OrderID: ___________
Status: 'Confirmed' ✅ / ❌
PaymentMethod: 'credit' ✅ / ❌
Amount: XXXX د.ع ✅ / ❌
Credit Transaction: ✅ / ❌
Seller Message: ✅ / ❌

COMPARISON:
✅ / ❌ Order structure identical
✅ / ❌ Amounts match
✅ / ❌ Transactions match
✅ / ❌ Messages match
✅ / ❌ Inventory updated correctly

CONCLUSION:
[ ] PASS - Feature parity achieved
[ ] FAIL - Issues found (list below)

Issues Found:
_________________________________
_________________________________
_________________________________

Notes:
_________________________________
_________________________________
```

---

## 🚀 Post-Test Actions

### If All Tests Pass ✅
1. Document results
2. Mark feature as ready
3. Deploy to production
4. Notify stakeholders
5. Monitor usage

### If Issues Found ❌
1. Log issues with details
2. Update code as needed
3. Re-run affected tests
4. Verify fixes
5. Repeat until all pass

---

## 📞 Test Support

### Quick Reference Commands

```sql
-- Get test customer info
SELECT * FROM CreditCustomers WHERE CustomerID = 30;

-- Get closed store info
SELECT * FROM Sellers WHERE SellerID = 21;

-- Get test product
SELECT * FROM Products WHERE SellerID = 21 LIMIT 1;

-- Check latest order
SELECT * FROM Orders WHERE BuyerID = 30 ORDER BY OrderID DESC LIMIT 1;

-- Check latest credit transaction
SELECT * FROM CustomerCredit WHERE CustomerID = 30 ORDER BY CreditID DESC LIMIT 1;

-- Check seller messages
SELECT * FROM Messages WHERE SellerID = 21 ORDER BY CreatedAt DESC LIMIT 5;
```

---

**Test Duration:** ~15-20 minutes per scenario
**Status:** Ready to execute
**Last Updated:** January 18, 2026
