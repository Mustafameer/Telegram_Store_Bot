
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

class TelegramService {
  static const String _botToken = "8562406465:AAHHaUMALVMjfgVKlAYNh8nziTwIeg5GDCs";
  static const String _baseUrl = "https://api.telegram.org/bot$_botToken";

  /// Send a text message to a transparent Telegram user
  static Future<bool> sendMessage(int chatId, String text) async {
    try {
      final url = Uri.parse('$_baseUrl/sendMessage');
      final response = await http.post(
        url,
        body: {
          'chat_id': chatId.toString(),
          'text': text,
          'parse_mode': 'Markdown',
        },
      );

      if (response.statusCode == 200) {
        // ignore: avoid_print
        print('Message sent to $chatId');
        return true;
      } else {
         // ignore: avoid_print
        print('Failed to send message: ${response.body}');
        return false;
      }
    } catch (e) {
       // ignore: avoid_print
      print('Error sending telegram message: $e');
      return false;
    }
  }

  /// Send a photo to a Telegram user
  static Future<bool> sendPhoto(int chatId, String imagePath, {String? caption}) async {
    try {
      final url = Uri.parse('$_baseUrl/sendPhoto');
      final file = File(imagePath);
      
      if (!await file.exists()) {
        print('Image file not found: $imagePath');
        return false;
      }

      final request = http.MultipartRequest('POST', url);
      request.fields['chat_id'] = chatId.toString();
      if (caption != null) {
        request.fields['caption'] = caption;
        request.fields['parse_mode'] = 'Markdown';
      }
      
      final imageFile = await file.readAsBytes();
      request.files.add(
        http.MultipartFile.fromBytes(
          'photo',
          imageFile,
          filename: file.path.split('/').last,
          contentType: MediaType('image', 'jpeg'),
        ),
      );

      final response = await request.send();
      final responseBody = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        print('Photo sent to $chatId');
        return true;
      } else {
        print('Failed to send photo: $responseBody');
        return false;
      }
    } catch (e) {
      print('Error sending telegram photo: $e');
      return false;
    }
  }

  /// Send multiple photos as a media group
  static Future<bool> sendMediaGroup(int chatId, List<String> imagePaths, {String? caption}) async {
    try {
      if (imagePaths.isEmpty) return false;
      
      // Telegram API allows max 10 media items per group
      final maxItems = imagePaths.length > 10 ? 10 : imagePaths.length;
      final imagesToSend = imagePaths.take(maxItems).toList();
      
      final url = Uri.parse('$_baseUrl/sendMediaGroup');
      final request = http.MultipartRequest('POST', url);
      request.fields['chat_id'] = chatId.toString();

      // Build media array
      final List<Map<String, String>> mediaList = [];
      for (int i = 0; i < imagesToSend.length; i++) {
        final file = File(imagesToSend[i]);
        if (await file.exists()) {
          final fileName = 'photo_$i';
          final imageFile = await file.readAsBytes();
          request.files.add(
            http.MultipartFile.fromBytes(
              fileName,
              imageFile,
              filename: file.path.split('/').last,
              contentType: MediaType('image', 'jpeg'),
            ),
          );
          
          mediaList.add({
            'type': 'photo',
            'media': 'attach://$fileName',
          });
        }
      }

      // Convert media list to JSON array string
      final mediaJsonStrings = mediaList.asMap().entries.map((entry) {
        final i = entry.key;
        final m = entry.value;
        final parts = <String>[];
        parts.add('"type":"${m['type']}"');
        parts.add('"media":"${m['media']}"');
        // Add caption only to first item
        if (i == 0 && caption != null) {
          // Escape caption for JSON
          final escapedCaption = caption.replaceAll('\\', '\\\\').replaceAll('"', '\\"').replaceAll('\n', '\\n');
          parts.add('"caption":"$escapedCaption"');
          parts.add('"parse_mode":"Markdown"');
        }
        return '{${parts.join(',')}}';
      }).toList();
      
      request.fields['media'] = '[${mediaJsonStrings.join(',')}]';

      final response = await request.send();
      final responseBody = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        print('Media group sent to $chatId (${imagesToSend.length} photos)');
        return true;
      } else {
        print('Failed to send media group: $responseBody');
        // Fallback: send photos individually
        print('📤 Falling back to individual photo sending...');
        for (int i = 0; i < imagesToSend.length; i++) {
          await sendPhoto(chatId, imagesToSend[i], caption: i == 0 ? caption : null);
          await Future.delayed(const Duration(milliseconds: 500)); // Rate limiting
        }
        return true;
      }
    } catch (e) {
      print('Error sending telegram media group: $e');
      // Fallback: send photos individually
      try {
        print('📤 Falling back to individual photo sending...');
        for (int i = 0; i < imagePaths.length; i++) {
          await sendPhoto(chatId, imagePaths[i], caption: i == 0 ? caption : null);
          await Future.delayed(const Duration(milliseconds: 500)); // Rate limiting
        }
        return true;
      } catch (fallbackError) {
        print('❌ Fallback also failed: $fallbackError');
        return false;
      }
    }
  }
}
