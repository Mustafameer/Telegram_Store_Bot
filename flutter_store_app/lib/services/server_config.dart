import 'package:shared_preferences/shared_preferences.dart';

class ServerConfig {
  static const String keyHost = 'server_host';
  static const String keyPort = 'server_port';
  static const String keyDbName = 'server_db';
  static const String keyUser = 'server_user';
  static const String keyPass = 'server_pass';

  // Defaults (can be localhost for desktop, but mobile needs IP)
  // Defaults (Railway Cloud Config)
  static const String defaultHost = 'switchback.proxy.rlwy.net';
  static const int defaultPort = 20266;
  static const String defaultDb = 'railway';
  static const String defaultUser = 'postgres';
  static const String defaultPass = 'bqcTJxNXLgwOftDoarrtmjmjYWurEIEh';

  static Future<void> saveConfig({
    required String host,
    required int port,
    required String database,
    required String username,
    required String password,
    bool ssl = false,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(keyHost, host);
    await prefs.setInt(keyPort, port);
    await prefs.setString(keyDbName, database);
    await prefs.setString(keyUser, username);
    await prefs.setString(keyPass, password);
    await prefs.setBool('server_ssl', ssl);
  }

  static Future<Map<String, dynamic>> getConfig() async {
    final prefs = await SharedPreferences.getInstance();
    return {
      'host': prefs.getString(keyHost) ?? defaultHost,
      'port': prefs.getInt(keyPort) ?? defaultPort,
      'database': prefs.getString(keyDbName) ?? defaultDb,
      'username': prefs.getString(keyUser) ?? defaultUser,
      'password': prefs.getString(keyPass) ?? defaultPass,
      'ssl': prefs.getBool('server_ssl') ?? true,
    };
  }
}
