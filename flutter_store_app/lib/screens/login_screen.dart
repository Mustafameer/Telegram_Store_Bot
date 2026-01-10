import 'dart:io';
import 'package:flutter/material.dart';
import '../database/database_helper.dart';
import '../models/database_models.dart';
import 'home_screen.dart';
import '../services/sync_service.dart';
import '../services/exit_service.dart';

// Conditional import for desktop-only features
import 'package:window_manager/window_manager.dart' if (dart.library.html) 'dart:html' as window_manager;

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final TextEditingController _idController = TextEditingController();
  bool _isLoading = false;
  String _errorMessage = '';

  // Hardcoded Admin ID from bot.py
  static const int adminId = 1041977029; 

  @override
  void initState() {
    super.initState();
    
    // Desktop-only window management
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      try {
        window_manager.windowManager.addListener(_WindowListener(this));
        _initWindowCloseHandler();
      } catch (e) {
        // window_manager not available, continue
        print("Window manager not available: $e");
      }
    }
    
    // Start Sync Immediately on Launch (Startup Sync)
    WidgetsBinding.instance.addPostFrameCallback((_) {
       SyncService.instance.startSyncTimer();
    });
  }
  
  Future<void> _initWindowCloseHandler() async {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      try {
        await window_manager.windowManager.setPreventClose(true);
      } catch (e) {
        // Ignore on mobile
      }
    }
  }

  @override
  void dispose() {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      try {
        window_manager.windowManager.removeListener(_WindowListener(this));
      } catch (e) {
        // Ignore on mobile
      }
    }
    super.dispose();
  }
  
  void _handleWindowClose() {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      try {
        ExitService.startExitFlow(context);
      } catch (e) {
        // Ignore on mobile
      }
    }
  }

  Future<void> _login() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    final input = _idController.text.trim();
    if (input.isEmpty) {
       setState(() {
        _isLoading = false;
        _errorMessage = 'الرجاء إدخال معرف التليجرام';
      });
      return;
    }

    final telegramId = int.tryParse(input);
    if (telegramId == null) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'معرف التليجرام يجب أن يكون أرقاماً فقط';
      });
      return;
    }

    try {
      // 1. Check if Admin
      if (telegramId == adminId) {
        if (!mounted) return;
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (context) => HomeScreen(
            isAdmin: true, 
            currentUserId: telegramId
          )),
        );
        return;
      }

      // 2. Check if Seller
      final seller = await DatabaseHelper.instance.getSellerByTelegramId(telegramId);
      if (seller != null) {
        if (!mounted) return;
        Navigator.of(context).pushReplacement(
           MaterialPageRoute(builder: (context) => HomeScreen(
             isAdmin: false, 
             isSeller: true,
             currentUserId: telegramId
           )),
        );
        return;
      }

      // 3. If neither
      setState(() {
        _errorMessage = 'لم يتم العثور على حساب بائع أو مسؤول بهذا المعرف';
      });

    } catch (e) {
      setState(() {
        _errorMessage = 'حدث خطأ: $e';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    Widget scaffold = Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            child: Container(
              constraints: const BoxConstraints(maxWidth: 400),
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(Icons.storefront, size: 80, color: Color(0xFF2A9D8F)),
                  const SizedBox(height: 32),
                  Text(
                    'تسجيل الدخول',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: const Color(0xFF264653)
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'الرجاء إدخال معرف تليجرام الخاص بك',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 32),
                  TextField(
                    controller: _idController,
                    decoration: InputDecoration(
                      labelText: 'Telegram ID',
                      prefixIcon: const Icon(Icons.perm_identity),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      errorText: _errorMessage.isNotEmpty ? _errorMessage : null,
                    ),
                    keyboardType: TextInputType.number,
                    onSubmitted: (_) => _login(),
                  ),
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: _isLoading ? null : _login,
                    style: FilledButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    child: _isLoading 
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) 
                        : const Text('دخول'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
      bottomNavigationBar: Container(
        padding: const EdgeInsets.all(12),
        color: Colors.grey.shade100,
        child: StreamBuilder<String>(
          stream: SyncService.instance.statusStream,
          initialData: "جاري الانتظار...",
          builder: (context, snapshot) {
            final status = snapshot.data ?? "";
            Color statusColor = Colors.grey;
            if (status.contains("⬇️")) statusColor = Colors.blue;
            if (status.contains("⬆️")) statusColor = Colors.green;
            if (status.contains("❌")) statusColor = Colors.red;
            if (status.contains("✅")) statusColor = Colors.teal;

            return Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (status.contains("Starting") || status.contains("Downloading") || status.contains("Pushing") || status.contains("Synchronizing"))
                   const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                const SizedBox(width: 8),
                Flexible(
                  child: Text(
                    status, 
                    style: TextStyle(color: statusColor, fontWeight: FontWeight.bold, fontSize: 12),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
    
    // Wrap with PopScope only on desktop
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      return PopScope(
        canPop: false,
        onPopInvokedWithResult: (didPop, result) async {
          if (didPop) return;
          try {
            await ExitService.startExitFlow(context);
          } catch (e) {
            // Ignore on mobile
          }
        },
        child: scaffold,
      );
    }
    
    return scaffold;
  }
}

// Helper class for window listener (desktop only)
class _WindowListener extends window_manager.WindowListener {
  final _LoginScreenState _state;
  _WindowListener(this._state);
  
  @override
  void onWindowClose() {
    _state._handleWindowClose();
  }
}
