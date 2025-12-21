
import 'dart:io';
import 'package:path/path.dart' as p;
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:window_manager/window_manager.dart';
import 'services/sync_service.dart';
import 'screens/login_screen.dart'; // Keep for now or remove if unused, but removing might break if other files ref it.
import 'screens/home_screen.dart'; // Add this

import 'package:sqflite_common_ffi/sqflite_ffi.dart'; // Add this import

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize FFI (Desktop Only)
  if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  
    await windowManager.ensureInitialized();

    WindowOptions windowOptions = const WindowOptions(
      size: Size(1280, 720),
      minimumSize: Size(800, 600),
      center: true,
      skipTaskbar: false,
      titleBarStyle: TitleBarStyle.normal,
    );
    
    // Force show immediately to avoid "ghost app"
    await windowManager.ensureInitialized();
    await windowManager.show(); 
    await windowManager.maximize();
    await windowManager.focus();
  }

  // Force create Images directory (Desktop Only path check for now to avoid premature crash, 
  // though main.dart shouldn't really be doing this IO manually if DB helper handles it.
  // We'll leave it conditional for Desktop for now or remove it.)
  if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
    try {
       final imgDir = Directory(p.join(Directory.current.path, 'data', 'Images'));
       if (!await imgDir.exists()) {
         await imgDir.create(recursive: true);
         print("✅ Created Images Directory in main: ${imgDir.path}");
       }
    } catch (e) {
       print("❌ Failed to create Images directory in main: $e");
    }
  }

  // Start Sync Service
  // SyncService.instance.startSyncTimer(); // Moved to HomeScreen to capture UI events 

  runApp(const MyApp());
}



class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Telegram Store Manager',
      debugShowCheckedModeBanner: false,
      locale: const Locale('ar', 'AE'),
      supportedLocales: const [
        Locale('ar', 'AE'),
        Locale('en', 'US'),
      ],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF2A9D8F), // Teal/Premium Green
          brightness: Brightness.light, 
        ),
        textTheme: GoogleFonts.cairoTextTheme(), // Arabic friendly font
        scaffoldBackgroundColor: const Color(0xFFF5F7FA),
        cardTheme: CardThemeData(
          elevation: 2,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          color: Colors.white,
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.white,
          elevation: 0,
          centerTitle: true,
          scrolledUnderElevation: 0,
        ),
      ),
      darkTheme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF2A9D8F),
          brightness: Brightness.dark,
        ),
        textTheme: GoogleFonts.cairoTextTheme(ThemeData.dark().textTheme),
        scaffoldBackgroundColor: const Color(0xFF121212),
        cardTheme: CardThemeData(
          elevation: 2,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          color: const Color(0xFF1E1E1E),
        ),
      ),
      themeMode: ThemeMode.system,
      home: const LoginScreen(),
    );
  }
}
