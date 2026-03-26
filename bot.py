# -*- coding: utf-8 -*-
# Copyright ©️ 2025 Professional Timer Bot
# عالمي - احترافي - متعدد اللغات

import os
import asyncio
import re
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, MessageDeleteForbidden, MessageIdInvalid, UserIsBlocked

# ====================== الإعدادات ======================
API_ID = 34257542
API_HASH = "614a1b5c5b712ac6de5530d5c571c42a"
BOT_TOKEN = "8662063487:AAFhVJQSQCpn52tv98ISkZO0ztAWCDml4UU"

# إعدادات متقدمة
MAX_TIMERS_PER_USER = 10
MAX_TIMER_DURATION = 365 * 86400  # سنة كحد أقصى
MIN_INTERVAL = 5  # أقل فترة تذكير (ثواني)
DEFAULT_LANG = "ar"

# الترجمة
TRANSLATIONS = {
    "ar": {
        "start": "🎯 أهلاً بك في بوت العدادات الاحترافي!\n\n<b>✨ المميزات:</b>\n• مؤقتات متعددة لكل مستخدم\n• تذكير دوري مرن\n• أزرار تفاعلية ديناميكية\n• دعم كامل للغة العربية\n\n<b>📝 طريقة الاستخدام:</b>\n<code>عداد (الحدث) (المدة)</code>\n\n<b>📌 أمثلة:</b>\n<code>عداد (اجتماع) (بعد 30 دقيقة)</code>\n<code>عداد (صلاة) (الساعة 8 مساء)</code>\n<code>عداد (مكالمة) (بعد ساعتين)</code>\n\n<b>🛠️ الأوامر:</b>\n/stop - إيقاف كل مؤقتاتك\n/list - عرض مؤقتاتك النشطة",
        "invalid_format": "❌ صيغة غير صحيحة!\nاستخدم: <code>عداد (الحدث) (المدة)</code>",
        "invalid_time": "❌ لم أفهم المدة: {time}\nمثال: بعد 30 دقيقة، الساعة 8 مساء",
        "too_long": "⚠️ المدة طويلة جداً (أقصى سنة واحدة)",
        "too_many": "⚠️ لديك {count} مؤقت نشط (الحد الأقصى {max})",
        "interval_request": "⏰ حدد مدة التذكير:\n<code>كل 5 دقائق</code>\n<code>كل ساعة</code>\n<code>كل 30 ثانية</code>",
        "timer_started": "✅ تم البدء!\n<b>الحدث:</b> {event}\n<b>المدة:</b> {duration}\n<b>التذكير:</b> كل {interval}",
        "timer_expired": "🚨 <b>انتهى الوقت!</b> 🚨\n\n<b>📢 {event}</b>\n\n{mentions}",
        "timer_stopped": "🛑 تم إيقاف {count} مؤقت",
        "no_timers": "📭 لا يوجد مؤقتات نشطة",
        "list_timers": "📋 <b>مؤقتاتك النشطة:</b>\n\n{timers}",
        "deleted": "🗑️ تم الحذف",
        "error": "⚠️ حدث خطأ: {error}"
    },
    "en": {
        "start": "🎯 Welcome to Professional Timer Bot!\n\n<b>✨ Features:</b>\n• Multiple timers per user\n• Flexible reminders\n• Interactive buttons\n• Full English support\n\n<b>📝 Usage:</b>\n<code>timer (event) (duration)</code>\n\n<b>📌 Examples:</b>\n<code>timer (meeting) (in 30 minutes)</code>\n<code>timer (prayer) (at 8 PM)</code>\n\n<b>🛠️ Commands:</b>\n/stop - Stop all timers\n/list - List active timers",
        "invalid_format": "❌ Invalid format!\nUse: <code>timer (event) (duration)</code>",
        "invalid_time": "❌ Couldn't understand: {time}",
        "too_long": "⚠️ Duration too long (max 1 year)",
        "too_many": "⚠️ You have {count} active timers (max {max})",
        "interval_request": "⏰ Set reminder interval:\n<code>every 5 minutes</code>\n<code>every hour</code>",
        "timer_started": "✅ Started!\n<b>Event:</b> {event}\n<b>Duration:</b> {duration}\n<b>Reminder:</b> every {interval}",
        "timer_expired": "🚨 <b>Time's up!</b> 🚨\n\n<b>📢 {event}</b>",
        "timer_stopped": "🛑 Stopped {count} timer(s)",
        "no_timers": "📭 No active timers",
        "list_timers": "📋 <b>Your active timers:</b>\n\n{timers}",
        "deleted": "🗑️ Deleted",
        "error": "⚠️ Error: {error}"
    }
}

# ====================== قاعدة البيانات ======================
class Database:
    def __init__(self, db_path="timers.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                event TEXT,
                end_time INTEGER,
                interval_seconds INTEGER,
                message_id INTEGER,
                created_at INTEGER,
                active INTEGER DEFAULT 1
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_lang (
                user_id INTEGER PRIMARY KEY,
                lang TEXT DEFAULT 'ar'
            )
        """)
        self.conn.commit()
    
    def add_timer(self, chat_id, user_id, event, end_time, interval_seconds, message_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO timers (chat_id, user_id, event, end_time, interval_seconds, message_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (chat_id, user_id, event, end_time, interval_seconds, message_id, int(datetime.now().timestamp())))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_active_timers(self, user_id=None, timer_id=None):
        cursor = self.conn.cursor()
        if timer_id:
            cursor.execute("SELECT * FROM timers WHERE id = ? AND active = 1", (timer_id,))
            return cursor.fetchone()
        elif user_id:
            cursor.execute("SELECT * FROM timers WHERE user_id = ? AND active = 1 ORDER BY end_time", (user_id,))
            return cursor.fetchall()
        else:
            cursor.execute("SELECT * FROM timers WHERE active = 1")
            return cursor.fetchall()
    
    def deactivate_timer(self, timer_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE timers SET active = 0 WHERE id = ?", (timer_id,))
        self.conn.commit()
    
    def deactivate_user_timers(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE timers SET active = 0 WHERE user_id = ? AND active = 1", (user_id,))
        self.conn.commit()
        return cursor.rowcount
    
    def get_user_lang(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT lang FROM user_lang WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else DEFAULT_LANG
    
    def set_user_lang(self, user_id, lang):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO user_lang (user_id, lang) VALUES (?, ?)", (user_id, lang))
        self.conn.commit()

db = Database()

# ====================== الأدوات المساعدة ======================
def get_text(user_id, key, **kwargs):
    """جلب النص المترجم"""
    lang = db.get_user_lang(user_id)
    text = TRANSLATIONS.get(lang, TRANSLATIONS["ar"]).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text

def parse_advanced_time(time_str: str, lang: str = "ar") -> Optional[int]:
    """تحليل الوقت المتقدم"""
    now = datetime.now()
    time_str = time_str.strip().lower()
    
    # تحويل الأرقام العربية
    arabic_nums = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
    time_str = time_str.translate(arabic_nums)
    
    # إزالة كلمات البداية
    time_str = re.sub(r'^(بعد|في|خلال|in|after|at)\s+', '', time_str)
    
    # التحقق من الغد
    is_tomorrow = bool(re.search(r'(بكرة|غدا|tomorrow)', time_str))
    if is_tomorrow:
        time_str = re.sub(r'(بكرة|غدا|tomorrow)\s*', '', time_str).strip()
    
    # تحليل الوقت (الساعة)
    time_match = re.search(r'(\d+)\s*(مساء|صباحا|م|ص|pm|am)', time_str)
    if time_match:
        hour = int(time_match.group(1))
        period = time_match.group(2)
        if period in ['مساء', 'م', 'pm']:
            if hour < 12: hour += 12
        elif period in ['صباح', 'ص', 'am']:
            if hour == 12: hour = 0
        target_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if is_tomorrow or target_time < now:
            target_time += timedelta(days=1)
        return int((target_time - now).total_seconds())
    
    # تحليل المدة
    time_map = {
        'ثانية': 1, 'ثواني': 1, 'second': 1, 'seconds': 1,
        'دقيقة': 60, 'دقائق': 60, 'minute': 60, 'minutes': 60,
        'ساعة': 3600, 'ساعات': 3600, 'hour': 3600, 'hours': 3600,
        'يوم': 86400, 'أيام': 86400, 'day': 86400, 'days': 86400,
    }
    
    special_cases = {
        'نص ساعة': 1800, 'نصف ساعة': 1800, 'half hour': 1800,
        'ربع ساعة': 900, 'quarter hour': 900,
        'ساعتين': 7200, 'two hours': 7200,
        'دقيقتين': 120, 'two minutes': 120,
        'يومين': 172800, 'two days': 172800,
    }
    
    for pattern, seconds in special_cases.items():
        if re.search(pattern, time_str):
            return seconds
    
    match = re.search(r'(\d+)\s*(.*)', time_str)
    if match:
        number = int(match.group(1))
        unit = match.group(2).strip()
        for pattern, seconds in time_map.items():
            if re.search(pattern, unit):
                return number * seconds
    
    return None

def format_duration(seconds: int, lang: str = "ar") -> str:
    """تنسيق المدة بشكل مقروء"""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} {'يوم' if lang == 'ar' else 'day'}{'s' if days > 1 and lang == 'en' else ''}")
    if hours > 0:
        parts.append(f"{hours} {'ساعة' if lang == 'ar' else 'hour'}{'s' if hours > 1 and lang == 'en' else ''}")
    if minutes > 0:
        parts.append(f"{minutes} {'دقيقة' if lang == 'ar' else 'minute'}{'s' if minutes > 1 and lang == 'en' else ''}")
    if secs > 0 or not parts:
        parts.append(f"{secs} {'ثانية' if lang == 'ar' else 'second'}{'s' if secs > 1 and lang == 'en' else ''}")
    
    return ' '.join(parts)

def get_dynamic_buttons(event: str, remaining: int, lang: str = "ar") -> InlineKeyboardMarkup:
    """إنشاء أزرار ديناميكية"""
    days = remaining // 86400
    hours = (remaining % 86400) // 3600
    minutes = (remaining % 3600) // 60
    secs = remaining % 60
    
    # زر الحدث
    top_button = [InlineKeyboardButton(f"⏰ {event[:30]}", callback_data="none")]
    
    # أزرار الوقت
    if days > 0:
        bottom_buttons = [
            InlineKeyboardButton(f"📅 {days} {'ي' if lang == 'ar' else 'd'}", callback_data="none"),
            InlineKeyboardButton(f"⏱️ {hours} {'س' if lang == 'ar' else 'h'}", callback_data="none"),
            InlineKeyboardButton(f"⏲️ {minutes} {'د' if lang == 'ar' else 'm'}", callback_data="none")
        ]
    else:
        bottom_buttons = [
            InlineKeyboardButton(f"⏱️ {hours} {'س' if lang == 'ar' else 'h'}", callback_data="none"),
            InlineKeyboardButton(f"⏲️ {minutes} {'د' if lang == 'ar' else 'm'}", callback_data="none"),
            InlineKeyboardButton(f"⚡ {secs} {'ث' if lang == 'ar' else 's'}", callback_data="none")
        ]
    
    return InlineKeyboardMarkup([top_button, bottom_buttons])

# ====================== البوت ======================
bot = Client("ProfessionalTimerBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# تخزين مؤقت للعمليات النشطة
active_tasks: Dict[int, asyncio.Task] = {}

@bot.on_message(filters.command(['start', 'help', 'مساعدة']))
async def start_command(client, message: Message):
    """أمر البدء"""
    user_id = message.from_user.id
    
    # التحقق من اللغة
    if len(message.command) > 1 and message.command[1] in ['en', 'ar']:
        db.set_user_lang(user_id, message.command[1])
    
    await message.reply(get_text(user_id, "start"), parse_mode="HTML")

@bot.on_message(filters.command(['stop', 'ايقاف']))
async def stop_command(client, message: Message):
    """إيقاف جميع المؤقتات"""
    user_id = message.from_user.id
    count = db.deactivate_user_timers(user_id)
    
    # إلغاء المهام النشطة
    for timer_id, task in list(active_tasks.items()):
        if not task.done():
            task.cancel()
    
    await message.reply(get_text(user_id, "timer_stopped", count=count))

@bot.on_message(filters.command(['list', 'قائمة']))
async def list_command(client, message: Message):
    """عرض المؤقتات النشطة"""
    user_id = message.from_user.id
    timers = db.get_active_timers(user_id=user_id)
    
    if not timers:
        await message.reply(get_text(user_id, "no_timers"))
        return
    
    timer_list = []
    for timer in timers:
        remaining = max(0, timer[4] - int(datetime.now().timestamp()))
        timer_list.append(
            f"• <b>{timer[3]}</b>\n"
            f"  ⏱️ {format_duration(remaining, db.get_user_lang(user_id))}\n"
            f"  🔔 كل {format_duration(timer[5], db.get_user_lang(user_id))}"
        )
    
    text = get_text(user_id, "list_timers", timers="\n\n".join(timer_list))
    await message.reply(text, parse_mode="HTML")

@bot.on_message(filters.regex(r'^(عداد|timer)\s+\((.+)\)\s+\((.+)\)$') | filters.regex(r'^(عداد|timer)\s+(.+)\s+(.+)$'))
async def set_timer(client, message: Message):
    """إنشاء مؤقت جديد"""
    user_id = message.from_user.id
    lang = db.get_user_lang(user_id)
    
    # استخراج البيانات
    text = message.text
    match = re.search(r'^(عداد|timer)\s+\(?(.+?)\)?\s+\(?(.+?)\)?$', text)
    if not match:
        await message.reply(get_text(user_id, "invalid_format"), parse_mode="HTML")
        return
    
    event_name = match.group(2).strip()
    time_str = match.group(3).strip()
    
    # تحليل الوقت
    total_seconds = parse_advanced_time(time_str, lang)
    if total_seconds is None:
        await message.reply(get_text(user_id, "invalid_time", time=time_str))
        return
    
    # التحقق من المدة
    if total_seconds > MAX_TIMER_DURATION:
        await message.reply(get_text(user_id, "too_long"))
        return
    
    # التحقق من عدد المؤقتات
    active_timers = db.get_active_timers(user_id=user_id)
    if len(active_timers) >= MAX_TIMERS_PER_USER:
        await message.reply(get_text(user_id, "too_many", count=len(active_timers), max=MAX_TIMERS_PER_USER))
        return
    
    # تخزين حالة المستخدم
    user_states[user_id] = {
        "event": event_name,
        "total_seconds": total_seconds
    }
    await message.reply(get_text(user_id, "interval_request"), parse_mode="HTML")

# تخزين مؤقت للحالات
user_states = {}

@bot.on_message(filters.text & ~filters.command(['start', 'help', 'stop', 'ايقاف', 'list', 'قائمة']))
async def handle_interval(client, message: Message):
    """معالجة تحديد فترة التذكير"""
    user_id = message.from_user.id
    lang = db.get_user_lang(user_id)
    
    # التحقق من وجود حالة
    if user_id not in user_states:
        return
    
    state = user_states.pop(user_id)
    
    # تحليل الفترة
    interval_str = message.text.replace("كل", "").replace("every", "").strip()
    interval_seconds = parse_advanced_time(interval_str, lang)
    
    if interval_seconds is None or interval_seconds < MIN_INTERVAL:
        await message.reply(get_text(user_id, "invalid_time", time=message.text))
        return
    
    # إنشاء المؤقت
    end_time = int(datetime.now().timestamp()) + state["total_seconds"]
    sent_msg = await message.reply("⏳ جاري البدء...")
    
    # حفظ في قاعدة البيانات
    timer_id = db.add_timer(
        message.chat.id, user_id, state["event"],
        end_time, interval_seconds, sent_msg.id
    )
    
    await sent_msg.edit_text(
        get_text(user_id, "timer_started",
                event=state["event"],
                duration=format_duration(state["total_seconds"], lang),
                interval=format_duration(interval_seconds, lang)),
        parse_mode="HTML"
    )
    
    # تشغيل العد التنازلي
    task = asyncio.create_task(run_timer(client, timer_id, message.chat.id, user_id, 
                                         state["event"], end_time, interval_seconds))
    active_tasks[timer_id] = task

async def run_timer(client, timer_id, chat_id, user_id, event, end_time, interval_seconds):
    """تشغيل العد التنازلي"""
    lang = db.get_user_lang(user_id)
    
    try:
        while True:
            now = int(datetime.now().timestamp())
            remaining = end_time - now
            
            if remaining <= 0:
                # انتهاء الوقت
                timer_info = db.get_active_timers(timer_id=timer_id)
                if timer_info and timer_info[9] == 1:
                    # منشن للمستخدمين
                    try:
                        # محاولة جلب اسم المستخدم
                        user = await client.get_users(user_id)
                        mention = f"[{user.first_name}](tg://user?id={user_id})"
                    except:
                        mention = f"@{user_id}"
                    
                    await client.send_message(
                        chat_id,
                        get_text(user_id, "timer_expired", event=event, mentions=mention),
                        parse_mode="HTML"
                    )
                    db.deactivate_timer(timer_id)
                break
            
            # إرسال تحديث
            remaining_formatted = format_duration(remaining, lang)
            try:
                # حذف الرسالة السابقة
                timer_info = db.get_active_timers(timer_id=timer_id)
                if timer_info and timer_info[7]:
                    try:
                        await client.delete_messages(chat_id, timer_info[7])
                    except:
                        pass
                
                # إرسال رسالة جديدة
                sent = await client.send_message(
                    chat_id,
                    f"⏰ <b>{event}</b>\n⏳ متبقي: {remaining_formatted}",
                    reply_markup=get_dynamic_buttons(event, remaining, lang),
                    parse_mode="HTML"
                )
                
                # تحديث معرف الرسالة
                cursor = db.conn.cursor()
                cursor.execute("UPDATE timers SET message_id = ? WHERE id = ?", (sent.id, timer_id))
                db.conn.commit()
                
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                print(f"Error in timer {timer_id}: {e}")
            
            # انتظار الفترة المحددة
            await asyncio.sleep(min(interval_seconds, remaining))
            
    except asyncio.CancelledError:
        pass
    finally:
        if timer_id in active_tasks:
            del active_tasks[timer_id]

@bot.on_callback_query()
async def handle_callback(client, callback_query: CallbackQuery):
    """معالجة الأزرار"""
    await callback_query.answer()

@bot.on_message(filters.text & filters.reply)
async def handle_delete(client, message: Message):
    """حذف المؤقت بالرد"""
    if message.text.strip() not in ["حذف", "delete"]:
        return
    
    if not message.reply_to_message:
        return
    
    # البحث عن المؤقت المرتبط بالرسالة
    reply_id = message.reply_to_message.id
    timers = db.get_active_timers()
    
    for timer in timers:
        if timer[7] == reply_id:
            db.deactivate_timer(timer[0])
            if timer[0] in active_tasks:
                active_tasks[timer[0]].cancel()
            
            try:
                await message.reply_to_message.delete()
            except:
                pass
            
            await message.reply(get_text(message.from_user.id, "deleted"))
            return

@bot.on_message()
async def handle_unknown(client, message: Message):
    """معالجة الرسائل غير المعروفة"""
    pass

if __name__ == "__main__":
    print("🚀 Professional Timer Bot is running...")
    print(f"📊 Database: SQLite")
    print(f"⚙️ Max timers per user: {MAX_TIMERS_PER_USER}")
    bot.run()
