# 🚀 API سريعة التنفيذ - نموذج جاهز للاستخدام

**هدف هذا الملف:** توفير كود جاهز يمكنك نسخه مباشرة والبدء به الآن!

---

## 📦 الخطوة 1: التثبيت

```bash
pip install fastapi uvicorn asyncpg python-dotenv aiohttp websockets
```

---

## 🔧 الخطوة 2: إنشاء ملف `api_server.py`

```python
# api_server.py
# نموذج API كامل وجاهز للاستخدام

import os
import asyncio
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import FastAPI, WebSocket, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncpg
import json
from dotenv import load_dotenv

load_dotenv()

# ============ الإعدادات ============
DATABASE_URL = os.environ.get('DATABASE_URL', '')
API_PORT = int(os.environ.get('API_PORT', 8000))
API_HOST = os.environ.get('API_HOST', '0.0.0.0')

# متغير عام للاتصال
db_pool = None
active_connections: Dict[int, List[WebSocket]] = {}  # {seller_id: [ws1, ws2, ...]}

# ============ Lifespan Events ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            ssl='require',
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        print("✅ Connected to PostgreSQL")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise
    
    yield
    
    # Shutdown
    if db_pool:
        await db_pool.close()
        print("✅ Database connection closed")

app = FastAPI(title="TelegramStoreBot API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ دوال المساعدة ============

async def get_seller(seller_id: int):
    """الحصول على بيانات البائع"""
    async with db_pool.acquire() as conn:
        return await conn.fetchrow(
            'SELECT * FROM "Sellers" WHERE "SellerID" = $1',
            seller_id
        )

async def broadcast_update(seller_id: int, message: dict):
    """إرسال تحديث لجميع اتصالات البائع النشطة"""
    if seller_id in active_connections:
        dead_connections = []
        for connection in active_connections[seller_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Failed to send to connection: {e}")
                dead_connections.append(connection)
        
        # حذف الاتصالات المقطوعة
        for conn in dead_connections:
            active_connections[seller_id].remove(conn)

# ============ مسارات WebSocket ============

@app.websocket("/ws/seller/{seller_id}")
async def websocket_endpoint(websocket: WebSocket, seller_id: int):
    """WebSocket للتحديثات الفورية"""
    await websocket.accept()
    
    if seller_id not in active_connections:
        active_connections[seller_id] = []
    active_connections[seller_id].append(websocket)
    
    print(f"✅ Seller {seller_id} connected ({len(active_connections[seller_id])} connections)")
    
    try:
        while True:
            data = await websocket.receive_json()
            if data.get('type') == 'ping':
                await websocket.send_json({'type': 'pong'})
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        active_connections[seller_id].remove(websocket)
        if not active_connections[seller_id]:
            del active_connections[seller_id]
        print(f"❌ Seller {seller_id} disconnected")

# ============ مسارات REST API ============

# ---- الرسائل والطلبات ----

@app.get("/api/sellers/{seller_id}/messages")
async def get_messages(
    seller_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = False
):
    """الحصول على رسائل البائع"""
    async with db_pool.acquire() as conn:
        query = '''
            SELECT 
                m.*,
                u."FullName" as customer_name
            FROM "Messages" m
            LEFT JOIN "Users" u ON m."UserID" = u."UserID"
            WHERE m."SellerID" = $1
        '''
        params = [seller_id]
        
        if unread_only:
            query += ' AND m."IsRead" = false'
        
        query += ' ORDER BY m."CreatedAt" DESC LIMIT $2 OFFSET $3'
        params.extend([limit, skip])
        
        messages = await conn.fetch(query, *params)
        return {
            "count": len(messages),
            "messages": [dict(m) for m in messages]
        }

@app.get("/api/sellers/{seller_id}/orders")
async def get_orders(
    seller_id: int,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """الحصول على طلبات البائع"""
    async with db_pool.acquire() as conn:
        query = '''
            SELECT 
                o.*,
                u."FullName" as customer_name,
                COUNT(oi."ItemID") as items_count,
                SUM(oi."Price" * oi."Quantity") as total_price
            FROM "Orders" o
            LEFT JOIN "Users" u ON o."BuyerID" = u."UserID"
            LEFT JOIN "OrderItems" oi ON o."OrderID" = oi."OrderID"
            WHERE o."SellerID" = $1
        '''
        params = [seller_id]
        param_count = 1
        
        if status:
            param_count += 1
            query += f' AND o."Status" = ${param_count}'
            params.append(status)
        
        query += f' GROUP BY o."OrderID", u."FullName" ORDER BY o."CreatedAt" DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}'
        params.extend([limit, skip])
        
        orders = await conn.fetch(query, *params)
        return {
            "count": len(orders),
            "orders": [dict(o) for o in orders]
        }

@app.post("/api/orders/{order_id}/status")
async def update_order_status(order_id: int, new_status: str):
    """تحديث حالة الطلب"""
    async with db_pool.acquire() as conn:
        # الحصول على بيانات الطلب
        order = await conn.fetchrow(
            'SELECT * FROM "Orders" WHERE "OrderID" = $1',
            order_id
        )
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # تحديث الحالة
        await conn.execute(
            '''UPDATE "Orders" 
               SET "Status" = $1, "UpdatedAt" = NOW() 
               WHERE "OrderID" = $2''',
            new_status, order_id
        )
        
        # إخطار البائع بالتحديث
        await broadcast_update(order['SellerID'], {
            'type': 'order_status_updated',
            'order_id': order_id,
            'new_status': new_status,
            'timestamp': datetime.now().isoformat()
        })
        
        return {'success': True, 'message': 'Order status updated'}

# ---- المنتجات ----

@app.get("/api/sellers/{seller_id}/products")
async def get_products(seller_id: int):
    """الحصول على منتجات البائع"""
    async with db_pool.acquire() as conn:
        products = await conn.fetch(
            '''SELECT * FROM "Products" 
               WHERE "SellerID" = $1 
               ORDER BY "ProductName" ASC''',
            seller_id
        )
        return {
            "count": len(products),
            "products": [dict(p) for p in products]
        }

@app.post("/api/sellers/{seller_id}/products")
async def add_product(seller_id: int, product_data: dict):
    """إضافة منتج جديد"""
    async with db_pool.acquire() as conn:
        product_id = await conn.fetchval(
            '''INSERT INTO "Products" 
               ("SellerID", "ProductName", "Price", "Quantity", "Description", "Status")
               VALUES ($1, $2, $3, $4, $5, $6)
               RETURNING "ProductID"''',
            seller_id,
            product_data.get('name'),
            product_data.get('price'),
            product_data.get('quantity', 0),
            product_data.get('description', ''),
            'active'
        )
        
        # إخطار البائع
        await broadcast_update(seller_id, {
            'type': 'product_added',
            'product_id': product_id,
            'product_name': product_data.get('name'),
            'timestamp': datetime.now().isoformat()
        })
        
        return {'product_id': product_id, 'success': True}

@app.put("/api/products/{product_id}")
async def update_product(product_id: int, data: dict):
    """تحديث المنتج"""
    async with db_pool.acquire() as conn:
        # الحصول على معرف البائع
        product = await conn.fetchrow(
            'SELECT "SellerID" FROM "Products" WHERE "ProductID" = $1',
            product_id
        )
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # التحديث
        await conn.execute(
            '''UPDATE "Products" 
               SET "ProductName" = $1, "Price" = $2, "Quantity" = $3, "UpdatedAt" = NOW()
               WHERE "ProductID" = $4''',
            data.get('name'),
            data.get('price'),
            data.get('quantity'),
            product_id
        )
        
        # إخطار البائع فقط بالمتغيرات
        await broadcast_update(product['SellerID'], {
            'type': 'product_updated',
            'product_id': product_id,
            'fields': {k: v for k, v in data.items() if v is not None},
            'timestamp': datetime.now().isoformat()
        })
        
        return {'success': True}

@app.delete("/api/products/{product_id}")
async def delete_product(product_id: int):
    """حذف المنتج"""
    async with db_pool.acquire() as conn:
        product = await conn.fetchrow(
            'SELECT "SellerID" FROM "Products" WHERE "ProductID" = $1',
            product_id
        )
        
        if not product:
            raise HTTPException(status_code=404)
        
        await conn.execute(
            'DELETE FROM "Products" WHERE "ProductID" = $1',
            product_id
        )
        
        # إخطار البائع
        await broadcast_update(product['SellerID'], {
            'type': 'product_deleted',
            'product_id': product_id,
            'timestamp': datetime.now().isoformat()
        })
        
        return {'success': True}

# ---- الفئات ----

@app.get("/api/sellers/{seller_id}/categories")
async def get_categories(seller_id: int):
    """الحصول على فئات البائع"""
    async with db_pool.acquire() as conn:
        categories = await conn.fetch(
            '''SELECT * FROM "Categories" 
               WHERE "SellerID" = $1 
               ORDER BY "CategoryName" ASC''',
            seller_id
        )
        return {
            "count": len(categories),
            "categories": [dict(c) for c in categories]
        }

@app.post("/api/sellers/{seller_id}/categories")
async def add_category(seller_id: int, category_data: dict):
    """إضافة فئة جديدة"""
    async with db_pool.acquire() as conn:
        category_id = await conn.fetchval(
            '''INSERT INTO "Categories" ("SellerID", "CategoryName")
               VALUES ($1, $2)
               RETURNING "CategoryID"''',
            seller_id,
            category_data.get('name')
        )
        
        await broadcast_update(seller_id, {
            'type': 'category_added',
            'category_id': category_id,
            'category_name': category_data.get('name'),
            'timestamp': datetime.now().isoformat()
        })
        
        return {'category_id': category_id, 'success': True}

# ---- الإحصائيات ----

@app.get("/api/sellers/{seller_id}/stats")
async def get_seller_stats(seller_id: int):
    """الحصول على إحصائيات البائع"""
    async with db_pool.acquire() as conn:
        # عدد الطلبات الجديدة
        new_orders = await conn.fetchval(
            '''SELECT COUNT(*) FROM "Orders" 
               WHERE "SellerID" = $1 AND "Status" = 'pending' ''',
            seller_id
        )
        
        # عدد الرسائل الجديدة
        new_messages = await conn.fetchval(
            '''SELECT COUNT(*) FROM "Messages" 
               WHERE "SellerID" = $1 AND "IsRead" = false''',
            seller_id
        )
        
        # إجمالي المبيعات
        total_revenue = await conn.fetchval(
            '''SELECT SUM(oi."Price" * oi."Quantity")
               FROM "Orders" o
               JOIN "OrderItems" oi ON o."OrderID" = oi."OrderID"
               WHERE o."SellerID" = $1 AND o."Status" = 'completed' ''',
            seller_id
        )
        
        # عدد المنتجات
        product_count = await conn.fetchval(
            'SELECT COUNT(*) FROM "Products" WHERE "SellerID" = $1',
            seller_id
        )
        
        return {
            'pending_orders': new_orders or 0,
            'unread_messages': new_messages or 0,
            'total_revenue': float(total_revenue) if total_revenue else 0.0,
            'total_products': product_count or 0
        }

# ============ مسارات الصحة ============

@app.get("/health")
async def health():
    """فحص صحة الخادم"""
    if db_pool is None:
        return {'status': 'unhealthy', 'message': 'Database not connected'}
    
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval('SELECT 1')
        return {
            'status': 'healthy',
            'database': 'connected',
            'active_sellers': len(active_connections)
        }
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}

@app.get("/api/status")
async def api_status():
    """حالة API"""
    return {
        'api_version': '1.0.0',
        'active_connections': len(active_connections),
        'timestamp': datetime.now().isoformat()
    }

# ============ تشغيل الخادم ============

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        log_level='info'
    )
```

---

## 🚀 الخطوة 3: تشغيل الخادم

```bash
# تشغيل محلي
python api_server.py

# أو استخدم uvicorn مباشرة
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📱 الخطوة 4: استخدام الـ API من التطبيق (Flutter)

```dart
// lib/services/api_service.dart

import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'package:web_socket_channel/web_socket_channel.dart';

class ApiService {
  static const String BASE_URL = 'http://localhost:8000';  // غيّر حسب الـ server
  static WebSocketChannel? _channel;
  static int? _sellerId;
  static StreamController<Map<String, dynamic>>? _updateStream;

  // ============ التهيئة ============

  static Future<void> init(int sellerId) async {
    _sellerId = sellerId;
    _updateStream = StreamController<Map<String, dynamic>>.broadcast();
    await _connectWebSocket();
  }

  static Future<void> _connectWebSocket() async {
    try {
      _channel = WebSocketChannel.connect(
        Uri.parse('ws://localhost:8000/ws/seller/$_sellerId'),
      );
      
      _channel!.stream.listen(
        (message) {
          final data = jsonDecode(message);
          _updateStream?.add(data);
          _handleUpdate(data);
        },
        onError: (error) => print('WebSocket error: $error'),
        onDone: () => print('WebSocket closed'),
      );
      
      print('✅ Connected to WebSocket');
    } catch (e) {
      print('❌ WebSocket connection failed: $e');
    }
  }

  static void _handleUpdate(Map<String, dynamic> update) {
    final type = update['type'];
    
    switch (type) {
      case 'new_order':
        print('📦 طلب جديد: #${update['order_id']}');
        // تحديث الـ UI
        break;
      case 'new_message':
        print('💬 رسالة جديدة');
        // تحديث الـ UI
        break;
      case 'product_updated':
        print('🔄 تحديث المنتج: #${update['product_id']}');
        // تحديث فقط المنتج المتغير
        break;
      case 'order_status_updated':
        print('✅ تحديث حالة الطلب');
        break;
    }
  }

  // ============ الرسائل والطلبات ============

  static Future<List<dynamic>> getMessages({
    int skip = 0,
    int limit = 50,
    bool unreadsOnly = false,
  }) async {
    try {
      final response = await http.get(
        Uri.parse(
          '$BASE_URL/api/sellers/$_sellerId/messages'
          '?skip=$skip&limit=$limit&unread_only=$unreadsOnly'
        ),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['messages'] ?? [];
      }
      throw Exception('Failed to load messages');
    } catch (e) {
      print('Error: $e');
      return [];
    }
  }

  static Future<List<dynamic>> getOrders({
    String? status,
    int skip = 0,
    int limit = 50,
  }) async {
    try {
      final uri = '$BASE_URL/api/sellers/$_sellerId/orders?skip=$skip&limit=$limit';
      final response = await http.get(
        Uri.parse(status != null ? '$uri&status=$status' : uri),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['orders'] ?? [];
      }
      throw Exception('Failed to load orders');
    } catch (e) {
      print('Error: $e');
      return [];
    }
  }

  static Future<bool> updateOrderStatus(int orderId, String newStatus) async {
    try {
      final response = await http.post(
        Uri.parse('$BASE_URL/api/orders/$orderId/status'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'new_status': newStatus}),
      );

      return response.statusCode == 200;
    } catch (e) {
      print('Error: $e');
      return false;
    }
  }

  // ============ المنتجات ============

  static Future<List<dynamic>> getProducts() async {
    try {
      final response = await http.get(
        Uri.parse('$BASE_URL/api/sellers/$_sellerId/products'),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['products'] ?? [];
      }
      return [];
    } catch (e) {
      print('Error: $e');
      return [];
    }
  }

  static Future<int?> addProduct({
    required String name,
    required double price,
    required int quantity,
    String? description,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$BASE_URL/api/sellers/$_sellerId/products'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'name': name,
          'price': price,
          'quantity': quantity,
          'description': description ?? '',
        }),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body)['product_id'];
      }
      return null;
    } catch (e) {
      print('Error: $e');
      return null;
    }
  }

  static Future<bool> updateProduct(
    int productId, {
    String? name,
    double? price,
    int? quantity,
  }) async {
    try {
      final response = await http.put(
        Uri.parse('$BASE_URL/api/products/$productId'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'name': name,
          'price': price,
          'quantity': quantity,
        }),
      );

      return response.statusCode == 200;
    } catch (e) {
      print('Error: $e');
      return false;
    }
  }

  // ============ الإحصائيات ============

  static Future<Map<String, dynamic>> getStats() async {
    try {
      final response = await http.get(
        Uri.parse('$BASE_URL/api/sellers/$_sellerId/stats'),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return {};
    } catch (e) {
      print('Error: $e');
      return {};
    }
  }

  // ============ البث (Streaming) ============

  static Stream<Map<String, dynamic>> get updateStream {
    return _updateStream?.stream ?? Stream.empty();
  }

  static void dispose() {
    _channel?.sink.close();
    _updateStream?.close();
  }
}
```

---

## 💡 الاستخدام في الشاشة

```dart
class SellerDashboard extends StatefulWidget {
  @override
  _SellerDashboardState createState() => _SellerDashboardState();
}

class _SellerDashboardState extends State<SellerDashboard> {
  late List<dynamic> orders = [];
  late List<dynamic> messages = [];
  late Map<String, dynamic> stats = {};

  @override
  void initState() {
    super.initState();
    
    // تهيئة API للبائع
    ApiService.init(getCurrentSellerId());
    
    // جلب البيانات
    _loadData();
    
    // الاستماع للتحديثات الفورية
    ApiService.updateStream.listen((update) {
      setState(() {
        // سيتم تحديث الـ UI تلقائياً
      });
    });
  }

  Future<void> _loadData() async {
    final ord = await ApiService.getOrders();
    final msg = await ApiService.getMessages();
    final st = await ApiService.getStats();
    
    setState(() {
      orders = ord;
      messages = msg;
      stats = st;
    });
  }

  @override
  void dispose() {
    ApiService.dispose();
    super.dispose();
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
            // الإحصائيات
            StatsCard(stats: stats),
            
            // الطلبات الجديدة
            OrdersList(orders: orders),
            
            // الرسائل
            MessagesList(messages: messages),
          ],
        ),
      ),
    );
  }
}
```

---

## 🔗 ربط bot.py بـ API (اختياري)

```python
# إضافة لـ bot.py عند إنشاء طلب جديد

import aiohttp

async def notify_seller_via_api(seller_id: int, order_data: dict):
    """إرسال إشعار للبائع عبر API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'http://localhost:8000/api/notify',  # إضافة endpoint في API
                json={
                    'seller_id': seller_id,
                    'type': 'new_order',
                    'data': order_data
                }
            ) as resp:
                if resp.status == 200:
                    print(f"✅ Seller {seller_id} notified via API")
    except Exception as e:
        print(f"Error notifying seller: {e}")

# في دالة create_order:
order_id = create_order(...)
await notify_seller_via_api(seller_id, {
    'order_id': order_id,
    'customer': customer_name,
    'items': items,
    'total': total
})
```

---

## 📊 اختبار الـ API

```bash
# 1. فحص الصحة
curl http://localhost:8000/health

# 2. الحصول على الرسائل
curl http://localhost:8000/api/sellers/1/messages

# 3. الحصول على الطلبات
curl http://localhost:8000/api/sellers/1/orders

# 4. إضافة منتج
curl -X POST http://localhost:8000/api/sellers/1/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "منتج جديد",
    "price": 10000,
    "quantity": 5,
    "description": "وصف المنتج"
  }'

# 5. تحديث حالة الطلب
curl -X POST http://localhost:8000/api/orders/1/status \
  -H "Content-Type: application/json" \
  -d '{"new_status": "completed"}'
```

---

## 🎯 النتيجة النهائية

بعد تطبيق هذا النموذج:
- ✅ API كاملة وتعمل بكفاءة
- ✅ تحديثات فورية عبر WebSocket
- ✅ تطبيق يعمل بدون Telegram
- ✅ بيانات محسّنة (فقط المتغيرات)
- ✅ قابل للتوسع والتحسن

**الخطوة التالية:** انسخ `api_server.py` وشغّله الآن! 🚀
