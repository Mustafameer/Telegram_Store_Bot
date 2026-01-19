import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import '../models/notification_model.dart';

class NotificationService {
  static const String apiBase = 'http://localhost:5000/api';
  static const String remoteApiBase = 'https://telegramstorebot.railway.app/api';
  
  // Get API URL based on environment
  static Future<String> getApiUrl() async {
    // Try to detect if running on mobile or desktop
    try {
      // For now, assume we can reach the local API on desktop
      // and remote API on mobile
      // You might want to read this from SharedPreferences
      final testResponse = await http.get(
        Uri.parse('$apiBase/health'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 2));
      
      if (testResponse.statusCode == 200) {
        return apiBase;
      }
    } catch (e) {
      // Local API not available, use remote
    }
    
    return remoteApiBase;
  }
  
  /// احصل على الإشعارات للعميل
  /// 
  /// [customerId] معرف التليجرام للعميل
  /// [unreadOnly] هل تحضر الإشعارات غير المقروءة فقط (default: true)
  static Future<List<AppNotification>> getNotifications({
    required int customerId,
    bool unreadOnly = true,
  }) async {
    try {
      final apiUrl = await getApiUrl();
      
      final uri = Uri.parse('$apiUrl/notifications').replace(
        queryParameters: {
          'customer_id': customerId.toString(),
          'unread_only': unreadOnly.toString(),
        },
      );
      
      final response = await http.get(
        uri,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
      ).timeout(const Duration(seconds: 10));
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        if (data['success'] == true) {
          final List<dynamic> notificationsList = data['notifications'] ?? [];
          return notificationsList
              .map((json) => AppNotification.fromJson(json))
              .toList();
        } else {
          print('❌ Error from API: ${data['error']}');
          return [];
        }
      } else if (response.statusCode == 400) {
        print('❌ Bad request: ${response.body}');
        return [];
      } else if (response.statusCode == 500) {
        print('❌ Server error: ${response.body}');
        return [];
      } else {
        print('❌ Unexpected status code: ${response.statusCode}');
        print('Response: ${response.body}');
        return [];
      }
    } catch (e) {
      print('❌ Error fetching notifications: $e');
      return [];
    }
  }
  
  /// وضع علامة على إشعار كمقروء
  /// 
  /// [notificationId] معرف الإشعار
  static Future<bool> markAsRead(int notificationId) async {
    try {
      final apiUrl = await getApiUrl();
      
      final response = await http.post(
        Uri.parse('$apiUrl/notifications/$notificationId/read'),
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
      ).timeout(const Duration(seconds: 10));
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['success'] == true;
      } else {
        print('❌ Failed to mark notification as read: ${response.statusCode}');
        return false;
      }
    } catch (e) {
      print('❌ Error marking notification as read: $e');
      return false;
    }
  }
  
  /// احصل على الإشعارات غير المقروءة مع التحديث المستمر
  /// 
  /// [customerId] معرف التليجرام للعميل
  /// [refreshInterval] فترة التحديث بالثواني (default: 30 ثانية)
  static Stream<List<AppNotification>> streamUnreadNotifications({
    required int customerId,
    int refreshInterval = 30,
  }) {
    return Stream.periodic(
      Duration(seconds: refreshInterval),
      (_) => getNotifications(customerId: customerId, unreadOnly: true),
    ).asyncExpand((future) => future.asStream());
  }
}
