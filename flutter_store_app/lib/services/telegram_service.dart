
import 'package:http/http.dart' as http;

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
}
