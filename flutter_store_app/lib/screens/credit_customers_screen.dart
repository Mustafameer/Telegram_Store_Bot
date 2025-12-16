import 'package:flutter/material.dart';
import '../database/database_helper.dart';
import '../models/database_models.dart';
import 'package:intl/intl.dart' as intl;

class CreditCustomersScreen extends StatefulWidget {
  final int sellerId;
  const CreditCustomersScreen({super.key, required this.sellerId});

  @override
  State<CreditCustomersScreen> createState() => _CreditCustomersScreenState();
}

class _CreditCustomersScreenState extends State<CreditCustomersScreen> {
  late Future<List<CreditCustomer>> _customersFuture;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  void _refresh() {
    setState(() {
      _customersFuture = DatabaseHelper.instance.getCreditCustomers(widget.sellerId);
    });
  }

  Future<void> _addCustomer() async {
    final nameController = TextEditingController();
    final phoneController = TextEditingController();
    await showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('إضافة زبون آجل'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: nameController, decoration: const InputDecoration(labelText: 'الاسم الكامل')),
            const SizedBox(height: 8),
            TextField(controller: phoneController, decoration: const InputDecoration(labelText: 'رقم الهاتف')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
          FilledButton(
            onPressed: () async {
              if (nameController.text.isNotEmpty) {
                await DatabaseHelper.instance.addCreditCustomer(widget.sellerId, nameController.text, phoneController.text);
                if (mounted) {
                  Navigator.pop(context);
                  _refresh();
                }
              }
            },
            child: const Text('إضافة'),
          )
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('الزبائن الآجل')),
      floatingActionButton: FloatingActionButton(
        onPressed: _addCustomer,
        child: const Icon(Icons.person_add),
      ),
      body: FutureBuilder<List<CreditCustomer>>(
        future: _customersFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
          if (!snapshot.hasData || snapshot.data!.isEmpty) return const Center(child: Text('لا يوجد زبائن حالياً'));
          
          final customers = snapshot.data!;
          return ListView.builder(
            itemCount: customers.length,
            itemBuilder: (context, index) {
              final c = customers[index];
              return ListTile(
                leading: CircleAvatar(child: Text(c.fullName[0])),
                title: Text(c.fullName),
                subtitle: Text(c.phoneNumber ?? 'لا يوجد رقم'),
                trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                onTap: () {
                  Navigator.push(context, MaterialPageRoute(builder: (_) => CustomerStatementScreen(
                    customerId: c.customerId, 
                    customerName: c.fullName,
                    sellerId: widget.sellerId
                  )));
                },
              );
            },
          );
        },
      ),
    );
  }
}

class CustomerStatementScreen extends StatefulWidget {
  final int customerId;
  final String customerName;
  final int sellerId;

  const CustomerStatementScreen({
    super.key, 
    required this.customerId, 
    required this.customerName,
    required this.sellerId
  });

  @override
  State<CustomerStatementScreen> createState() => _CustomerStatementScreenState();
}

class _CustomerStatementScreenState extends State<CustomerStatementScreen> {
  late Future<List<CustomerCreditTransaction>> _transactionsFuture;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  void _refresh() {
    setState(() {
      _transactionsFuture = DatabaseHelper.instance.getCustomerTransactions(widget.customerId);
    });
  }

  Future<void> _addTransaction(String type) async {
    final amountController = TextEditingController();
    final descController = TextEditingController();
    
    final title = type == 'payment' ? 'تسجيل تسديد' : 'إضافة دين (شراء)';
    
    await showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(title),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: amountController, 
              decoration: const InputDecoration(labelText: 'المبلغ'),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 8),
            TextField(
              controller: descController, 
              decoration: const InputDecoration(labelText: 'ملاحظات / وصف'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
          FilledButton(
            onPressed: () async {
              final amount = double.tryParse(amountController.text);
              if (amount != null && amount > 0) {
                await DatabaseHelper.instance.addCreditTransaction(
                  customerId: widget.customerId,
                  sellerId: widget.sellerId,
                  transactionType: type,
                  amount: amount,
                  description: descController.text.isEmpty ? (type == 'payment' ? 'تسديد نقدي' : 'شراء آجل') : descController.text
                );
                if (mounted) {
                  Navigator.pop(context);
                  _refresh();
                }
              }
            },
            child: const Text('حفظ'),
          )
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('كشف حساب: ${widget.customerName}')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () => _addTransaction('payment'),
                    icon: const Icon(Icons.payment),
                    label: const Text('تسجيل تسديد'),
                    style: FilledButton.styleFrom(backgroundColor: Colors.green),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () => _addTransaction('credit'),
                    icon: const Icon(Icons.add_shopping_cart),
                    label: const Text('إضافة دين'),
                    style: FilledButton.styleFrom(backgroundColor: Colors.red),
                  ),
                ),
              ],
            ),
          ),
          const Divider(),
          Expanded(
            child: FutureBuilder<List<CustomerCreditTransaction>>(
              future: _transactionsFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
                
                final transactions = snapshot.data ?? [];
                
                // Calculate current balance (BalanceAfter of the latest transaction)
                double balance = 0;
                if (transactions.isNotEmpty) {
                   balance = transactions.first.balanceAfter ?? 0;
                }

                return Column(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(16),
                      color: Colors.blue.shade50,
                      width: double.infinity,
                      child: Text(
                        'الرصيد الحالي: ${intl.NumberFormat('#,###').format(balance)}',
                        style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.blue),
                        textAlign: TextAlign.center,
                      ),
                    ),
                    Expanded(
                      child: ListView.separated(
                        itemCount: transactions.length,
                        separatorBuilder: (_, __) => const Divider(height: 1),
                        itemBuilder: (context, index) {
                          final t = transactions[index];
                          final isPayment = t.transactionType == 'payment';
                          final color = isPayment ? Colors.green : Colors.red;
                          
                          return ListTile(
                            leading: Icon(isPayment ? Icons.arrow_downward : Icons.arrow_upward, color: color),
                            title: Text(t.description ?? ''),
                            subtitle: Text(t.transactionDate?.substring(0, 16).replaceFirst('T', ' ') ?? ''),
                            trailing: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              crossAxisAlignment: CrossAxisAlignment.end,
                              children: [
                                Text(
                                  '${isPayment ? '-' : '+'}${intl.NumberFormat('#,###').format(t.amount)}',
                                  style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 16),
                                ),
                                Text(
                                  'الرصيد: ${intl.NumberFormat('#,###').format(t.balanceAfter ?? 0)}',
                                  style: const TextStyle(fontSize: 12, color: Colors.grey),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
