import 'dart:io';
import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../database/database_helper.dart';
import '../services/sync_service.dart';

class ExitService {
  static bool _isExiting = false;

  /// Starts the exit flow using a non-dismissible dialog.
  /// 1. Syncs with Cloud
  /// 2. Closes Database
  /// 3. Exits App
  static Future<void> startExitFlow(BuildContext context) async {
    if (_isExiting) return;
    _isExiting = true;

    // Show Blocking Dialog
    if (context.mounted) {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) {
          return PopScope(
            canPop: false,
            child: AlertDialog(
              title: const Row(
                children: [
                  CircularProgressIndicator(),
                  SizedBox(width: 16),
                  Text("جاري الإغلاق..."),
                ],
              ),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("يتم الآن مزامنة البيانات وإغلاق التطبيق."),
                  const SizedBox(height: 16),
                  StreamBuilder<String>(
                    stream: SyncService.instance.statusStream,
                    initialData: "تحضير...",
                    builder: (context, snapshot) {
                      return Text(snapshot.data ?? "...");
                    },
                  ),
                ],
              ),
            ),
          );
        },
      );
    }

    try {
      // 1. Sync
      print("🚪 ExitFlow: Starting Sync...");
      // We assume syncNow handles its own errors gracefully but throws if critical? 
      // Actually syncNow catches errors and adds to stream. 
      await SyncService.instance.syncNow();
      print("🚪 ExitFlow: Sync Completed.");

      // 2. Close DB
      print("🚪 ExitFlow: Closing Database...");
      await DatabaseHelper.instance.close();
      
      // Additional safety: give time for file locks to release
      await Future.delayed(const Duration(milliseconds: 500)); 

      // Note: Data folder is NOT deleted to preserve user data between sessions
      print("🚪 ExitFlow: Data folder preserved for next session.");

    } catch (e) {
      print("❌ ExitFlow Error: $e");
    } finally {
      print("👋 ExitFlow: Exiting App.");
      exit(0);
    }
  }
}
