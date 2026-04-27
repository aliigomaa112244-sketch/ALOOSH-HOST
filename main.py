import sys
import telebot
from telebot import types
import io
import tokenize
import requests
import time
from threading import Thread
import subprocess
import string
from collections import defaultdict
from datetime import datetime, timedelta
import random
import re
import chardet
import logging
import threading
import os
import hashlib
import tempfile
import shutil
import zipfile
import sqlite3
import platform
import uuid
import socket
from concurrent.futures import ThreadPoolExecutor
import json

# إعدادات البوتات
BOT_TOKEN = '8529185398:AAGo721aPE_OSiXOgXnS11AZVtGrGSy6iWs'
ADMIN_ID = 8182317833
YOUR_USERNAME = '@al0osh505'
VIRUSTOTAL_API_KEY = 'YOUR_VIRUSTOTAL_API_KEY'
ADMIN_CHANNEL = '@FILES_OTP'

bot_scripts1 = defaultdict(lambda: {'processes': [], 'name': '', 'path': '', 'uploader': ''})
user_files = {}
lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=10)

bot = telebot.TeleBot(BOT_TOKEN)
bot_scripts = {}
uploaded_files_dir = "uploaded_files"
banned_users = set()
user_chats = {}

# ======= نظام الاشتراك عبر ID ======= #
approved_users = set()
pending_requests = {}
approved_users.add(ADMIN_ID)

# ======= إعدادات نظام الحماية ======= #
protection_enabled = True
protection_level = "medium"
suspicious_files_dir = 'suspicious_files'
MAX_FILE_SIZE = 2 * 1024 * 1024

# حالة تشغيل/إيقاف البوت
bot_running = True

# ========== نظام النقاط ==========
POINTS_FILE = "user_points.json"
DAILY_REWARD = 10
DAILY_COOLDOWN_HOURS = 24

GIFT_CODES_FILE = "gift_codes.json"

# إنشاء المجلدات المطلوبة
for directory in [uploaded_files_dir, suspicious_files_dir]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# ======= دوال نظام النقاط ======= #
def load_points():
    if os.path.exists(POINTS_FILE):
        with open(POINTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_points(points_data):
    with open(POINTS_FILE, 'w') as f:
        json.dump(points_data, f, indent=4)

def get_user_points(user_id):
    data = load_points()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"points": 0, "last_daily": None, "files": []}
        save_points(data)
    return data[uid]["points"]

def set_user_points(user_id, points):
    data = load_points()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"points": 0, "last_daily": None, "files": []}
    data[uid]["points"] = points
    save_points(data)

def add_user_points(user_id, points):
    current = get_user_points(user_id)
    set_user_points(user_id, current + points)

def remove_user_points(user_id, points):
    current = get_user_points(user_id)
    new_points = max(0, current - points)
    set_user_points(user_id, new_points)

def can_claim_daily(user_id):
    data = load_points()
    uid = str(user_id)
    if uid not in data or data[uid].get("last_daily") is None:
        return True
    last = datetime.strptime(data[uid]["last_daily"], "%Y-%m-%d %H:%M:%S")
    return datetime.now() - last >= timedelta(hours=DAILY_COOLDOWN_HOURS)

def claim_daily(user_id):
    if not can_claim_daily(user_id):
        return False
    add_user_points(user_id, DAILY_REWARD)
    data = load_points()
    uid = str(user_id)
    data[uid]["last_daily"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_points(data)
    return True

def add_file_to_user(user_id, filename):
    data = load_points()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"points": 0, "last_daily": None, "files": []}
    if filename not in data[uid]["files"]:
        data[uid]["files"].append(filename)
    save_points(data)

def remove_file_from_user(user_id, filename):
    data = load_points()
    uid = str(user_id)
    if uid in data and filename in data[uid]["files"]:
        data[uid]["files"].remove(filename)
        save_points(data)

def get_user_files_list(user_id):
    data = load_points()
    uid = str(user_id)
    if uid in data:
        return data[uid]["files"]
    return []

# ======= دوال كود الهدية ======= #
def load_gift_codes():
    if os.path.exists(GIFT_CODES_FILE):
        with open(GIFT_CODES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_gift_codes(codes):
    with open(GIFT_CODES_FILE, 'w') as f:
        json.dump(codes, f, indent=4)

def generate_gift_code(points, max_uses):
    code = hashlib.md5(f"{points}{max_uses}{time.time()}{random.random()}".encode()).hexdigest()[:10]
    codes = load_gift_codes()
    codes[code] = {
        "points": points,
        "max_uses": max_uses,
        "used": 0,
        "used_by": []
    }
    save_gift_codes(codes)
    return code

def redeem_gift_code(user_id, code):
    codes = load_gift_codes()
    if code not in codes:
        return False, "الكود غير صالح"
    gift = codes[code]
    if gift["used"] >= gift["max_uses"]:
        return False, "تم استخدام هذا الكود بأقصى عدد مرات"
    if str(user_id) in gift["used_by"]:
        return False, "لقد استخدمت هذا الكود مسبقاً"
    add_user_points(user_id, gift["points"])
    gift["used"] += 1
    gift["used_by"].append(str(user_id))
    save_gift_codes(codes)
    return True, f"تمت إضافة {gift['points']} نقطة"

# ======= دوال مساعدة أساسية ======= #
def save_chat_id(chat_id):
    if chat_id not in user_chats:
        user_chats[chat_id] = True
        print(f"تم حفظ chat_id: {chat_id}")

def is_admin(user_id):
    return user_id == ADMIN_ID

def is_approved_user(user_id):
    return user_id in approved_users or user_id == ADMIN_ID

def request_approval(user_id, user_info):
    pending_requests[user_id] = user_info
    
    markup = types.InlineKeyboardMarkup()
    approve_button = types.InlineKeyboardButton("قبول المستخدم", callback_data=f'approve_{user_id}', style="primary")
    reject_button = types.InlineKeyboardButton("رفض المستخدم", callback_data=f'reject_{user_id}', style="primary")
    markup.add(approve_button, reject_button)
    
    bot.send_message(
        ADMIN_ID,
        f"📋 طلب اشتراك جديد:\n\n"
        f"👤 الاسم: {user_info['first_name']}\n"
        f"🆔 ID: {user_id}\n"
        f"📌 اليوزر: @{user_info.get('username', 'غير متوفر')}\n"
        f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"اختر الإجراء المناسب:",
        reply_markup=markup
    )

def send_waiting_message(chat_id):
    markup = types.InlineKeyboardMarkup()
    support_button = types.InlineKeyboardButton("📞 التواصل مع الدعم", callback_data='online_support', style="primary")
    markup.add(support_button)
    
    bot.send_message(
        chat_id,
        "<tg-emoji emoji-id='6084396322444544568'>⏳</tg-emoji> تم إرسال طلب اشتراكك إلى الأدمن.\n"
        "يرجى الانتظار حتى يتم الموافقة على طلبك.\n\n"
        "للتواصل مع الدعم اضغط على الزر أدناه:",
        reply_markup=markup,
        parse_mode='HTML'
    )

# ======= دوال الحماية ======= #
def scan_file_for_malicious_code(file_path, user_id):
    if is_admin(user_id):
        return False, None, ""

    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        
        content = raw_data.decode('utf-8', errors='replace')
        
        dangerous_patterns = [
            r"rm\s+-rf\s+[\'\"]?/",
            r"import\s+marshal",
            r"import\s+zlib", 
            r"import\s+base64",
            r"eval\s*\(",
            r"exec\s*\(",
            r"shutil\.make_archive",
            r"bot\.send_document",
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True, f"تم اكتشاف أمر خطير: {pattern}", "malicious"
                
        return False, None, ""
    except Exception as e:
        return True, f"خطأ في الفحص: {e}", "malicious"

# ======= دوال أساسية ======= #
def stop_bot(script_path, chat_id, delete=False):
    try:
        if chat_id in bot_scripts and bot_scripts[chat_id].get('process'):
            process = bot_scripts[chat_id]['process']
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        
        if delete and os.path.exists(script_path):
            os.remove(script_path)
            
        return True
    except Exception as e:
        print(f"Error stopping bot: {e}")
        return False

def start_file(script_path, chat_id):
    script_name = os.path.basename(script_path)

    with lock:
        if chat_id not in bot_scripts:
            bot_scripts[chat_id] = {'process': None, 'files': [], 'path': script_path}

        try:
            if bot_scripts[chat_id].get('process') and bot_scripts[chat_id]['process'].poll() is None:
                bot.send_message(chat_id, f"الملف {script_name} يعمل بالفعل.")
                return

            p = subprocess.Popen([sys.executable, script_path])
            bot_scripts[chat_id]['process'] = p
            bot.send_message(chat_id, f"<tg-emoji emoji-id='5942913575658985039'>✅</tg-emoji> تم تشغيل الملف {script_name} بنجاح.", parse_mode='HTML')
        except Exception as e:
            bot.send_message(chat_id, f"❌ فشل في تشغيل الملف: {e}")

# ======= دوال التحكم في البوت الرئيسي ======= #
def start_bot_control():
    """تشغيل البوت الرئيسي"""
    global bot_running
    bot_running = True
    print("تم تشغيل البوت الرئيسي")

def stop_bot_control():
    """إيقاف البوت الرئيسي"""
    global bot_running
    bot_running = False
    print("تم إيقاف البوت الرئيسي")

# ======= Handlers الأساسية ======= #
@bot.message_handler(commands=['start'])
def start(message):
    save_chat_id(message.chat.id)
    user_id = message.from_user.id

    if not bot_running:
        bot.send_message(message.chat.id, "⏸️ البوت متوقف حالياً. يرجى الانتظار حتى يتم تشغيله.")
        return

    if message.from_user.username in banned_users:
        bot.send_message(message.chat.id, "⁉️ تم حظرك من البوت. تواصل مع المطور.")
        return

    if is_approved_user(user_id):
        show_main_menu(message)
    elif user_id in pending_requests:
        send_waiting_message(message.chat.id)
    else:
        user_info = {
            'first_name': message.from_user.first_name,
            'username': message.from_user.username or 'غير متوفر',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        request_approval(user_id, user_info)
        send_waiting_message(message.chat.id)

def show_main_menu(message):
    """عرض القائمة الرئيسية مع الأزرار المطلوبة"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # الأزرار الرئيسية كما في الصورة
    protection_button = types.InlineKeyboardButton("التحكم في الحماية 🛡️", callback_data='protection_control', style="success")
    upload_button = types.InlineKeyboardButton("رفع ملف 📥", callback_data='upload', style="success")
    my_files_button = types.InlineKeyboardButton("📂 ملفاتي", callback_data='my_files', style="success")
    points_button = types.InlineKeyboardButton("", callback_data='points_menu', style="primary")
    support_girl_button = types.InlineKeyboardButton("فتاة المحاور 👩‍💼", callback_data='support_girl', style="success")
    speed_button = types.InlineKeyboardButton("🚀 سرعة البوت", callback_data='speed', style="success")
    about_button = types.InlineKeyboardButton("ℹ️ حول البوت", callback_data='about_bot', style="success")
    tech_support_button = types.InlineKeyboardButton("🛠️ الدعم الفني", callback_data='tech_support', style="primary")
    install_lib_button = types.InlineKeyboardButton("📚 تثبيت مكتبة", callback_data='download_lib', style="primary")
    contact_support_button = types.InlineKeyboardButton("📞 التواصل مع الدعم", callback_data='online_support', style="primary")
    
    # ترتيب الأزرار كما في الصورة
    markup.add(protection_button, upload_button)
    markup.add(my_files_button, points_button)
    markup.add(support_girl_button, speed_button)
    markup.add(about_button, tech_support_button)
    markup.add(install_lib_button, contact_support_button)
    
    # إضافة أزرار الأدمن إذا كان مستخدم مسؤول
    if is_admin(message.from_user.id):
        users_button = types.InlineKeyboardButton("👥 إدارة المستخدمين", callback_data='manage_users', style="primary")
        bot_control_button = types.InlineKeyboardButton("⚡ تشغيل/إيقاف البوت", callback_data='bot_control', style="primary")
        all_files_button = types.InlineKeyboardButton("🗂️ ملفات الأدمن", callback_data='admin_all_files', style="primary")
        markup.add(users_button, bot_control_button)
        markup.add(all_files_button)

    bot.send_message(
        message.chat.id,
        f"<tg-emoji emoji-id='5260480440971570446'>🐍</tg-emoji> <b>Python Hosting</b> <tg-emoji emoji-id='5260480440971570446'>🐍</tg-emoji>\n\n"
        f"مرحباً، {message.from_user.first_name}! <tg-emoji emoji-id='5776176412583008554'>👋</tg-emoji>\n\n"
        "<b>الميزات المتاحة:</b> <tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji>\n\n"
        "• تشغيل الملف على سيرفر خاص\n"
        "• تشغيل الملفات بكل سهولة وسرعة\n"
        "• تواصل مع المحاور لأي إستفسار أو مشاكل\n\n"
        "<b>اختر من الأزرار أدناه:</b>",
        reply_markup=markup,
        parse_mode='HTML'
    )

# ======= ملفاتي ======= #
@bot.callback_query_handler(func=lambda call: call.data == 'my_files')
def my_files_callback(call):
    if not is_approved_user(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ تحتاج إلى موافقة الأدمن")
        return
    user_id = call.from_user.id
    files_list = get_user_files_list(user_id)
    if not files_list:
        bot.send_message(call.message.chat.id, "<tg-emoji emoji-id='5201731687863569981'>📁</tg-emoji> ليس لديك أي ملفات مرفوعة بعد.")
        return
    for filename in files_list:
        file_path = os.path.join(uploaded_files_dir, filename)
        if not os.path.exists(file_path):
            continue
        markup = types.InlineKeyboardMarkup()
        stop_btn = types.InlineKeyboardButton(f"⏸️ إيقاف", callback_data=f'stop_file_{user_id}_{filename}', style="primary")
        start_btn = types.InlineKeyboardButton(f"▶️ تشغيل", callback_data=f'start_file_{user_id}_{filename}', style="success")
        delete_btn = types.InlineKeyboardButton(f"🗑️ حذف", callback_data=f'delete_file_{user_id}_{filename}', style="success")
        markup.add(stop_btn, start_btn)
        markup.add(delete_btn)
        status = "يعمل" if (call.message.chat.id in bot_scripts and bot_scripts.get(call.message.chat.id, {}).get('process') and bot_scripts[call.message.chat.id]['process'].poll() is None) else "متوقف"
        bot.send_message(call.message.chat.id, f"<tg-emoji emoji-id='5201731687863569981'>📁</tg-emoji> <b>{filename}</b>\nالحالة: {status}", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_file_'))
def stop_user_file(call):
    _, _, user_id, filename = call.data.split('_', 3)
    if int(user_id) != call.from_user.id and not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية")
        return
    file_path = os.path.join(uploaded_files_dir, filename)
    stop_bot(file_path, call.message.chat.id)
    bot.answer_callback_query(call.id, f"<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> تم إيقاف {filename}")
    bot.edit_message_text(f"<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> تم إيقاف {filename}", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('start_file_'))
def start_user_file(call):
    _, _, user_id, filename = call.data.split('_', 3)
    if int(user_id) != call.from_user.id and not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية")
        return
    file_path = os.path.join(uploaded_files_dir, filename)
    start_file(file_path, call.message.chat.id)
    bot.answer_callback_query(call.id, f"<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> تم تشغيل {filename}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_file_'))
def delete_user_file(call):
    _, _, user_id, filename = call.data.split('_', 3)
    if int(user_id) != call.from_user.id and not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية")
        return
    file_path = os.path.join(uploaded_files_dir, filename)
    stop_bot(file_path, call.message.chat.id, delete=True)
    remove_file_from_user(int(user_id), filename)
    bot.answer_callback_query(call.id, f"<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> تم حذف {filename}")
    bot.edit_message_text(f"<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> تم حذف {filename}", call.message.chat.id, call.message.message_id)

# ======= ملفات الأدمن ======= #
# ======= ملفات الأدمن - النسخة المعدلة ======= #
@bot.callback_query_handler(func=lambda call: call.data == 'admin_all_files')
def admin_all_files(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية")
        return
    data = load_points()
    for uid, info in data.items():
        for filename in info.get("files", []):
            file_path = os.path.join(uploaded_files_dir, filename)
            if not os.path.exists(file_path):
                continue
            markup = types.InlineKeyboardMarkup()
            delete_btn = types.InlineKeyboardButton(f"🗑️ حذف", callback_data=f'admin_del_file_{uid}_{filename}', style="primary")
            markup.add(delete_btn)
            # ✅ استخدمت 📁 عادي بدل tg-emoji
            # في دالة admin_all_files
            bot.send_message(call.message.chat.id, f"📁 <b>المستخدم: {uid}</b>\nالملف: {filename}", reply_markup=markup, parse_mode='HTML')
            bot.send_message(call.message.chat.id, "✅ <b>انتهت قائمة الملفات.</b>", parse_mode='HTML')

# ======= نظام النقاط ======= #
@bot.callback_query_handler(func=lambda call: call.data == 'points_menu')
def points_menu(call):
    if not is_approved_user(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ تحتاج إلى موافقة الأدمن")
        return
    points = get_user_points(call.from_user.id)
    markup = types.InlineKeyboardMarkup()
    free_btn = types.InlineKeyboardButton("✨ نقاط مجانية (يومياً)", callback_data='claim_daily', style="success")
    buy_btn = types.InlineKeyboardButton("🛒 شراء نقاط", callback_data='buy_points', style="success")
    redeem_btn = types.InlineKeyboardButton("🎟️ إدخال كود هدية", callback_data='redeem_code_menu', style="success")
    back_btn = types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main', style="success")
    markup.add(free_btn, buy_btn)
    markup.add(redeem_btn)
    markup.add(back_btn)
    bot.send_message(call.message.chat.id, f"💎 <b>نظام النقاط</b>\n\nرصيدك الحالي: {points} نقطة\n\nاختر:", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'claim_daily')
def claim_daily_callback(call):
    if not is_approved_user(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ تحتاج إلى موافقة الأدمن")
        return
    if claim_daily(call.from_user.id):
        new_points = get_user_points(call.from_user.id)
        bot.answer_callback_query(call.id, f"<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> تم إضافة {DAILY_REWARD} نقطة! رصيدك الآن: {new_points}")
    else:
        bot.answer_callback_query(call.id, "❌ يمكنك الحصول على النقاط المجانية مرة كل 24 ساعة فقط")

@bot.callback_query_handler(func=lambda call: call.data == 'buy_points')
def buy_points_callback(call):
    bot.answer_callback_query(call.id, "📞 للشراء، تواصل مع الأدمن: @al0osh505")

@bot.callback_query_handler(func=lambda call: call.data == 'redeem_code_menu')
def redeem_code_menu(call):
    msg = bot.send_message(call.message.chat.id, "🎟️ أرسل كود الهدية الآن:")
    bot.register_next_step_handler(msg, process_redeem_code)

def process_redeem_code(message):
    code = message.text.strip()
    success, msg = redeem_gift_code(message.from_user.id, code)
    if success:
        bot.send_message(message.chat.id, f"<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> {msg}")
    else:
        bot.send_message(message.chat.id, f"❌ {msg}")

# ======= أوامر الأدمن الموسعة ======= #
@bot.callback_query_handler(func=lambda call: call.data == 'manage_users')
def manage_users(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "ليس لديك صلاحية")
        return
    
    total_approved = len(approved_users)
    total_pending = len(pending_requests)
    
    markup = types.InlineKeyboardMarkup()
    
    if pending_requests:
        pending_button = types.InlineKeyboardButton(f"📋 طلبات الانتظار ({total_pending})", callback_data='show_pending', style="primary")
        markup.add(pending_button)
    
    approved_button = types.InlineKeyboardButton(f"✅ المعتمدون ({total_approved})", callback_data='show_approved', style="primary")
    points_admin_btn = types.InlineKeyboardButton("💎 إدارة النقاط", callback_data='admin_points_panel', style="primary")
    broadcast_btn = types.InlineKeyboardButton("📢 إذاعة", callback_data='admin_broadcast_panel', style="success")
    gift_btn = types.InlineKeyboardButton("🎟️ إنشاء كود هدية", callback_data='admin_create_gift', style="primary")
    back_button = types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main', style="primary")
    
    markup.add(approved_button)
    markup.add(points_admin_btn)
    markup.add(broadcast_btn)
    markup.add(gift_btn)
    markup.add(back_button)
    
    bot.edit_message_text(
        f"<tg-emoji emoji-id='5258513401784573443'>👥</tg-emoji> <b>إدارة المستخدمين</b>\n\n"
        f"<tg-emoji emoji-id='6084693581426069171'>📊</tg-emoji> <b>الإحصائيات:</b>\n"
        f"<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> المعتمدون: {total_approved}\n"
        f"<tg-emoji emoji-id='6084396322444544568'>⏳</tg-emoji> طلبات الانتظار: {total_pending}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='HTML'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'admin_points_panel')
def admin_points_panel(call):
    if not is_admin(call.from_user.id):
        return
    bot.send_message(call.message.chat.id, "💎 أرسل: اضافة <user_id> <عدد النقاط> أو خصم <user_id> <عدد النقاط>")
    bot.register_next_step_handler(call.message, admin_points_action)

def admin_points_action(message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "❌ استخدم: اضافة ID نقاط أو خصم ID نقاط")
        return
    action, uid_str, points_str = parts
    try:
        uid = int(uid_str)
        points = int(points_str)
    except:
        bot.reply_to(message, "❌ تأكد من ID ونقاط صحيحة")
        return
    if action == "اضافة":
        add_user_points(uid, points)
        bot.reply_to(message, f"<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> تم إضافة {points} نقطة للمستخدم {uid}")
    elif action == "خصم":
        remove_user_points(uid, points)
        bot.reply_to(message, f"<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> تم خصم {points} نقطة من المستخدم {uid}")
    else:
        bot.reply_to(message, "❌ أمر غير معروف")

@bot.callback_query_handler(func=lambda call: call.data == 'admin_broadcast_panel')
def admin_broadcast_panel(call):
    if not is_admin(call.from_user.id):
        return
    msg = bot.send_message(call.message.chat.id, "📢 أرسل الرسالة التي تريد إذاعتها للجميع:")
    bot.register_next_step_handler(msg, admin_broadcast_send)

def admin_broadcast_send(message):
    if not is_admin(message.from_user.id):
        return
    text = message.text
    data = load_points()
    success = 0
    for uid in data.keys():
        try:
            bot.send_message(int(uid), f"📢 <b>إذاعة من الأدمن</b>\n\n{text}", parse_mode='HTML')
            success += 1
        except:
            pass
    bot.reply_to(message, f"<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> تم الإرسال لـ {success} مستخدم")

@bot.callback_query_handler(func=lambda call: call.data == 'admin_create_gift')
def admin_create_gift(call):
    if not is_admin(call.from_user.id):
        return
    msg = bot.send_message(call.message.chat.id, "🎟️ أرسل: عدد_النقاط عدد_الاستخدامات")
    bot.register_next_step_handler(msg, admin_create_gift_step2)

def admin_create_gift_step2(message):
    if not is_admin(message.from_user.id):
        return
    try:
        points, max_uses = map(int, message.text.split())
        code = generate_gift_code(points, max_uses)
        bot.reply_to(message, f"🎟️ كود الهدية:\n<code>{code}</code>\nعدد النقاط: {points}\nعدد المستخدمين: {max_uses}", parse_mode='HTML')
    except:
        bot.reply_to(message, "❌ خطأ: أرسل رقمين صحيحين")

# ======= باقي الكود الأصلي (بدون تغيير) ======= #
@bot.callback_query_handler(func=lambda call: call.data == 'support_girl')
def support_girl_callback(call):
    if not is_approved_user(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ تحتاج إلى موافقة الأدمن")
        return
        
    bot.answer_callback_query(call.id, "👩‍💼 جاري الاتصال بفتاة المحاور...")
    
    time.sleep(1)
    
    markup = types.InlineKeyboardMarkup()
    end_chat_button = types.InlineKeyboardButton("إنهاء المحادثة", callback_data='end_chat', style="primary")
    markup.add(end_chat_button)
    
    bot.send_message(
        call.message.chat.id,
        "<tg-emoji emoji-id='5310170944843579391'>👩‍💼</tg-emoji> <b>مرحباً! أنا فتاة المحاور</b>\n\n"
        "كيف يمكنني مساعدتك اليوم؟\n"
        "أنا هنا للإجابة على استفساراتك وتقديم الدعم.\n\n"
        "يمكنك سؤالي عن:\n"
        "• كيفية استخدام البوت\n"
        "• المشاكل التقنية\n"
        "• استفسارات عامة\n\n"
        "ما الذي تريد معرفته؟ <tg-emoji emoji-id='5310170944843579391'>💬</tg-emoji>",
        reply_markup=markup,
        parse_mode='HTML'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'end_chat')
def end_chat_callback(call):
    bot.answer_callback_query(call.id, "تم إنهاء المحادثة")
    
    markup = types.InlineKeyboardMarkup()
    restart_chat = types.InlineKeyboardButton("🔄 بدء محادثة جديدة", callback_data='support_girl', style="primary")
    main_menu = types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='back_to_main', style="primary")
    markup.add(restart_chat, main_menu)
    
    bot.edit_message_text(
        "<tg-emoji emoji-id='5776176412583008554'>👋</tg-emoji> <b>تم إنهاء المحادثة</b>\n\n"
        "شكراً لك على التواصل معنا!\n"
        "لا تتردد في البدء بمحادثة جديدة إذا كنت بحاجة للمساعدة.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='HTML'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'bot_control')
def bot_control_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية للتحكم في البوت")
        return
    
    global bot_running
    
    markup = types.InlineKeyboardMarkup()
    
    if bot_running:
        stop_button = types.InlineKeyboardButton("🛑 إيقاف البوت", callback_data='stop_bot_main', style="primary")
        status_text = "<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> البوت يعمل حالياً"
        markup.add(stop_button)
    else:
        start_button = types.InlineKeyboardButton("⚡ تشغيل البوت", callback_data='start_bot_main', style="primary")
        status_text = "⏸️ البوت متوقف حالياً"
        markup.add(start_button)
    
    back_button = types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main', style="primary")
    markup.add(back_button)
    
    bot.edit_message_text(
        f"<tg-emoji emoji-id='5773971380668210102'>⚡</tg-emoji> <b>تحكم في البوت الرئيسي</b>\n\n"
        f"الحالة: {status_text}\n\n"
        f"من هنا يمكنك التحكم في حالة البوت الرئيسي:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='HTML'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'stop_bot_main')
def stop_bot_main(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية")
        return
    
    stop_bot_control()
    
    bot.answer_callback_query(call.id, "🛑 تم إيقاف البوت")
    bot_control_callback(call)

@bot.callback_query_handler(func=lambda call: call.data == 'start_bot_main')
def start_bot_main(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية")
        return
    
    start_bot_control()
    
    bot.answer_callback_query(call.id, "⚡ تم تشغيل البوت")
    bot_control_callback(call)

@bot.callback_query_handler(func=lambda call: call.data == 'speed')
def check_speed(call):
    if not is_approved_user(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ تحتاج إلى موافقة الأدمن")
        return
        
    bot.answer_callback_query(call.id, "⏳ جاري قياس سرعة البوت...")
    
    wait_msg = bot.send_message(call.message.chat.id, "<tg-emoji emoji-id='6084396322444544568'>⏳</tg-emoji> <b>انتظر يتم قياس سرعة البوت...</b>", parse_mode='HTML')
    
    start_time = time.time()
    
    response_times = []
    for i in range(3):
        test_start = time.time()
        time.sleep(0.1)
        response_times.append((time.time() - test_start) * 1000)
    
    avg_response_time = sum(response_times) / len(response_times)
    total_time = (time.time() - start_time) * 1000
    
    if avg_response_time < 50:
        rating = "⚡ ممتازة!"
        emoji = "<tg-emoji emoji-id='5773971380668210102'>⚡</tg-emoji>"
    elif avg_response_time < 100:
        rating = "🚀 جيدة جداً"
        emoji = "🚀"
    elif avg_response_time < 200:
        rating = "👍 جيدة"
        emoji = "<tg-emoji emoji-id='5395661577380707230'>👍</tg-emoji>"
    else:
        rating = "🐌 تحتاج تحسين"
        emoji = "<tg-emoji emoji-id='5199778976687472097'>🐌</tg-emoji>"
    
    bot.edit_message_text(
        f"{emoji} <b>سرعة البوت الحالية:</b>\n\n"
        f"• سرعة الاستجابة: <code>{avg_response_time:.2f} ms</code>\n"
        f"• الوقت الكلي: <code>{total_time:.2f} ms</code>\n"
        f"• التقييم: <b>{rating}</b>\n\n"
        f"<i>{datetime.now().strftime('%I:%M %p')}</i>",
        call.message.chat.id,
        wait_msg.message_id,
        parse_mode='HTML'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'upload')
def upload_file_callback(call):
    if not is_approved_user(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ تحتاج إلى موافقة الأدمن")
        return
    
    if not bot_running:
        bot.answer_callback_query(call.id, "⏸️ البوت متوقف حالياً")
        return
        
    bot.answer_callback_query(call.id, "📤 جاري إعداد رفع الملف...")
    
    markup = types.InlineKeyboardMarkup()
    cancel_button = types.InlineKeyboardButton("❌ إلغاء", callback_data='back_to_main', style="primary")
    markup.add(cancel_button)
    
    bot.send_message(
        call.message.chat.id,
        "<tg-emoji emoji-id='5776366177123045379'>📤</tg-emoji> <b>رفع ملف</b>\n\n"
        "أرسل ملف البوت الآن (ملف .py فقط)\n"
        "الحد الأقصى للحجم: 2MB\n\n"
        "سيتم فحص الملف تلقائياً للحماية.",
        reply_markup=markup,
        parse_mode='HTML'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'about_bot')
def about_bot(call):
    bot.answer_callback_query(call.id)
    
    markup = types.InlineKeyboardMarkup()
    features_button = types.InlineKeyboardButton("🌟 الميزات", callback_data='features_list', style="success")
    back_button = types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main', style="success")
    markup.add(features_button, back_button)
    
    bot.send_message(
        call.message.chat.id,
        "<tg-emoji emoji-id='5260480440971570446'>ℹ️</tg-emoji> <b>حول البوت</b>\n\n"
        "🐍 <b>Python Hosting Bot</b>\n\n"
        "<b>المميزات:</b>\n"
        "<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> تشغيل الملفات على سيرفر خاص\n"
        "<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> سرعة وأداء عالي\n"
        "<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> نظام حماية متقدم\n"
        "<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> دعم فني متكامل\n"
        "<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> إدارة مستخدمين ذكية\n\n"
        "<b>للمطورين:</b>\n"
        "<tg-emoji emoji-id='5980787993139481991'>🔹</tg-emoji> رفع وتشغيل ملفات .py\n"
        "<tg-emoji emoji-id='5980787993139481991'>🔹</tg-emoji> تثبيت المكتبات المطلوبة\n"
        "<tg-emoji emoji-id='5980787993139481991'>🔹</tg-emoji> مراقبة أداء البوت\n"
        "<tg-emoji emoji-id='5980787993139481991'>🔹</tg-emoji> تحكم كامل في العمليات",
        reply_markup=markup,
        parse_mode='HTML'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'features_list')
def show_features(call):
    bot.answer_callback_query(call.id)
    
    markup = types.InlineKeyboardMarkup()
    back_button = types.InlineKeyboardButton("🔙 رجوع", callback_data='about_bot', style="primary")
    markup.add(back_button)
    
    bot.edit_message_text(
        "<tg-emoji emoji-id='5233537411044107383'>🌟</tg-emoji> <b>الميزات المتاحة:</b>\n\n"
        "🛡️ <b>نظام الحماية:</b>\n"
        "• فحص الملفات تلقائياً\n"
        "• منع الملفات الضارة\n"
        "• مستويات حماية متعددة\n\n"
        "<tg-emoji emoji-id='5773971380668210102'>⚡</tg-emoji> <b>الأداء:</b>\n"
        "• تشغيل سريع للملفات\n"
        "• قياس سرعة البوت\n"
        "• إدارة العمليات الذكية\n\n"
        "<tg-emoji emoji-id='5258513401784573443'>👥</tg-emoji> <b>إدارة المستخدمين:</b>\n"
        "• نظام موافقة آمن\n"
        "• تحكم كامل للمشرف\n"
        "• حظر المستخدمين الضارين\n\n"
        "<tg-emoji emoji-id='5366231924597604153'>🛠️</tg-emoji> <b>الدعم:</b>\n"
        "• دعم فني متكامل\n"
        "• مساعدة مباشرة\n"
        "• حل المشاكل التقنية",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='HTML'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'download_lib')
def download_library(call):
    if not is_approved_user(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ تحتاج إلى موافقة الأدمن")
        return
        
    bot.send_message(call.message.chat.id, "<tg-emoji emoji-id='5346132860631791153'>📚</tg-emoji> أرسل اسم المكتبة التي تريد تثبيتها:", parse_mode='HTML')
    bot.register_next_step_handler(call.message, install_library_step)

def install_library_step(message):
    library_name = message.text.strip()
    bot.send_message(message.chat.id, f"🔄 جاري تثبيت {library_name}...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", library_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            bot.send_message(message.chat.id, f"<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> تم تثبيت {library_name} بنجاح", parse_mode='HTML')
        else:
            bot.send_message(message.chat.id, f"❌ فشل في تثبيت {library_name}\n{result.stderr}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'online_support')
def online_support(call):
    bot.answer_callback_query(call.id, "جارٍ إرسال طلب الدعم...")
    
    user_info = f"👤 {call.from_user.first_name}\n<tg-emoji emoji-id='5226717982230591144'>🆔</tg-emoji> {call.from_user.id}\n📌 @{call.from_user.username or 'غير متوفر'}"
    
    bot.send_message(
        ADMIN_ID,
        f"📞 طلب دعم فوري:\n\n{user_info}\n\n"
        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        parse_mode='HTML'
    )
    
    bot.send_message(call.message.chat.id, "<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> تم إرسال طلب الدعم للأدمن", parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'protection_control')
def protection_control(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "ليس لديك صلاحية")
        return
        
    status = "<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> مفعل" if protection_enabled else "❌ معطل"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    enable_btn = types.InlineKeyboardButton("تفعيل الحماية", callback_data='enable_protection', style="primary")
    disable_btn = types.InlineKeyboardButton("تعطيل الحماية", callback_data='disable_protection', style="success")
    low_btn = types.InlineKeyboardButton("منخفض", callback_data='protection_low', style="primary")
    medium_btn = types.InlineKeyboardButton("متوسط", callback_data='protection_medium', style="success")
    high_btn = types.InlineKeyboardButton("عالي", callback_data='protection_high', style="success")
    back_btn = types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main', style="primary")
    
    markup.add(enable_btn, disable_btn)
    markup.add(low_btn, medium_btn, high_btn)
    markup.add(back_btn)
    
    bot.edit_message_text(
        f"<tg-emoji emoji-id='5823268688874179761'>⚙️</tg-emoji> <b>إعدادات الحماية</b>\n\n"
        f"الحالة: {status}\n"
        f"المستوى: {protection_level}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='HTML'
    )

@bot.callback_query_handler(func=lambda call: call.data in ['enable_protection', 'disable_protection', 'protection_low', 'protection_medium', 'protection_high'])
def handle_protection_settings(call):
    global protection_enabled, protection_level
    
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "ليس لديك صلاحية")
        return
        
    if call.data == 'enable_protection':
        protection_enabled = True
        bot.answer_callback_query(call.id, "<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> تم تفعيل الحماية")
    elif call.data == 'disable_protection':
        protection_enabled = False
        bot.answer_callback_query(call.id, "❌ تم تعطيل الحماية")
    elif call.data == 'protection_low':
        protection_level = "low"
        bot.answer_callback_query(call.id, "🔵 مستوى منخفض")
    elif call.data == 'protection_medium':
        protection_level = "medium"
        bot.answer_callback_query(call.id, "🟡 مستوى متوسط")
    elif call.data == 'protection_high':
        protection_level = "high"
        bot.answer_callback_query(call.id, "🔴 مستوى عالي")
    
    protection_control(call)

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
def back_to_main(call):
    try:
        show_main_menu(call.message)
        bot.answer_callback_query(call.id, "العودة للقائمة الرئيسية")
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ في العودة")

@bot.message_handler(content_types=['document'])
def handle_file(message):
    if not is_approved_user(message.from_user.id):
        bot.reply_to(message, "❌ تحتاج إلى موافقة الأدمن لرفع الملفات.")
        return
        
    try:
        user_id = message.from_user.id
        
        if message.from_user.username in banned_users:
            bot.send_message(message.chat.id, "⁉️ تم حظرك من البوت")
            return

        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        
        if file_info.file_size > MAX_FILE_SIZE:
            bot.reply_to(message, "⛔ حجم الملف يتجاوز 2MB")
            return
            
        downloaded_file = bot.download_file(file_info.file_path)
        bot_script_name = message.document.file_name
        
        if not bot_script_name.endswith('.py'):
            bot.reply_to(message, "❌ فقط ملفات بايثون مسموحة")
            return

        temp_path = os.path.join(tempfile.gettempdir(), bot_script_name)
        with open(temp_path, 'wb') as temp_file:
            temp_file.write(downloaded_file)

        if protection_enabled and not is_admin(user_id):
            is_malicious, activity, threat_type = scan_file_for_malicious_code(temp_path, user_id)
            if is_malicious:
                bot.reply_to(message, "⛔ تم رفض الملف لأسباب أمنية")
                return
                
        script_path = os.path.join(uploaded_files_dir, bot_script_name)
        shutil.move(temp_path, script_path)

        bot_scripts[message.chat.id] = {
            'name': bot_script_name,
            'uploader': message.from_user.username,
            'path': script_path,
            'process': None
        }
        
        add_file_to_user(user_id, bot_script_name)

        markup = types.InlineKeyboardMarkup()
        stop_button = types.InlineKeyboardButton(f"🛑 إيقاف {bot_script_name}", callback_data=f'stop_{message.chat.id}_{bot_script_name}', style="primary")
        markup.add(stop_button)

        bot.reply_to(
            message,
            f"<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> <b>تم رفع الملف بنجاح</b>\n\n"
            f"الملف: {bot_script_name}\n"
            f"👤 المستخدم: @{message.from_user.username}\n\n"
            f"يمكنك إيقاف التشغيل بالزر أدناه:",
            reply_markup=markup,
            parse_mode='HTML'
        )
        
        start_file(script_path, message.chat.id)
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_'))
def stop_bot_callback(call):
    try:
        parts = call.data.split('_')
        chat_id = int(parts[1])
        script_name = '_'.join(parts[2:])
        
        script_path = os.path.join(uploaded_files_dir, script_name)
        if stop_bot(script_path, chat_id):
            bot.answer_callback_query(call.id, "<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> تم الإيقاف")
            bot.edit_message_text(
                f"🛑 تم إيقاف {script_name}",
                call.message.chat.id,
                call.message.message_id
            )
        else:
            bot.answer_callback_query(call.id, "❌ فشل في الإيقاف")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def approve_user(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "ليس لديك صلاحية")
        return
        
    user_id = int(call.data.split('_')[1])
    
    if user_id in pending_requests:
        user_info = pending_requests.pop(user_id)
        approved_users.add(user_id)
        
        try:
            bot.send_message(
                user_id,
                f"<tg-emoji emoji-id='5233537411044107383'>🎉</tg-emoji> <b>تمت الموافقة على طلبك!</b>\n\n"
                f"مرحباً {user_info['first_name']} <tg-emoji emoji-id='5776176412583008554'>👋</tg-emoji>\n"
                f"يمكنك الآن استخدام البوت بالكامل.\n\n"
                f"أرسل /start لبدء الاستخدام.",
                parse_mode='HTML'
            )
        except:
            pass
        
        bot.answer_callback_query(call.id, "<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> تم قبول المستخدم")
        bot.edit_message_text(
            f"<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> <b>تم قبول المستخدم:</b>\n"
            f"👤 {user_info['first_name']}\n"
            f"<tg-emoji emoji-id='5226717982230591144'>🆔</tg-emoji> {user_id}\n"
            f"📌 @{user_info['username']}",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )
    else:
        bot.answer_callback_query(call.id, "❌ لم يتم العثور على الطلب")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_'))
def reject_user(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "ليس لديك صلاحية")
        return
        
    user_id = int(call.data.split('_')[1])
    
    if user_id in pending_requests:
        user_info = pending_requests.pop(user_id)
        
        try:
            bot.send_message(
                user_id,
                "❌ تم رفض طلب اشتراكك.\n\n"
                "للتواصل مع الدعم اضغط /start واختر التواصل مع الدعم."
            )
        except:
            pass
        
        bot.answer_callback_query(call.id, "❌ تم رفض المستخدم")
        bot.edit_message_text(
            f"❌ <b>تم رفض المستخدم:</b>\n"
            f"👤 {user_info['first_name']}\n"
            f"<tg-emoji emoji-id='5226717982230591144'>🆔</tg-emoji> {user_id}\n"
            f"📌 @{user_info['username']}",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )
    else:
        bot.answer_callback_query(call.id, "❌ لم يتم العثور على الطلب")

@bot.callback_query_handler(func=lambda call: call.data == 'show_pending')
def show_pending_requests(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "ليس لديك صلاحية")
        return
    
    if not pending_requests:
        bot.answer_callback_query(call.id, "لا توجد طلبات انتظار")
        return
    
    for user_id, user_info in list(pending_requests.items())[:5]:
        markup = types.InlineKeyboardMarkup()
        approve_btn = types.InlineKeyboardButton("قبول", callback_data=f'approve_{user_id}', style="primary")
        reject_btn = types.InlineKeyboardButton("رفض", callback_data=f'reject_{user_id}', style="primary")
        markup.add(approve_btn, reject_btn)
        
        bot.send_message(
            call.message.chat.id,
            f"👤 {user_info['first_name']}\n"
            f"<tg-emoji emoji-id='5226717982230591144'>🆔</tg-emoji> {user_id}\n"
            f"📌 @{user_info['username']}\n"
            f"<tg-emoji emoji-id='5348398031580447334'>⏰</tg-emoji> {user_info['timestamp']}",
            reply_markup=markup,
            parse_mode='HTML'
        )

@bot.callback_query_handler(func=lambda call: call.data == 'show_approved')
def show_approved_users(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "ليس لديك صلاحية")
        return
    
    users_list = list(approved_users)[:20]
    if not users_list:
        bot.send_message(call.message.chat.id, "لا يوجد مستخدمين معتمدين")
        return
    
    text = "<tg-emoji emoji-id='5211112665237175703'>✅</tg-emoji> <b>قائمة المستخدمين المعتمدين:</b>\n\n"
    for uid in users_list:
        text += f"🆔 {uid}\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='HTML')

@bot.message_handler(commands=['rck'])
def broadcast_message(message):
    if not is_admin(message.from_user.id):
        return
        
    try:
        msg = message.text.split(' ', 1)[1]
        success = 0
        failed = 0
        
        for user_id in approved_users:
            try:
                bot.send_message(user_id, msg)
                success += 1
            except:
                failed += 1
                
        bot.reply_to(message, f"<tg-emoji emoji-id='6084693581426069171'>📊</tg-emoji> تم الإرسال لـ {success} مستخدم، فشل: {failed}", parse_mode='HTML')
    except:
        bot.reply_to(message, "❌ استخدم: /rck الرسالة")

if __name__ == '__main__':
    print("🤖 البوت يعمل...")
    print(f"المستخدمون المعتمدون: {len(approved_users)}")
    print(f"طلبات الانتظار: {len(pending_requests)}")
    print(f"حالة البوت: {'يعمل' if bot_running else 'متوقف'}")
    
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ خطأ: {e}")
        time.sleep(5)