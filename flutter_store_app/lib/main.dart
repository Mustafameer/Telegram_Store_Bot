
import 'dart:io';
import 'package:path/path.dart' as p;
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:google_fonts/google_fonts.dart';
import 'services/sync_service.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';

// Conditional imports for desktop-only features
import 'package:sqflite_common_ffi/sqflite_ffi.dart' if (dart.library.html) 'dart:html' as sqflite_ffi;
import 'package:window_manager/window_manager.dart' if (dart.library.html) 'dart:html' as window_manager;

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize FFI (Desktop Only)
  if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
    sqflite_ffi.sqfliteFfiInit();
    sqflite_ffi.databaseFactory = sqflite_ffi.databaseFactoryFfi;
  
    try {
      await window_manager.windowManager.ensureInitialized();

      // Get screen size to calculate optimal window size
      final screenSize = await window_manager.windowManager.getSize();
      final screenWidth = screenSize.width;
      final screenHeight = screenSize.height;
      
      // Use 90% of screen size for a large but centered window
      final windowWidth = (screenWidth * 0.9).round();
      final windowHeight = (screenHeight * 0.9).round();
      
      window_manager.WindowOptions windowOptions = window_manager.WindowOptions(
        size: Size(windowWidth.toDouble(), windowHeight.toDouble()),
        minimumSize: const Size(800, 600),
        center: true,
        skipTaskbar: false,
        titleBarStyle: window_manager.TitleBarStyle.normal,
      );
      
      // Set window options and show centered
      await window_manager.windowManager.waitUntilReadyToShow(windowOptions, () async {
        await window_manager.windowManager.show();
      });
      
      // Ensure window is centered
      await window_manager.windowManager.center();
      await window_manager.windowManager.focus();
    } catch (e) {
      // window_manager not available (mobile), continue
      print("Window manager not available (mobile platform): $e");
    }
  }

  // Force create Images directory (Desktop Only)
  if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
    try {
       // Get executable directory
       final executablePath = Platform.resolvedExecutable;
       final exeDir = p.dirname(executablePath);
       final imgDir = Directory(p.join(exeDir, 'data', 'Images'));
       if (!await imgDir.exists()) {
         await imgDir.create(recursive: true);
         print("✅ Created Images Directory in main: ${imgDir.path}");
       }
    } catch (e) {
       print("❌ Failed to create Images directory in main: $e");
    }
  }

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
