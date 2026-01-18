# Desktop App Configuration for Closed Store Instant Purchase

## File: flutter_store_app/lib/screens/cart_screen.dart

### New Dependencies Added
- `import '../../models/database_models.dart';` - For ProductImage class

### New Method: `_showPurchasedImages()`
**Location:** Lines 48-101
**Purpose:** Display purchased product images in a dialog after instant order creation

**Parameters:**
- `items` (List<Map<String, dynamic>>): List of cart items with ProductID

**Logic:**
1. Iterate through all purchased items
2. For each item, fetch images via `DatabaseHelper.instance.getProductImages(productId)`
3. Build itemsWithImages list containing items with available images
4. Display dialog with:
   - Product name as header
   - Horizontal scrollable image list (120x120 each)
   - Fallback placeholder for missing images
   - "حسناً" button to dismiss

**UI Components:**
- `AlertDialog` with title "📸 صور المنتجات المشتراة"
- `SingleChildScrollView` for vertical scrolling
- `ListView.builder` with horizontal scroll for images
- `Image.file()` for displaying image from file path
- `Container` with grey background for missing images

### Modified Method: `_placeOrder()`
**Location:** Lines 118-244
**Key Changes for Closed Store Flow:**

#### Lines 118-167: Closed Store Detection
```dart
// Check all stores in cart
for (var sellerId in bySeller.keys) {
  final seller = sellers.firstWhere(...);
  if (seller == null || !seller.requireCustomerRegistration) {
    allStoresClosed = false;
    break;
  }
  
  // Check customer registration
  final creditCustomers = await DatabaseHelper.instance.getCreditCustomers(sellerId);
  final isRegistered = creditCustomers.any((cc) => cc.telegramId == widget.userId);
  
  if (!isRegistered) {
    userRegisteredInAll = false;
    break;
  }
}
```

#### Lines 169-200: Order Creation Loop
```dart
if (allStoresClosed && userRegisteredInAll) {
  // For each seller, create order with:
  // - status: 'Confirmed'
  // - paymentMethod: 'credit'
  // - fullyPaid: false
  // - notes: 'طلب مؤكد من زبون آجل'
  // - address: '' (empty, not needed)
}
```

#### Lines 189-197: Credit Transaction (NEW)
```dart
await DatabaseHelper.instance.addCreditTransaction(
  customerId: widget.userId,
  sellerId: sellerId,
  transactionType: 'purchase',
  amount: total,
  description: 'شراء آجل - طلب #$orderId'
);
```
- Records deduction from customer's credit account
- Uses transaction type 'purchase'
- Amount equals total order value
- Description includes order number for tracking

#### Lines 199-200: Clear Cart & Display Images (NEW)
```dart
await DatabaseHelper.instance.clearCart(widget.userId);
await _showPurchasedImages(items);
```

#### Lines 202-225: Enhanced Success Dialog
```dart
AlertDialog(
  title: "✅ تم إنزال طلبك",
  content: Column(
    const Text("تم إنزال طلبك بنجاح!"),
    Text("المبلغ المخصوم: ${formatPrice(totalAllOrders)} د.ع"),
    const Text("✅ تم تطبيق المبلغ على حسابك الآجل", 
              style: TextStyle(color: Colors.green)),
    const Text("سيتم معالجة الطلب من قبل صاحب المتجر",
              style: TextStyle(color: Colors.grey)),
  ),
)
```

### Database Method Calls

#### 1. getCreditCustomers(sellerId)
**Purpose:** Get all credit customers for a store
**Returns:** List<CreditCustomer>
**Usage:** Check if user is registered in that store
```dart
final creditCustomers = await DatabaseHelper.instance.getCreditCustomers(sellerId);
final isRegistered = creditCustomers.any((cc) => cc.telegramId == widget.userId);
```

#### 2. createOrder()
**Purpose:** Create order record in database
**Parameters:**
- `buyerId`: Customer/user ID
- `sellerId`: Store ID
- `total`: Order total amount
- `address`: Delivery address (empty string for closed stores)
- `notes`: Order notes
- `items`: List of order items
- `status`: 'Confirmed' for instant orders
- `paymentMethod`: 'credit' for credit customers
- `fullyPaid`: false (no immediate payment)

**Returns:** int (orderId)

#### 3. addCreditTransaction()
**Purpose:** Record credit transaction in customer's account
**Parameters:**
- `customerId`: Customer ID
- `sellerId`: Store ID
- `transactionType`: 'purchase' for orders
- `amount`: Amount to deduct
- `description`: Transaction description for tracking

**Returns:** void (Future<void>)

#### 4. getProductImages(productId)
**Purpose:** Get all images for a product
**Parameters:**
- `productId`: Product ID

**Returns:** List<ProductImage>
- Each includes: imageId, productId, imagePath, imageOrder

#### 5. addMessage()
**Purpose:** Send notification to seller
**Parameters:**
- `orderId`: Order ID
- `sellerId`: Seller ID
- `messageType`: 'new_order'
- `messageText`: Message content (e.g., "طلب جديد #$orderId - مؤكد")

**Returns:** void (Future<void>)

#### 6. clearCart()
**Purpose:** Remove all items from customer's cart
**Parameters:**
- `customerId`: Customer ID

**Returns:** void (Future<void>)

## Closed Store Checkout Flow - Complete

### Preconditions
1. Store has `RequireCustomerRegistration = 1` (closed store)
2. Customer is registered in `CreditCustomers` table for that store
3. ALL stores in cart must be closed AND customer registered in ALL

### Execution Steps
1. **Check Conditions** - Verify all stores closed + customer registered in all
2. **Create Order** - For each seller:
   - Create order record with status='Confirmed', paymentMethod='credit'
   - Get total amount for that seller's items
3. **Deduct Credit** - Add transaction to `CustomerCredit`:
   - TransactionType = 'purchase'
   - Amount = order total
   - Tracks deduction on customer's account
4. **Update Inventory** - Handled by `createOrder()`:
   - Updates `Products` table Quantity
   - Decrements by purchased amount
5. **Display Images** - Show product images in dialog:
   - Fetches from `imagestorage` table via ProductID
   - Shows in horizontal scrollable list
   - Provides visual confirmation
6. **Notify Parties**:
   - **Seller:** Message "طلب جديد #$orderId - مؤكد"
   - **Customer:** Success dialog with:
     - "تم إنزال طلبك بنجاح!"
     - Amount deducted from account
     - Confirmation images shown
7. **Clean Up** - Clear customer's cart

### Database Records Created
1. **Orders** table:
   - BuyerID = customer ID
   - SellerID = store ID
   - Total = order amount
   - Status = 'Confirmed'
   - PaymentMethod = 'credit'
   - FullyPaid = false
   - Address = '' (empty)
   - Notes = 'طلب مؤكد من زبون آجل'

2. **OrderItems** table:
   - OrderID = created order ID
   - ProductID = purchased product
   - Quantity = purchased quantity
   - Price = product price at time of purchase

3. **CustomerCredit** table:
   - CustomerID = customer ID
   - SellerID = store ID
   - TransactionType = 'purchase'
   - Amount = order total
   - Description = 'شراء آجل - طلب #$orderId'
   - BalanceBefore = previous balance
   - BalanceAfter = balance after deduction

4. **Messages** table:
   - OrderID = created order ID
   - SellerID = store ID
   - MessageType = 'new_order'
   - MessageText = 'طلب جديد #$orderId - مؤكد'
   - CreatedAt = current timestamp

## Error Handling

### Try-Catch Block
- Location: Lines 176-239
- Catches exceptions during order creation
- Displays error snackbar if any step fails
- Ensures _isLoading flag reset in finally block

### Validation
- Check for null sellerId (skip orphaned items)
- Check for database availability
- Verify seller exists and has requireCustomerRegistration=1
- Verify customer is in creditCustomers table

## UI/UX Elements

### Loading State
- `setState(() => _isLoading = true)` at start
- `setState(() => _isLoading = false)` in finally
- Disables button during processing

### User Feedback
1. **Image Dialog** - Shows what was purchased
2. **Success Dialog** - Confirms amount deducted
3. **Snackbar** - Shows errors if any
4. **Cart Clear** - Visual confirmation items removed

## Testing Scenarios

### Positive Flow
1. Customer logged in
2. Add items from closed store(s) to cart
3. Customer registered in those stores
4. Click "إتمام جميع الطلبات"
5. Expected:
   - Order created with status='Confirmed'
   - Credit deducted
   - Images shown
   - Success message displayed
   - Seller notified
   - Cart cleared

### Negative Scenarios
1. **Store is Open** - Skip instant checkout, use delivery dialog
2. **Customer Not Registered** - Skip instant checkout, use delivery dialog
3. **Database Error** - Show error snackbar, keep cart intact
4. **Image Not Found** - Show placeholder, continue with success

## Feature Parity with Bot

| Step | Bot (Telegram) | Desktop (Flutter) | Status |
|------|---|---|---|
| Check closed store | ✅ | ✅ | MATCH |
| Check registration | ✅ | ✅ | MATCH |
| Create order | ✅ | ✅ | MATCH |
| Set status='Confirmed' | ✅ | ✅ | MATCH |
| Set paymentMethod='credit' | ✅ | ✅ | MATCH |
| Deduct credit | ✅ | ✅ | MATCH |
| Update inventory | ✅ | ✅ | MATCH |
| Fetch images | ✅ Send | ✅ Display | ALIGNED |
| Notify seller | ✅ | ✅ | MATCH |
| Success message | ✅ | ✅ | MATCH |

## Known Limitations

1. **Desktop Images:** Displayed in dialog (app uses local file paths)
   - Bot: Sends images directly to Telegram
   - Both show images to customer ✅

2. **Notification Method:** Desktop uses database messages
   - Bot: Sends Telegram messages
   - Both notify seller ✅

3. **Network:** Desktop assumes local PostgreSQL availability
   - Bot: Works with cloud PostgreSQL (Railway)
   - Configuration handles via DatabaseHelper ✅

## Performance Notes

- Image fetching: One query per product in cart
- Total queries: ~3-4 DB calls per closed store order
- Dialog display: Async, doesn't block UI
- No network latency (local paths for images)

---

**Status:** ✅ Complete and Ready for Testing
**Version:** 1.0.0
**Last Updated:** 2025-01-18
