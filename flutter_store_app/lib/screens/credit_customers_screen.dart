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
    print('📱 CreditCustomersScreen initialized for seller: ${widget.sellerId}');
    _refresh();
  }

  void _refresh() {
    print('🔄 Refreshing credit customers list for seller: ${widget.sellerId}');
    setState(() {
      _customersFuture = DatabaseHelper.instance.getCreditCustomers(widget.sellerId);
    });
  }

  Future<void> _addCustomer() async {
    final nameController = TextEditingController();
    final telegramIdController = TextEditingController();
    await showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('إضافة زبون آجل'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: nameController, decoration: const InputDecoration(labelText: 'الاسم الكامل')),
            const SizedBox(height: 8),
            TextField(controller: telegramIdController, decoration: const InputDecoration(labelText: 'آيدي التلكرام'), keyboardType: TextInputType.number),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
          FilledButton(
            onPressed: () async {
              if (nameController.text.isNotEmpty) {
                final telegramId = telegramIdController.text.isNotEmpty ? int.tryParse(telegramIdController.text) : null;
                await DatabaseHelper.instance.addCreditCustomer(widget.sellerId, nameController.text, '', telegramId: telegramId);
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

  Future<void> _editCustomer(CreditCustomer customer) async {
    final nameController = TextEditingController(text: customer.fullName);
    final telegramIdController = TextEditingController(text: customer.telegramId?.toString() ?? '');
    
    await showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('تعديل زبون آجل'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: nameController, decoration: const InputDecoration(labelText: 'الاسم الكامل')),
            const SizedBox(height: 8),
            TextField(controller: telegramIdController, decoration: const InputDecoration(labelText: 'آيدي التلكرام'), keyboardType: TextInputType.number),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
          FilledButton(
            onPressed: () async {
              if (nameController.text.isNotEmpty) {
                await DatabaseHelper.instance.updateCreditCustomer(
                  customer.customerId,
                  widget.sellerId,
                  nameController.text,
                  null,
                );
                if (mounted) {
                  Navigator.pop(context);
                  _refresh();
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('تم التعديل بنجاح')),
                  );
                }
              }
            },
            child: const Text('حفظ'),
          )
        ],
      ),
    );
  }

  Future<void> _deleteCustomer(CreditCustomer customer) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: Text('هل أنت متأكد من حذف الزبون "${customer.fullName}"؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('إلغاء'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('حذف'),
          ),
        ],
      ),
    );

    if (confirm == true) {
      try {
        await DatabaseHelper.instance.deleteCreditCustomer(customer.customerId, widget.sellerId);
        if (mounted) {
          _refresh();
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('تم الحذف بنجاح')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('خطأ في الحذف: $e')),
          );
        }
      }
    }
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
                subtitle: Text(c.telegramId != null ? 'آيدي: ${c.telegramId}' : 'بدون آيدي تلكرام'),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.edit, color: Colors.blue),
                      onPressed: () => _editCustomer(c),
                      tooltip: 'تعديل',
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete, color: Colors.red),
                      onPressed: () => _deleteCustomer(c),
                      tooltip: 'حذف',
                    ),
                    IconButton(
                      icon: const Icon(Icons.arrow_forward_ios, size: 16),
                      onPressed: () {
                        Navigator.push(context, MaterialPageRoute(builder: (_) => CustomerStatementScreen(
                          customerId: c.customerId, 
                          customerName: c.fullName,
                          sellerId: widget.sellerId
                        )));
                      },
                      tooltip: 'كشف الحساب',
                    ),
                  ],
                ),
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

  Future<void> _editTransaction(CustomerCreditTransaction transaction) async {
    final amountController = TextEditingController(text: transaction.amount.toString());
    final descController = TextEditingController(text: transaction.description ?? '');
    final typeController = transaction.transactionType;
    
    await showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('تعديل المعاملة'),
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
            const SizedBox(height: 8),
            Text(
              'النوع: ${typeController == 'payment' ? 'تسديد' : 'شراء آجل'}',
              style: const TextStyle(color: Colors.grey, fontSize: 14),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
          FilledButton(
            onPressed: () async {
              final amount = double.tryParse(amountController.text);
              if (amount != null && amount > 0) {
                double balanceBefore = transaction.balanceBefore ?? 0;
                double balanceAfter = balanceBefore;
                
                if (typeController == 'credit') {
                  balanceAfter = balanceBefore + amount;
                } else if (typeController == 'payment') {
                  balanceAfter = balanceBefore - amount;
                }
                
                final success = await DatabaseHelper.instance.updateCreditTransaction(
                  creditId: transaction.creditId,
                  transactionType: typeController,
                  amount: amount,
                  description: descController.text.isEmpty ? (typeController == 'payment' ? 'تسديد نقدي' : 'شراء آجل') : descController.text,
                  balanceBefore: balanceBefore,
                  balanceAfter: balanceAfter,
                );
                
                if (mounted) {
                  Navigator.pop(context);
                  if (success) {
                    _refresh();
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('تم التعديل بنجاح')),
                    );
                  } else {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('فشل التعديل')),
                    );
                  }
                }
              }
            },
            child: const Text('حفظ'),
          )
        ],
      ),
    );
  }

  Future<void> _deleteTransaction(CustomerCreditTransaction transaction) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: Text(
          'هل أنت متأكد من حذف هذه المعاملة؟\n${transaction.description}\n${intl.NumberFormat('#,###').format(transaction.amount)} دينار'
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('إلغاء'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('حذف'),
          ),
        ],
      ),
    );

    if (confirm == true) {
      final success = await DatabaseHelper.instance.deleteCreditTransaction(transaction.creditId);
      if (mounted) {
        if (success) {
          _refresh();
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('تم الحذف بنجاح')),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('فشل الحذف')),
          );
        }
      }
    }
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
                
                double balance = 0;
                if (transactions.isNotEmpty) {
                  final latestTransaction = transactions.first;
                  balance = latestTransaction.balanceAfter ?? 0;
                  print('💰 الرصيد من آخر معاملة: $balance');
                }

                return Column(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(16),
                      color: balance >= 0 ? Colors.green.shade50 : Colors.red.shade50,
                      width: double.infinity,
                      child: Column(
                        children: [
                          const Text(
                            'الرصيد الحالي',
                            style: TextStyle(fontSize: 14, color: Colors.grey),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${intl.NumberFormat('#,###').format(balance)}',
                            style: TextStyle(
                              fontSize: 28, 
                              fontWeight: FontWeight.bold, 
                              color: balance >= 0 ? Colors.green : Colors.red
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            balance >= 0 ? 'للزبون حساب دائن' : 'الزبون مدين',
                            style: TextStyle(
                              fontSize: 12, 
                              color: balance >= 0 ? Colors.green : Colors.red
                            ),
                          ),
                        ],
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
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              mainAxisAlignment: MainAxisAlignment.end,
                              children: [
                                Flexible(
                                  child: Padding(
                                    padding: const EdgeInsets.only(right: 8.0),
                                    child: Column(
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      crossAxisAlignment: CrossAxisAlignment.end,
                                      children: [
                                        Text(
                                          '${isPayment ? '-' : '+'}${intl.NumberFormat('###').format(t.amount)}',
                                          style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 13),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                        Text(
                                          'ر: ${intl.NumberFormat('###').format(t.balanceAfter ?? 0)}',
                                          style: const TextStyle(fontSize: 10, color: Colors.grey),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                                SizedBox(
                                  width: 48,
                                  height: 48,
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      InkWell(
                                        onTap: () => _editTransaction(t),
                                        child: const Icon(Icons.edit, size: 16, color: Colors.blue),
                                      ),
                                      InkWell(
                                        onTap: () => _deleteTransaction(t),
                                        child: const Icon(Icons.delete, size: 16, color: Colors.red),
                                      ),
                                    ],
                                  ),
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
