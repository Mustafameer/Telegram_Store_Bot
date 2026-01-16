"""
معالج Webhook للبوت
Webhook Handler
"""
import json
import logging
from flask import Flask, request, jsonify
from config import HOST, PORT, WEBHOOK_URL, MAINTENANCE_MODE
from bot import bot
from handlers import handle_message, handle_callback

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    """استقبال التحديثات من Telegram"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'ok': False, 'error': 'No data'}), 400
        
        # التحقق من IP
        ip = request.remote_addr or request.headers.get('CF-Connecting-IP', '0.0.0.0')
        
        if not bot.is_telegram_ip(ip):
            logger.warning(f"Invalid IP attempt: {ip}")
            return jsonify({'ok': False, 'error': 'Forbidden'}), 403
        
        logger.info(f"Received update: {json.dumps(data, indent=2)}")
        
        # معالجة التحديث
        if 'message' in data:
            handle_message(data['message'], data)
        
        elif 'callback_query' in data:
            handle_callback(data['callback_query'], data)
        
        return jsonify({'ok': True}), 200
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/status', methods=['GET'])
def status():
    """فحص حالة البوت"""
    return jsonify({
        'status': 'ok',
        'bot_id': bot.api.api_key.split(':')[0],
        'maintenance': MAINTENANCE_MODE
    })


@app.route('/test', methods=['GET'])
def test():
    """اختبار الاتصال"""
    try:
        me = bot.api.get_me()
        if me:
            return jsonify({
                'ok': True,
                'bot': me
            })
        else:
            return jsonify({
                'ok': False,
                'error': 'Failed to get bot info'
            }), 500
    
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@app.route('/set_webhook', methods=['POST'])
def set_webhook():
    """تعيين webhook"""
    try:
        url = request.json.get('url') or WEBHOOK_URL
        result = bot.api.set_webhook(url)
        
        if result:
            return jsonify({
                'ok': True,
                'result': 'Webhook set successfully'
            })
        else:
            return jsonify({
                'ok': False,
                'error': 'Failed to set webhook'
            }), 500
    
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@app.route('/get_webhook_info', methods=['GET'])
def get_webhook_info():
    """الحصول على معلومات webhook"""
    try:
        info = bot.api.get_webhook_info()
        return jsonify({
            'ok': True,
            'webhook_info': info
        })
    
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    logger.info(f"Starting bot server on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=False)
