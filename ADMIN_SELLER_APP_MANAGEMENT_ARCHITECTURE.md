# 🏗️ إدارة المتاجر عبر التطبيقات (بدون Telegram)

**الترجمة:** إمكانية استخدام Admin و Seller تطبيق Desktop و Mobile لإدارة المتاجر مباشرة بدون الدخول للتليجرام مع تحديثات فورية وفقط للمتغيرات.

---

## 📊 الوضع الحالي

### ✅ ما يوجد الآن:

| المكون | التفاصيل | الحالة |
|------|---------|-------|
| **Flutter App (Mobile)** | تطبيق موبايل للمتجر | ✅ موجود |
| **Desktop App** | تطبيق سطح المكتب | ✅ موجود |
| **PostgreSQL Database** | قاعدة البيانات السحابية (Railway) | ✅ متصل |
| **Telegram Bot** | واجهة التليجرام | ✅ يعمل |
| **Direct DB Connection** | الاتصال المباشر بـ PostgreSQL | ✅ من التطبيق |
| **WebSocket/Real-time** | التحديثات الفورية | ❌ غير موجود |
| **REST API** | واجهة برمجية للتطبيقات | ⚠️ غير منفصل |

### ❌ ما ينقص:

1. **واجهة برمجية مركزية (Central REST/GraphQL API)**
   - حالياً كل تطبيق يتصل مباشرة بـ PostgreSQL
   - لا توجد طبقة وسيطة (Middleware)

2. **نظام التحديثات الفورية**
   - لا يوجد WebSocket أو Polling
   - لا يوجد Real-time notifications

3. **نظام الاشتراك في التغييرات (Change Subscription)**
   - تطبيقات متعددة تصل لنفس البيانات
   - لا توجد آلية لتنسيق التحديثات

---

## 🎯 ما تريده:

```
Admin ─┐
       ├─→ Desktop App ─┐
Seller ┘                ├─→ Store Management (بدون Telegram)
                        │
                        └─→ Direct Database Access
                                    ↓
                        Real-time Updates (فقط المتغيرات)
                                    ↓
                        Messages, Orders, Notifications
```

---

## ✅ هل هذا ممكن؟

### **الإجابة: نعم، 100% ممكن!** ✅

لكن يتطلب 3 مراحل:

---

## 🛠️ الحل الموصى به

### **المرحلة 1️⃣: بناء REST API (مركزي)**

#### أ) استخدام FastAPI (الأفضل):

```python
# في ملف جديد: api_server.py

from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Set

app = FastAPI()

# السماح بـ CORS للتطبيقات
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ الاتصال بـ PostgreSQL ============
import asyncpg
DATABASE_URL = os.environ.get('DATABASE_URL')
pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, ssl='require')

# ============ مسارات API للبيع والإدارة ============

# 1. الحصول على المتجر
@app.get("/api/sellers/{seller_id}/store")
async def get_store(seller_id: int):
    async with pool.acquire() as conn:
        store = await conn.fetchrow(
            "SELECT * FROM Sellers WHERE SellerID = $1",
            seller_id
        )
        return store

# 2. الحصول على الرسائل الجديدة (الطلبات)
@app.get("/api/sellers/{seller_id}/messages")
async def get_messages(seller_id: int, skip: int = 0, limit: int = 50):
    async with pool.acquire() as conn:
        messages = await conn.fetch(
            """SELECT * FROM Messages 
               WHERE SellerID = $1 
               ORDER BY CreatedAt DESC 
               LIMIT $2 OFFSET $3""",
            seller_id, limit, skip
        )
        return messages

# 3. الحصول على الطلبات
@app.get("/api/sellers/{seller_id}/orders")
async def get_orders(seller_id: int):
    async with pool.acquire() as conn:
        orders = await conn.fetch(
            """SELECT o.*, COUNT(oi.ItemID) as items_count
               FROM Orders o
               LEFT JOIN OrderItems oi ON o.OrderID = oi.OrderID
               WHERE o.SellerID = $1
               GROUP BY o.OrderID
               ORDER BY o.CreatedAt DESC""",
            seller_id
        )
        return orders

# 4. تحديث حالة الطلب
@app.post("/api/orders/{order_id}/status")
async def update_order_status(order_id: int, status: str):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE Orders SET Status = $1, UpdatedAt = NOW() WHERE OrderID = $2",
            status, order_id
        )
        return {"success": True}

# 5. إضافة منتج
@app.post("/api/sellers/{seller_id}/products")
async def add_product(seller_id: int, product_data: dict):
    async with pool.acquire() as conn:
        product_id = await conn.fetchval(
            """INSERT INTO Products 
               (SellerID, ProductName, Price, Quantity, Description, Status)
               VALUES ($1, $2, $3, $4, $5, $6)
               RETURNING ProductID""",
            seller_id, product_data['name'], product_data['price'],
            product_data['quantity'], product_data.get('description'), 'active'
        )
        return {"product_id": product_id}

# 6. تحديث المنتج
@app.put("/api/products/{product_id}")
async def update_product(product_id: int, data: dict):
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE Products 
               SET ProductName = $1, Price = $2, Quantity = $3, UpdatedAt = NOW()
               WHERE ProductID = $4""",
            data.get('name'), data.get('price'), data.get('quantity'), product_id
        )
        return {"success": True}
```

---

### **المرحلة 2️⃣: نظام التحديثات الفورية (Real-time)**

#### الخيار A: WebSocket (الأفضل للأداء)

```python
# إضافة لـ api_server.py

# متغير عام لتتبع الاتصالات
active_connections: dict = {}  # {seller_id: [websocket1, websocket2, ...]}

@app.websocket("/ws/seller/{seller_id}")
async def websocket_endpoint(websocket: WebSocket, seller_id: int):
    await websocket.accept()
    
    # إضافة الاتصال للقائمة
    if seller_id not in active_connections:
        active_connections[seller_id] = []
    active_connections[seller_id].append(websocket)
    
    try:
        while True:
            # الاستقبال من التطبيق
            data = await websocket.receive_json()
            
            # التعامل مع الرسالة
            if data['type'] == 'acknowledge':
                # تطبيق أرسل رسالة اعتراف
                print(f"Seller {seller_id} received update")
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # إزالة الاتصال
        active_connections[seller_id].remove(websocket)

# دالة لإرسال تحديث لكل الـ sellers المتصلين
async def broadcast_to_seller(seller_id: int, update: dict):
    """إرسال تحديث فوراً لبائع معين"""
    if seller_id in active_connections:
        for connection in active_connections[seller_id]:
            try:
                await connection.send_json(update)
            except Exception as e:
                print(f"Failed to send: {e}")

# دالة للاستدعاء من bot.py عند حدث جديد
async def notify_seller_new_order(seller_id: int, order_data: dict):
    """عند وصول طلب جديد"""
    await broadcast_to_seller(seller_id, {
        "type": "new_order",
        "order_id": order_data['order_id'],
        "customer_name": order_data['customer_name'],
        "total": order_data['total'],
        "timestamp": datetime.now().isoformat(),
        "items": order_data['items']  # فقط المعلومات المتغيرة
    })

async def notify_seller_new_message(seller_id: int, message_data: dict):
    """عند وصول رسالة جديدة"""
    await broadcast_to_seller(seller_id, {
        "type": "new_message",
        "message_id": message_data['id'],
        "customer_name": message_data['customer'],
        "message": message_data['text'],
        "timestamp": datetime.now().isoformat()
    })
```

#### الخيار B: Polling (إذا كنت تريد شيء أبسط)

```python
# في التطبيق (Flutter/Desktop)

class RealtimeService {
    static Future<void> startPolling(int sellerId) async {
        while (true) {
            try {
                final response = await http.get(
                    Uri.parse('https://your-api.com/api/sellers/$sellerId/updates?since=$lastUpdate')
                );
                
                if (response.statusCode == 200) {
                    final updates = jsonDecode(response.body);
                    for (var update in updates) {
                        handleUpdate(update);  // معالجة فقط المتغيرات
                    }
                    lastUpdate = DateTime.now();
                }
                
                // انتظر 5 ثواني قبل الفحص التالي
                await Future.delayed(Duration(seconds: 5));
            } catch (e) {
                print('Polling error: $e');
                await Future.delayed(Duration(seconds: 10));
            }
        }
    }
}
```

---

### **المرحلة 3️⃣: ربط API بالتطبيقات**

#### التطبيق (Flutter):

```dart
// lib/services/seller_api_service.dart

class SellerApiService {
  static const String BASE_URL = 'https://your-api.com';
  static WebSocket? _websocket;
  static int? _sellerId;

  // الاتصال بـ WebSocket
  static Future<void> connectWebSocket(int sellerId) async {
    _sellerId = sellerId;
    try {
      _websocket = await WebSocket.connect(
        'wss://your-api.com/ws/seller/$sellerId'
      );
      
      // الاستماع للتحديثات
      _websocket?.listen((dynamic message) {
        final data = jsonDecode(message);
        handleUpdate(data);
      });
    } catch (e) {
      print('WebSocket connection failed: $e');
    }
  }

  // الحصول على الرسائل
  static Future<List<Message>> getMessages(int sellerId) async {
    final response = await http.get(
      Uri.parse('$BASE_URL/api/sellers/$sellerId/messages'),
      headers: {'Authorization': 'Bearer $token'},
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List;
      return data.map((m) => Message.fromJson(m)).toList();
    }
    throw Exception('Failed to load messages');
  }

  // إضافة منتج
  static Future<int> addProduct(int sellerId, ProductData data) async {
    final response = await http.post(
      Uri.parse('$BASE_URL/api/sellers/$sellerId/products'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(data.toJson()),
    );
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body)['product_id'];
    }
    throw Exception('Failed to add product');
  }

  // تحديث حالة الطلب
  static Future<void> updateOrderStatus(int orderId, String status) async {
    final response = await http.post(
      Uri.parse('$BASE_URL/api/orders/$orderId/status'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({'status': status}),
    );
    
    if (response.statusCode != 200) {
      throw Exception('Failed to update order status');
    }
  }

  static void handleUpdate(Map<String, dynamic> update) {
    switch (update['type']) {
      case 'new_order':
        // تحديث قائمة الطلبات
        print('📦 طلب جديد: #${update['order_id']}');
        // تحديث الـ UI بدون إعادة تحميل كامل
        break;
      case 'new_message':
        // تحديث قائمة الرسائل
        print('💬 رسالة جديدة من ${update['customer_name']}');
        break;
      case 'product_sold':
        // تحديث الكمية فقط
        print('تم بيع منتج #${update['product_id']}');
        break;
    }
  }
}
```

#### استخدام في الشاشة:

```dart
// lib/screens/seller_dashboard.dart

class SellerDashboard extends StatefulWidget {
  @override
  _SellerDashboardState createState() => _SellerDashboardState();
}

class _SellerDashboardState extends State<SellerDashboard> {
  late List<Message> messages = [];
  late List<Order> orders = [];

  @override
  void initState() {
    super.initState();
    final sellerId = getCurrentSellerId();
    
    // الاتصال بـ WebSocket للتحديثات الفورية
    SellerApiService.connectWebSocket(sellerId);
    
    // جلب البيانات الأولية
    _loadData();
  }

  Future<void> _loadData() async {
    final sellerId = getCurrentSellerId();
    messages = await SellerApiService.getMessages(sellerId);
    orders = await SellerApiService.getOrders(sellerId);
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('لوحة البائع'),
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // قسم الرسائل/الطلبات الجديدة
            MessagesSection(messages: messages),
            
            // قسم الطلبات
            OrdersSection(orders: orders),
            
            // قسم المنتجات
            ProductsManagementSection(),
          ],
        ),
      ),
    );
  }
}
```

---

### **المرحلة 4️⃣: تحديث bot.py للتكامل**

```python
# في bot.py، عند إنشاء طلب:

async def notify_seller_via_api(seller_id: int, order_data: dict):
    """تنبيه البائع عبر API بدلاً من Telegram"""
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'https://your-api.com/api/sellers/{seller_id}/notify',
            json={
                'type': 'new_order',
                'order_id': order_data['order_id'],
                'items': order_data['items'],
                'customer': order_data['customer_name'],
                'total': order_data['total']
            }
        ) as resp:
            if resp.status == 200:
                print(f"✅ Seller {seller_id} notified via API")

# تحديث الدالة الحالية
async def create_confirmed_order(telegram_id, seller_id, items, payment_method='credit'):
    # ... الكود الحالي ...
    
    # بدلاً من إرسال رسالة Telegram:
    if os.environ.get('USE_API_NOTIFICATIONS') == 'true':
        await notify_seller_via_api(seller_id, {
            'order_id': order_id,
            'items': items,
            'customer_name': customer_name,
            'total': total_amount
        })
    else:
        # الإرسال التقليدي عبر Telegram
        bot.send_message(seller_telegram_id, message_text)
```

---

## 📊 مقارنة الحلول

| المعيار | WebSocket | Polling | GraphQL |
|--------|-----------|---------|---------|
| **التأخير** | 0.1s | 5-10s | 0.5s |
| **استهلاك البيانات** | منخفض جداً | عالي | منخفض |
| **التعقيد** | متوسط | بسيط | معقد |
| **الأداء** | عالي جداً | متوسط | عالي |
| **الموصى به** | ✅ الأفضل | للتطبيقات الخفيفة | للمشاريع الكبرى |

---

## 🚀 خطة التنفيذ (مرحلي)

### **الأسبوع 1:**
- [ ] بناء API بـ FastAPI (Messages, Orders, Products endpoints)
- [ ] الاختبار المحلي
- [ ] النشر على Railway أو Heroku

### **الأسبوع 2:**
- [ ] إضافة WebSocket للتحديثات الفورية
- [ ] اختبار الاتصال المتزامن
- [ ] تحسين الأداء

### **الأسبوع 3:**
- [ ] تحديث Flutter app للاتصال بـ API
- [ ] تحديث Desktop app
- [ ] حذف الاتصال المباشر بـ DB (اختياري)

### **الأسبوع 4:**
- [ ] ربط bot.py بـ API
- [ ] اختبارات شاملة
- [ ] النشر على الإنتاج

---

## 🔐 الأمان

```python
# في API، إضافة المصادقة:

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
import jwt

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
        seller_id = payload.get("seller_id")
        return seller_id
    except:
        raise HTTPException(status_code=401)

@app.get("/api/sellers/{seller_id}/messages")
async def get_messages(seller_id: int, current_seller = Depends(verify_token)):
    if current_seller != seller_id:
        raise HTTPException(status_code=403)
    # ... الكود ...
```

---

## 🎯 الخلاصة

| السؤال | الإجابة |
|------|--------|
| هل ممكن إدارة المتاجر بدون Telegram؟ | ✅ نعم، تماماً |
| هل التحديثات تكون فورية؟ | ✅ نعم، مع WebSocket |
| هل فقط المتغيرات تُرسل؟ | ✅ نعم، تصميم البروتوكول يسمح بذلك |
| كم المجهود المطلوب؟ | 3-4 أسابيع تطوير |
| هل يتطلب تغيير كبير في bot.py؟ | ❌ لا، إضافة بسيطة فقط |

**النتيجة النهائية:** سيكون لديك نظام احترافي يسمح للـ Admins و Sellers بإدارة كل شيء من التطبيقات بكفاءة عالية! 🚀
