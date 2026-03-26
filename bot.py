#Copyright ©️ 2021 TeLe TiPs. All Rights Reserved
#Polished UI/UX upgrade (NO core logic changed)

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import os
import asyncio
import re
from datetime import datetime, timedelta
from pyrogram.errors import FloodWait, MessageDeleteForbidden

# --- إعدادات البوت المباشرة ---
API_ID = 34257542
API_HASH = "614a1b5c5b712ac6de5530d5c571c42a"
BOT_TOKEN = "8662063487:AAFhVJQSQCpn52tv98ISkZO0ztAWCDml4UU"
# ---------------------------

bot = Client(
    "Countdown-Arabic-Polished",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user_states = {}
active_timers = {}

# ----------- تحسين عرض الوقت -----------

def format_time(seconds):
    d = seconds // 86400
    h = (seconds % 86400) // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    parts = []
    if d > 0: parts.append(f"{d} يوم")
    if h > 0: parts.append(f"{h} ساعة")
    if m > 0: parts.append(f"{m} دقيقة")
    if s > 0 or not parts: parts.append(f"{s} ثانية")

    return " • ".join(parts)

# ----------- parser (نفس حقك بدون تغيير) -----------

def parse_advanced_arabic_time(time_str):
    now = datetime.now()
    time_str = time_str.strip().lower()
    arabic_nums = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
    time_str = time_str.translate(arabic_nums)
    time_str = re.sub(r'^(بعد|في|خلال)\s+', '', time_str)
    
    is_tomorrow = False
    if re.search(r'(بكرة|بكرى|غدا|غداً)', time_str):
        is_tomorrow = True
        time_str = re.sub(r'(بكرة|بكرى|غدا|غداً)\s*', '', time_str).strip()

    time_match = re.search(r'(\d+)\s*(مساء|صباحا|صباحاً|م|ص)', time_str)
    if time_match:
        hour = int(time_match.group(1))
        period = time_match.group(2)
        if 'مساء' in period or period == 'م':
            if hour < 12: hour += 12
        elif 'صباح' in period or period == 'ص':
            if hour == 12: hour = 0
        target_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if is_tomorrow or target_time < now:
            target_time += timedelta(days=1)
        return int((target_time - now).total_seconds())

    time_map = {
        r'ثانية?': 1, r'ثواني': 1,
        r'دقيقة?': 60, r'دقائق': 60, r'دقايق': 60,
        r'ساعة?': 3600, r'ساعات': 3600,
        r'يوم': 86400, r'أيام': 86400, r'ايام': 86400,
    }
    special_cases = {
        r'نص ساعة?': 1800, r'نصف ساعة?': 1800,
        r'ربع ساعة?': 900, r'ثلث ساعة?': 1200,
        r'ساعتين': 7200, r'دقيقتين': 120, r'يومين': 172800,
        r'خمس دقايق': 300, r'عشر دقايق': 600,
    }
    for pattern, seconds in special_cases.items():
        if re.search(pattern, time_str): return seconds
    match = re.search(r'(\d+)\s*(.*)', time_str)
    if match:
        number = int(match.group(1))
        unit_part = match.group(2).strip()
        for pattern, seconds in time_map.items():
            if re.search(pattern, unit_part): return number * seconds
    for pattern, seconds in time_map.items():
        if re.fullmatch(pattern, time_str): return seconds
    return None

# ----------- أزرار -----------

def get_dynamic_timer_buttons(event_name, seconds):
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    top_button = [InlineKeyboardButton(f"{event_name}", callback_data="none")]
    
    if days > 0:
        bottom_buttons = [
            InlineKeyboardButton(f"{days} يوم", callback_data="none"),
            InlineKeyboardButton(f"{hours} ساعة", callback_data="none"),
            InlineKeyboardButton(f"{minutes} دقيقة", callback_data="none")
        ]
    else:
        bottom_buttons = [
            InlineKeyboardButton(f"{hours} ساعة", callback_data="none"),
            InlineKeyboardButton(f"{minutes} دقيقة", callback_data="none"),
            InlineKeyboardButton(f"{secs} ثانية", callback_data="none")
        ]
    return InlineKeyboardMarkup([top_button, bottom_buttons])

# ----------- START -----------

@bot.on_message(filters.command(['start', 'help', 'مساعدة']))
async def start(client, message):
    help_text = (
        "👋 أهلاً بك في بوت العدّ التنازلي\n\n"
        "📌 أرسل:\n"
        "`عداد (اسم الحدث) (الوقت)`\n\n"
        "📎 مثال:\n"
        "• عداد (مكالمة) (بعد 5 دقائق)\n\n"
        "🧠 ثم اختر مدة التذكير\n"
        "🗑️ للحذف: رد بكلمة (حذف)"
    )
    await message.reply(help_text)

# ----------- STEP 1 -----------

@bot.on_message(filters.regex(r'^عداد\s+\((.+)\)\s+\((.+)\)$') | filters.regex(r'^عداد\s+(.+)\s+(.+)$'))
async def set_timer_step1(client, message):
    match = re.search(r'^عداد\s+\(?(.+?)\)?\s+\(?(.+?)\)?$', message.text)

    event_name = match.group(1).strip()
    time_str = match.group(2).strip()

    total_seconds = parse_advanced_arabic_time(time_str)
    if total_seconds is None:
        return await message.reply("❌ لم أفهم الوقت")

    user_states[message.from_user.id] = {
        "event": event_name,
        "total_seconds": total_seconds
    }

    await message.reply("⏱️ اكتب مدة التذكير\nمثال: كل 5 دقائق")

# ----------- STEP 2 -----------

@bot.on_message(filters.text & ~filters.command(['start', 'help', 'مساعدة']))
async def handle_responses(client, message):
    user_id = message.from_user.id

    # حذف
    if message.text.strip() == "حذف" and message.reply_to_message:
        reply_msg_id = message.reply_to_message.id

        for timer_key in list(active_timers.keys()):
            if reply_msg_id in active_timers[timer_key]["messages"]:
                active_timers[timer_key]["active"] = False

                for msg_id in active_timers[timer_key]["messages"]:
                    try:
                        await client.delete_messages(message.chat.id, msg_id)
                    except:
                        pass

                del active_timers[timer_key]
                return await message.reply("✅ تم الحذف")

    # التذكير
    if user_id in user_states:
        state = user_states.pop(user_id)

        interval_str = message.text.replace("كل", "").strip()
        interval_seconds = parse_advanced_arabic_time(interval_str)

        if interval_seconds is None:
            return await message.reply("❌ لم أفهم مدة التذكير")

        await message.reply(
            f"✅ بدأ العداد\n\n📌 {state['event']}\n⏰ {message.text}"
        )

        asyncio.create_task(
            run_countdown(
                client,
                message.chat.id,
                state["event"],
                state["total_seconds"],
                interval_seconds
            )
        )

# ----------- العداد -----------

async def run_countdown(client, chat_id, event, total_seconds, interval_seconds):
    remaining = total_seconds
    timer_key = f"{chat_id}_{event}_{datetime.now().timestamp()}"

    active_timers[timer_key] = {"active": True, "messages": []}

    while remaining > 0:
        if not active_timers[timer_key]["active"]:
            return

        display = format_time(remaining)

        text = f"⏳ {event}\n\n⏱️ {display}"

        try:
            sent_msg = await client.send_message(
                chat_id,
                text,
                reply_markup=get_dynamic_timer_buttons(event, remaining)
            )
        except FloodWait as e:
            await asyncio.sleep(e.value)
            continue

        active_timers[timer_key]["messages"] = [sent_msg.id]

        if remaining <= interval_seconds:
            await asyncio.sleep(remaining)
            remaining = 0
        else:
            await asyncio.sleep(interval_seconds)
            remaining -= interval_seconds

    await client.send_message(
        chat_id,
        f"🚨 انتهى الوقت\n\n📌 {event}\n\n🔔 انتبهوا"
    )

    if timer_key in active_timers:
        del active_timers[timer_key]

# -----------

print("Bot running...")
bot.run()
