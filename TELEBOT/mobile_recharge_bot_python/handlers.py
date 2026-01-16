"""
معالجات الرسائل والأوامر
Message and Command Handlers
"""
import logging
import json
from bot import bot
from config import MAINTENANCE_MODE
from languages import get_text

logger = logging.getLogger(__name__)


def handle_message(message, update):
    """معالجة الرسائل النصية - عربي فقط"""
    try:
        chat_id = message['chat']['id']
        from_id = message['from']['id']
        text = message.get('text', '').strip()
        
        # الحصول على أو إنشاء المستخدم
        user = bot.get_or_create_user(message['from'])
        
        # فرض اللغة العربية
        bot.set_user_language(from_id, 'ar')
        
        # التحقق من وضع الصيانة
        if MAINTENANCE_MODE and not bot.is_authorized(from_id):
            bot.send_message(
                chat_id,
                get_text('under_maintenance', 'ar')
            )
            return
        
        # معالجة الأوامر
        if text.startswith('/'):
            handle_command(chat_id, from_id, text, user)
        else:
            handle_text(chat_id, from_id, text, user)
    
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)


def handle_callback(callback_query, update):
    """معالجة استعلامات callback - عربي فقط"""
    try:
        callback_id = callback_query['id']
        from_id = callback_query['from']['id']
        data = callback_query.get('data', '').strip()
        message = callback_query.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        message_id = message.get('message_id')
        
        # الحصول على المستخدم
        user = bot.db.get_user_by_id(from_id)
        
        # فرض اللغة العربية
        bot.set_user_language(from_id, 'ar')
        
        if not user:
            bot.api.answer_callback_query(
                callback_id,
                get_text('notfounduser', 'ar'),
                show_alert=True
            )
            return
        
        # معالجة البيانات
        logger.info(f"Callback data: {data} from user {from_id}")
        
        # سيتم إضافة معالجات محددة هنا حسب البيانات
        handle_callback_data(callback_id, chat_id, message_id, from_id, data, user)
    
    except Exception as e:
        logger.error(f"Error handling callback: {e}", exc_info=True)


def handle_command(chat_id, from_id, text, user):
    """معالجة الأوامس"""
    command = text.split()[0].lower()
    
    if command == '/start':
        handle_start(chat_id, from_id, user)
    
    elif command == '/account':
        handle_account(chat_id, from_id, user)
    
    elif command == '/history':
        handle_history(chat_id, from_id, user)
    
    elif command == '/admin':
        handle_admin(chat_id, from_id, user)
    
    elif command == '/users':
        handle_users(chat_id, from_id, user)
    
    elif command == '/stats':
        handle_stats(chat_id, from_id, user)
    
    elif command == '/profit':
        handle_profit(chat_id, from_id, user)
    
    else:
        bot.send_message(
            chat_id,
            f"❌ أمر غير معروف: {command}"
        )


def handle_start(chat_id, from_id, user):
    """معالجة أمر /start - عربي فقط"""
    
    # فرض اللغة العربية
    bot.set_user_language(from_id, 'ar')
    
    if bot.is_owner(from_id):
        text = "مرحباً مالك البوت! 👑\n\nاختر من الخيارات:"
        buttons = [
            {'text': '📊 الإحصائيات', 'callback_data': 'stats'},
            {'text': '💰 الأرباح', 'callback_data': 'profit'},
            {'text': '👥 المستخدمين', 'callback_data': 'users'},
            {'text': '⚙️ الإعدادات', 'callback_data': 'settings'},
        ]
    
    elif bot.is_admin(from_id):
        text = "مرحباً مسؤول! 🔐\n\nاختر من الخيارات:"
        buttons = [
            {'text': '📊 الإحصائيات', 'callback_data': 'stats'},
            {'text': '💰 الأرباح', 'callback_data': 'profit'},
            {'text': '👥 المستخدمين', 'callback_data': 'users'},
        ]
    
    else:
        text = "مرحباً بك في بوت شحن الهاتف المحمول! 👋\n\nاختر من الخيارات:"
        buttons = [
            {'text': '📱 شحن جديد', 'callback_data': 'recharge'},
            {'text': '💳 حسابي', 'callback_data': 'account'},
            {'text': '📋 السجل', 'callback_data': 'history'},
        ]
    
    keyboard = bot.build_inline_keyboard(buttons)
    bot.send_message(chat_id, text, reply_markup=keyboard)
    
    # تسجيل الإجراء
    bot.log_action(user['id'], 'start_command', {'chat_id': chat_id})


def handle_account(chat_id, from_id, user):
    """معالجة أمر /account"""
    text = f"""
💳 حسابك:

👤 الاسم: {user.get('first_name', '')} {user.get('last_name', '')}
🆔 المعرف: {user['from_id']}
💰 الرصيد: {user.get('balance', 0)} IQD
✅ الحالة: {'نشط ✅' if user.get('status') else 'معطل ❌'}
📅 تاريخ التسجيل: {user.get('created_at', 'N/A')}
    """
    bot.send_message(chat_id, text)


def handle_history(chat_id, from_id, user):
    """معالجة أمر /history"""
    transactions = bot.get_user_transactions(user['id'], limit=10)
    
    if not transactions:
        bot.send_message(chat_id, "لا توجد عمليات سابقة 📭")
        return
    
    text = "📋 سجل العمليات:\n\n"
    
    for t in transactions:
        text += f"""
🏢 الشركة: {t['company']}
📞 الرقم: {t['phone_number']}
💰 المبلغ: {t['amount']} IQD
📱 الشحنة: {t['charge']}
✅ الحالة: {t['status']}
📅 التاريخ: {t['created_at']}
───────────────────
        """
    
    bot.send_message(chat_id, text)


def handle_admin(chat_id, from_id, user):
    """معالجة أمر /admin"""
    if not bot.is_authorized(from_id):
        bot.send_message(chat_id, get_text('access_denied'))
        return
    
    text = "🔐 لوحة تحكم المسؤول:\n\n"
    buttons = [
        {'text': '📊 الإحصائيات', 'callback_data': 'admin_stats'},
        {'text': '💰 الأرباح', 'callback_data': 'admin_profit'},
        {'text': '👥 المستخدمين', 'callback_data': 'admin_users'},
        {'text': '📝 السجلات', 'callback_data': 'admin_logs'},
    ]
    
    keyboard = bot.build_inline_keyboard(buttons)
    bot.send_message(chat_id, text, reply_markup=keyboard)


def handle_users(chat_id, from_id, user):
    """معالجة أمر /users"""
    if not bot.is_authorized(from_id):
        bot.send_message(chat_id, get_text('access_denied'))
        return
    
    all_users = bot.db.get_all_users()
    text = f"👥 عدد المستخدمين: {len(all_users)}\n\n"
    
    for u in all_users[:10]:  # عرض أول 10
        text += f"👤 {u['first_name']} {u['last_name']} - ID: {u['from_id']}\n"
    
    if len(all_users) > 10:
        text += f"\n... و {len(all_users) - 10} مستخدم آخر"
    
    bot.send_message(chat_id, text)


def handle_stats(chat_id, from_id, user):
    """معالجة أمر /stats"""
    if not bot.is_authorized(from_id):
        bot.send_message(chat_id, get_text('access_denied'))
        return
    
    all_users = bot.db.get_all_users()
    text = f"""
📊 إحصائيات البوت:

👥 عدد المستخدمين: {len(all_users)}
✅ المستخدمين النشطين: {sum(1 for u in all_users if u['status'])}
❌ المستخدمين المعطلين: {sum(1 for u in all_users if not u['status'])}
    """
    
    bot.send_message(chat_id, text)


def handle_profit(chat_id, from_id, user):
    """معالجة أمر /profit"""
    if not bot.is_authorized(from_id):
        bot.send_message(chat_id, get_text('access_denied'))
        return
    
    profit = bot.get_profit()
    text = "💰 الأرباح الحالية:\n\n"
    
    total = 0
    for company, amount in profit.items():
        text += f"{bot.get_company_name(company)}: {amount} IQD\n"
        total += amount
    
    text += f"\n💵 الإجمالي: {total} IQD"
    
    bot.send_message(chat_id, text)


def handle_text(chat_id, from_id, text, user):
    """معالجة النصوص العادية"""
    # يتم معالجة النصوص حسب حالة المستخدم
    state, param = bot.get_user_state(user['id'])
    
    if not state:
        bot.send_message(chat_id, "❓ لم أفهم رسالتك.\nاستخدم /start للقائمة الرئيسية")
    else:
        logger.info(f"User {from_id} state: {state}, text: {text}")
        # معالجة حسب الحالة
        handle_state_text(chat_id, from_id, state, param, text, user)


def handle_callback_data(callback_id, chat_id, message_id, from_id, data, user):
    """معالجة بيانات callback"""
    
    if data == 'recharge':
        # بدء عملية شحن جديدة
        companies = bot.get_companies()
        buttons = [
            {'text': bot.get_company_name(comp), 'callback_data': f'comp_{comp}'}
            for comp in companies
        ]
        
        keyboard = bot.build_row_keyboard(buttons, cols=2)
        bot.edit_message(
            chat_id, message_id,
            "📱 اختر الشركة:",
            reply_markup=keyboard
        )
        
        bot.set_user_state(user['id'], 'choosing_company')
    
    elif data == 'account':
        handle_account(chat_id, from_id, user)
        bot.answer_callback(callback_id, "معلومات حسابك", show_alert=False)
    
    elif data == 'history':
        handle_history(chat_id, from_id, user)
        bot.answer_callback(callback_id, "سجل العمليات", show_alert=False)
    
    elif data.startswith('comp_'):
        # اختيار شركة
        company = data.replace('comp_', '')
        charges = bot.get_charges()
        
        buttons = [
            {'text': str(c), 'callback_data': f'charge_{c}'}
            for c in charges
        ]
        
        keyboard = bot.build_row_keyboard(buttons, cols=4)
        bot.edit_message(
            chat_id, message_id,
            f"💰 اختر المبلغ ({bot.get_company_name(company)}):",
            reply_markup=keyboard
        )
        
        bot.set_user_state(user['id'], 'choosing_charge', {'company': company})
    
    elif data.startswith('charge_'):
        # اختيار المبلغ
        charge = int(data.replace('charge_', ''))
        state, param = bot.get_user_state(user['id'])
        company = param.get('company', '')
        
        bot.edit_message(
            chat_id, message_id,
            f"📞 أدخل رقم الهاتف:\n(الشركة: {bot.get_company_name(company)}, المبلغ: {charge})"
        )
        
        bot.set_user_state(
            user['id'], 'entering_phone',
            {'company': company, 'charge': charge}
        )
    
    elif data == 'admin_stats':
        handle_stats(chat_id, from_id, user)
    
    elif data == 'admin_profit':
        handle_profit(chat_id, from_id, user)
    
    elif data == 'admin_users':
        handle_users(chat_id, from_id, user)
    
    bot.answer_callback(callback_id)


def handle_state_text(chat_id, from_id, state, param, text, user):
    """معالجة النصوص حسب الحالة"""
    
    if state == 'entering_phone':
        # التحقق من رقم الهاتف
        company = param.get('company', '')
        charge = param.get('charge', 0)
        
        # التحقق البسيط من الرقم
        if not text.isdigit() or len(text) < 10:
            bot.send_message(chat_id, "❌ رقم الهاتف غير صحيح.\nأدخل رقماً صحيحاً:")
            return
        
        # تأكيد العملية
        text_confirm = f"""
✅ تأكيد العملية:

🏢 الشركة: {bot.get_company_name(company)}
📞 الرقم: {text}
💰 المبلغ: {charge} IQD

اضغط تأكيد للمتابعة:
        """
        
        buttons = [
            {'text': '✅ تأكيد', 'callback_data': f'confirm_recharge'},
            {'text': '❌ إلغاء', 'callback_data': 'cancel'},
        ]
        
        keyboard = bot.build_inline_keyboard(buttons)
        bot.send_message(chat_id, text_confirm, reply_markup=keyboard)
        
        bot.set_user_state(
            user['id'], 'confirming_recharge',
            {
                'company': company,
                'phone': text,
                'charge': charge
            }
        )
    
    else:
        bot.send_message(chat_id, "❓ لم أفهم رسالتك.")
