from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
import os
import asyncio
import re
import uuid
from datetime import datetime, timedelta

# --- أمان (متغيرات بيئة) ---
API_ID = int(os.getenv("34257542"))
API_HASH = os.getenv("614a1b5c5b712ac6de5530d5c571c42a")
BOT_TOKEN = os.getenv("AAFhVJQSQCpn52tv98ISkZO0ztAWCDml4UU")

bot = Client("Countdown-Pro", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_states = {}
active_timers = {}

MAX_GLOBAL_TIMERS = 50
MAX_USER_TIMERS = 3

# ------------------ الوقت ------------------

def parse_advanced_arabic_time(time_str):
    now = datetime.now()
    time_str = time_str.strip().lower()

    arabic_nums = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
    time_str = time_str.translate(arabic_nums)

    time_str = re.sub(r'^(بعد|في|خلال)\s+', '', time_str)

    # دعم "ساعة ونص"
    if "ونص" in time_str:
        base = parse_advanced_arabic_time(time_str.replace("ونص", "").strip())
        if base:
            return int(base + 1800)

    match = re.search(r'(\d+(\.\d+)?)\s*(ساعة|دقيقة|ثانية)', time_str)
    if match:
        num = float(match.group(1))
        unit = match.group(3)

        if "ساعة" in unit:
            return int(num * 3600)
        elif "دقيقة" in unit:
            return int(num * 60)
        elif "ثانية" in unit:
            return int(num)

    mapping = {
        "ثانية": 1, "دقيقة": 60, "ساعة": 3600
    }

    for k, v in mapping.items():
        if k in time_str:
            return v

    return None

# ------------------ الأزرار ------------------

def get_buttons(event, seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(event, callback_data="none")],
        [
            InlineKeyboardButton(f"{h} ساعة", callback_data="none"),
            InlineKeyboardButton(f"{m} دقيقة", callback_data="none"),
            InlineKeyboardButton(f"{s} ثانية", callback_data="none")
        ]
    ])

# ------------------ إرسال آمن ------------------

async def safe_send(client, chat_id, text, markup=None):
    try:
        return await client.send_message(chat_id, text, reply_markup=markup)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await client.send_message(chat_id, text, reply_markup=markup)

# ------------------ الأوامر ------------------

@bot.on_message(filters.regex(r'^عداد\s+\(?(.+?)\)?\s+\(?(.+?)\)?$'))
async def set_timer(client, message):
    if len(active_timers) >= MAX_GLOBAL_TIMERS:
        return await message.reply("السيرفر مشغول حالياً ⚠️")

    user_id = message.from_user.id

    user_count = sum(1 for t in active_timers.values() if t["user"] == user_id)
    if user_count >= MAX_USER_TIMERS:
        return await message.reply("عندك عدادات كثيرة بالفعل ❌")

    match = re.search(r'^عداد\s+\(?(.+?)\)?\s+\(?(.+?)\)?$', message.text)
    event = match.group(1).strip()
    time_str = match.group(2).strip()

    total = parse_advanced_arabic_time(time_str)
    if not total:
        return await message.reply("ما فهمت الوقت ❌")

    user_states[user_id] = {"event": event, "total": total}

    await message.reply("حدد مدة التذكير ⏰")

@bot.on_message(filters.text)
async def interval_handler(client, message):
    user_id = message.from_user.id

    if user_id not in user_states:
        return

    state = user_states.pop(user_id)

    interval = parse_advanced_arabic_time(message.text.replace("كل", "").strip())
    if not interval:
        return await message.reply("ما فهمت مدة التذكير ❌")

    if interval > state["total"]:
        return await message.reply("مدة التذكير أكبر من وقت الحدث ❌")

    timer_id = str(uuid.uuid4())

    active_timers[timer_id] = {
        "active": True,
        "user": user_id,
        "last_msg": None
    }

    await message.reply(f"تم بدء العداد لـ {state['event']} ⏳")

    asyncio.create_task(run_timer(client, message.chat.id, timer_id, state["event"], state["total"], interval))

# ------------------ العداد ------------------

async def run_timer(client, chat_id, timer_id, event, total, interval):
    remaining = total

    while remaining > 0:
        if not active_timers.get(timer_id, {}).get("active"):
            return

        wait = min(interval, remaining)
        await asyncio.sleep(wait)
        remaining -= wait

        text = f"العدّ التنازلي لـ {event} 🌙\nمتبقي {remaining} ثانية\nتهيأوا ✨"

        msg = await safe_send(client, chat_id, text, get_buttons(event, remaining))

        active_timers[timer_id]["last_msg"] = msg.id

    await safe_send(client, chat_id, f"انتهى الوقت 🚨\n{event}")

    active_timers.pop(timer_id, None)

# ------------------

print("Bot running...")
bot.run()
