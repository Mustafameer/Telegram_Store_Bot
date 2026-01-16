"""
ترجمات البوت
Bot Translations
"""

LANGUAGES = {
    'ar': {
        # Messages
        'start': 'مرحباً بك في بوت شحن الهاتف المحمول 👋\nاختر ما تريد:',
        'menu': 'القائمة الرئيسية:',
        'request': 'طلب شحن',
        'account': 'حسابي',
        'history': 'السجل',
        'admin': 'لوحة التحكم 🔐',
        'start_admin': 'مرحباً مسؤول! اختر من الخيارات:',
        'notfounduser': 'عذراً، أنت غير مسجل في النظام.\nاتصل بالمسؤول.',
        'notfounduserowner': 'مستخدم جديد غير مسجل:\n👤 {}\n🆔 {}',
        
        # Companies
        'asiacell': 'Asiacell (آسيا سيل)',
        'zain': 'Zain (زين)',
        'korek': 'Korek (كورك)',
        'iraqsell': 'Iraqsell (عراق سيل)',
        'alkafil': 'Alkafil (الكفيل)',
        'creditrequest': 'طلب رصيد',
        'others': 'أخرى',
        'netzain': 'Net Zain (نت زين)',
        'netasiacell': 'Net Asiacell (نت آسيا)',
        
        # User Info
        'name': 'الاسم',
        'id': 'المعرف',
        'balance': 'الرصيد',
        'phone': 'رقم الهاتف',
        
        # Reports
        'profit': 'الأرباح اليومية',
        'reportUser_text': 'الإجمالي: {}\n{}',
        'statsPhotos': 'إحصائيات الصور',
        
        # Errors
        'error': 'حدث خطأ ما 😞',
        'error_invalid_input': 'إدخال غير صحيح',
        'under_maintenance': 'تحت الصيانة 🚫\n🚫 Under maintenance',
        'access_denied': 'الوصول مرفوض ❌',
        
        # Commands
        'choose_company': 'اختر الشركة:',
        'choose_amount': 'اختر المبلغ:',
        'enter_phone': 'أدخل رقم الهاتف:',
        'confirm_operation': 'تأكيد العملية:',
        'operation_success': 'تمت العملية بنجاح ✅',
        'operation_failed': 'فشلت العملية ❌',
        'back': '🔙 رجوع',
        'cancel': '❌ إلغاء',
        'confirm': '✅ تأكيد',
    },
    'en': {
        # Messages
        'start': 'Welcome to Mobile Recharge Bot 👋\nChoose what you want:',
        'menu': 'Main Menu:',
        'request': 'Request',
        'account': 'Account',
        'history': 'History',
        'admin': 'Admin Panel 🔐',
        'start_admin': 'Welcome Admin! Choose an option:',
        'notfounduser': 'Sorry, you are not registered.\nContact admin.',
        'notfounduserowner': 'New unregistered user:\n👤 {}\n🆔 {}',
        
        # Companies
        'asiacell': 'Asiacell',
        'zain': 'Zain',
        'korek': 'Korek',
        'iraqsell': 'Iraqsell',
        'alkafil': 'Alkafil',
        'creditrequest': 'Credit Request',
        'others': 'Others',
        'netzain': 'Net Zain',
        'netasiacell': 'Net Asiacell',
        
        # User Info
        'name': 'Name',
        'id': 'ID',
        'balance': 'Balance',
        'phone': 'Phone',
        
        # Reports
        'profit': 'Daily Profit',
        'reportUser_text': 'Total: {}\n{}',
        'statsPhotos': 'Photos Stats',
        
        # Errors
        'error': 'Something went wrong 😞',
        'error_invalid_input': 'Invalid input',
        'under_maintenance': 'Under maintenance 🚫',
        'access_denied': 'Access Denied ❌',
        
        # Commands
        'choose_company': 'Choose company:',
        'choose_amount': 'Choose amount:',
        'enter_phone': 'Enter phone number:',
        'confirm_operation': 'Confirm operation:',
        'operation_success': 'Operation successful ✅',
        'operation_failed': 'Operation failed ❌',
        'back': '🔙 Back',
        'cancel': '❌ Cancel',
        'confirm': '✅ Confirm',
    }
}


def get_text(key, language='ar', *args):
    """الحصول على نص مترجم (عربي فقط)"""
    # فرض استخدام اللغة العربية دائماً
    language = 'ar'
    texts = LANGUAGES.get(language, LANGUAGES['ar'])
    text = texts.get(key, key)
    
    # معالجة الـ placeholders
    if args:
        try:
            return text.format(*args)
        except:
            return text
    
    return text
