

import 'package:flutter/material.dart';
import '../database/database_helper.dart';
import 'home_screen.dart';
import 'store_detail_screen.dart';

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
          MaterialPageRoute(builder: (context) => const HomeScreen(isAdmin: true)),
        );
        return;
      }

      // 2. Check if Seller
      final seller = await DatabaseHelper.instance.getSellerByTelegramId(telegramId);
      if (seller != null) {
        if (!mounted) return;
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (context) => StoreDetailScreen(seller: seller, isSellerMode: true)),
        );
        return;
      }

      // 3. If neither (could be a user, but this app is for management)
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
    return Scaffold(
      body: Center(
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
    );
  }
}
