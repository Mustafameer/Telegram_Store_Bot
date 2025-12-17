
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:window_manager/window_manager.dart';
import 'services/sync_service.dart';
import 'screens/login_screen.dart';

import 'package:sqflite_common_ffi/sqflite_ffi.dart'; // Add this import

void main() async {
  // Initialize FFI
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;
  
  // Force create Images directory
  try {
     final imgDir = Directory(r'C:\Users\Hp\Desktop\TelegramStoreBot\data\Images');
     if (!await imgDir.exists()) {
       await imgDir.create(recursive: true);
       print("✅ Created Images Directory in main: ${imgDir.path}");
     }
  } catch (e) {
     print("❌ Failed to create Images directory in main: $e");
  }

  WidgetsFlutterBinding.ensureInitialized();
  await windowManager.ensureInitialized();

  // Start Sync Service MOVED to Login/Home Screen to show UI progress
  // SyncService.instance.startSyncTimer();

  WindowOptions windowOptions = const WindowOptions(
    size: Size(1280, 720),
    center: true,
    backgroundColor: Colors.transparent,
    skipTaskbar: false,
    titleBarStyle: TitleBarStyle.normal,
  );
  
  windowManager.waitUntilReadyToShow(windowOptions, () async {
    await windowManager.show();
    await windowManager.maximize();
    await windowManager.focus();
    await windowManager.setPreventClose(true); // Prevent default close to handle sync
  });

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
      builder: (context, child) {
        return WindowSyncManager(child: child!);
      },
      home: const LoginScreen(),
    );
  }
}

class WindowSyncManager extends StatefulWidget {
  final Widget child;
  const WindowSyncManager({super.key, required this.child});

  @override
  State<WindowSyncManager> createState() => _WindowSyncManagerState();
}

class _WindowSyncManagerState extends State<WindowSyncManager> with WindowListener {
  @override
  void initState() {
    super.initState();
    windowManager.addListener(this);
  }

  @override
  void dispose() {
    windowManager.removeListener(this);
    super.dispose();
  }

  @override
  void onWindowClose() async {
    // Show Sync Dialog
    bool isSyncing = true;
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Row(children: [
           CircularProgressIndicator(), 
           SizedBox(width: 16),
           Text("جاري المزامنة قبل الخروج...")
        ]),
        content: const Text("يرجى الانتظار حتى يتم رفع التغييرات للسحابة."),
      ),
    );

    try {
      // Run Sync
      await SyncService.instance.syncNow();
    } catch (e) {
      print("Exit Sync Failed: $e");
    } finally {
      // Close window
      await windowManager.destroy();
    }
  }

  @override
  Widget build(BuildContext context) {
    return widget.child;
  }
}
