import 'package:flutter/material.dart';
import 'package:postgres/postgres.dart';
import '../services/server_config.dart';
import '../services/sync_service.dart';

class ServerSettingsScreen extends StatefulWidget {
  const ServerSettingsScreen({super.key});

  @override
  State<ServerSettingsScreen> createState() => _ServerSettingsScreenState();
}

class _ServerSettingsScreenState extends State<ServerSettingsScreen> {
  final _formKey = GlobalKey<FormState>();
  final _hostController = TextEditingController();
  final _portController = TextEditingController();
  final _dbController = TextEditingController();
  final _userController = TextEditingController();
  final _passController = TextEditingController();
  bool _isLoading = false;
  bool _useSSL = false;
  String? _statusMessage;
  Color _statusColor = Colors.black;

  @override
  void initState() {
    super.initState();
    _loadCurrentConfig();
  }

  Future<void> _loadCurrentConfig() async {
    final config = await ServerConfig.getConfig();
    setState(() {
      _hostController.text = config['host'];
      _portController.text = config['port'].toString();
      _dbController.text = config['database'];
      _userController.text = config['username'];
      _passController.text = config['password'];
      _useSSL = config['ssl'];
    });
  }

  Future<void> _testConnection() async {
    if (!_formKey.currentState!.validate()) return;
    
    setState(() {
      _isLoading = true;
      _statusMessage = "جاري الاتصال...";
      _statusColor = Colors.blue;
    });

    Connection? conn;
    try {
      final host = _hostController.text.trim();
      final port = int.parse(_portController.text.trim());
      final db = _dbController.text.trim();
      final user = _userController.text.trim();
      final pass = _passController.text.trim();

      conn = await Connection.open(
        Endpoint(
          host: host,
          database: db,
          username: user,
          password: pass,
          port: port,
        ),
        settings: ConnectionSettings(sslMode: _useSSL ? SslMode.require : SslMode.disable),
      );

      setState(() {
        _statusMessage = "تم الاتصال بنجاح! ✅";
        _statusColor = Colors.green;
      });
    } catch (e) {
      setState(() {
        _statusMessage = "فشل الاتصال: $e";
        _statusColor = Colors.red;
      });
    } finally {
      await conn?.close();
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _saveSettings() async {
    if (!_formKey.currentState!.validate()) return;

    await ServerConfig.saveConfig(
      host: _hostController.text.trim(),
      port: int.parse(_portController.text.trim()),
      database: _dbController.text.trim(),
      username: _userController.text.trim(),
      password: _passController.text.trim(),
      ssl: _useSSL,
    );

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تم حفظ الإعدادات')));
      Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('إعدادات السرفر المحلي')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'أدخل بيانات السرفر (PostgreSQL) الموجود على الحاسوب',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 20),
              TextFormField(
                controller: _hostController,
                decoration: const InputDecoration(labelText: 'IP Address (Host)', border: OutlineInputBorder(), hintText: '192.168.1.X'),
                validator: (v) => v!.isEmpty ? 'مطلوب' : null,
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _portController,
                decoration: const InputDecoration(labelText: 'Port', border: OutlineInputBorder(), hintText: '5432'),
                keyboardType: TextInputType.number,
                validator: (v) => v!.isEmpty ? 'مطلوب' : null,
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _dbController,
                decoration: const InputDecoration(labelText: 'Database Name', border: OutlineInputBorder()),
                 validator: (v) => v!.isEmpty ? 'مطلوب' : null,
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _userController,
                decoration: const InputDecoration(labelText: 'Username', border: OutlineInputBorder()),
                 validator: (v) => v!.isEmpty ? 'مطلوب' : null,
              ),
               const SizedBox(height: 10),
              TextFormField(
                controller: _passController,
                decoration: const InputDecoration(labelText: 'Password', border: OutlineInputBorder()),
                obscureText: true,
                 validator: (v) => v!.isEmpty ? 'مطلوب' : null,
              ),
               const SizedBox(height: 10),
              TextFormField(
                controller: _passController,
                decoration: const InputDecoration(labelText: 'Password', border: OutlineInputBorder()),
                obscureText: true,
                 validator: (v) => v!.isEmpty ? 'مطلوب' : null,
              ),
              const SizedBox(height: 10),
              SwitchListTile(
                title: const Text("استخدام اتصال آمن (SSL)"),
                subtitle: const Text("قم بتفعيله عند الاتصال بـ Railway أو سرفر سحابي"),
                value: _useSSL,
                onChanged: (val) => setState(() => _useSSL = val),
              ),
              const SizedBox(height: 20),
              if (_statusMessage != null) ...[
                Text(_statusMessage!, style: TextStyle(color: _statusColor, fontWeight: FontWeight.bold), textAlign: TextAlign.center),
                const SizedBox(height: 20),
              ],
              Row(
                children: [
                   Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _isLoading ? null : _testConnection, 
                      icon: const Icon(Icons.network_check),
                      label: const Text('اختبار الاتصال')
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: _isLoading ? null : _saveSettings, 
                      icon: const Icon(Icons.save),
                      label: const Text('حفظ'),
                      style: ElevatedButton.styleFrom(backgroundColor: Colors.blue, foregroundColor: Colors.white),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              const Divider(),
              const Text("أدوات متقدمة", style: TextStyle(fontWeight: FontWeight.bold)),
              ListTile(
                title: const Text("رفع قاعدة البيانات الحالية"),
                subtitle: const Text("استخدم هذا الخيار عند الانتقال لسرفر جديد لنقل بياناتك الحالية إليه."),
                leading: const Icon(Icons.cloud_upload, color: Colors.orange),
                onTap: _isLoading ? null : () async {
                   final confirm = await showDialog<bool>(
                     context: context,
                     builder: (ctx) => AlertDialog(
                       title: const Text("تأكيد الرفع"),
                       content: const Text("سيتم رفع جميع البيانات من هذا الجهاز إلى السرفر المحدد.\nتأكد أن السرفر جديد أو فارغ لتجنب تكرار البيانات."),
                       actions: [
                         TextButton(onPressed: ()=>Navigator.pop(ctx, false), child: const Text("إلغاء")),
                         FilledButton(onPressed: ()=>Navigator.pop(ctx, true), child: const Text("بدء الرفع")),
                       ],
                     )
                   );
                   
                   if (confirm == true) {
                      setState(() {
                         _isLoading = true;
                         _statusMessage = "جاري رفع البيانات...";
                         _statusColor = Colors.blue;
                      });
                      
                      // Subscribe to stream temporarily
                      final sub = SyncService.instance.statusStream.listen((msg) {
                         if (mounted) setState(() => _statusMessage = msg);
                      });

                      await SyncService.instance.uploadFullDatabase();
                      
                      await sub.cancel();
                      setState(() => _isLoading = false);
                   }
                },
              )
            ],
          ),
        ),
      ),
    );
  }
}
