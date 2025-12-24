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
  /// 3. Deletes Data Folder
  /// 4. Exits App
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
                  const Text("يتم الآن مزامنة البيانات وحذف الملفات المحلية لضمان الأمان."),
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

      // 3. Delete Data Folder
      final dataPath = await DatabaseHelper.instance.getDbPath().then((path) => p.dirname(path));
      // Re-verify path to be safe (should be .../data)
      // Check if it's the expected 'data' folder
      if (dataPath.endsWith('data')) {
          final dir = Directory(dataPath);
          if (await dir.exists()) {
             print("🚪 ExitFlow: Deleting Data Directory: ${dir.path}");
             try {
               await dir.delete(recursive: true);
               print("🚪 ExitFlow: Data Deleted ✅");
             } catch (e) {
               print("❌ ExitFlow: Failed to delete data: $e");
               // Try deleting contents if folder locked?
             }
          }
      } else {
         print("⚠️ ExitFlow: DB path weird, skipping delete to be safe: $dataPath");
      }

    } catch (e) {
      print("❌ ExitFlow Error: $e");
    } finally {
      print("👋 ExitFlow: Exiting App.");
      exit(0);
    }
  }
}
