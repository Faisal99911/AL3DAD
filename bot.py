#Copyright ©️ 2021 TeLe TiPs. All Rights Reserved
#Enhanced for Arabic support, Dynamic Buttons, Interval Reminders, and Smart NLP by Manus AI

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import os
import asyncio
import re
from datetime import datetime, timedelta
from pyrogram.errors import FloodWait, MessageNotModified

# --- إعدادات البوت المباشرة ---
API_ID = 34257542
API_HASH = "614a1b5c5b712ac6de5530d5c571c42a"
BOT_TOKEN = "8662063487:AAFhVJQSQCpn52tv98ISkZO0ztAWCDml4UU"
# ---------------------------

# Initialize Bot
bot = Client(
    "Countdown-Arabic-Pro-V2",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Dictionary to store user states for interval setting
user_states = {}
# Dictionary to store active timers for deletion
active_timers = {}

# Smart Arabic Time Parser
def parse_advanced_arabic_time(time_str):
    now = datetime.now()
    time_str = time_str.strip().lower()
    
    # Handle Arabic numerals (١٢٣ -> 123)
    arabic_nums = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
    time_str = time_str.translate(arabic_nums)
    
    # Remove common prefixes
    time_str = re.sub(r'^(بعد|في|خلال)\s+', '', time_str)
    
    # 1. Handle "Tomorrow" (بكرة / غداً)
    is_tomorrow = False
    if re.search(r'(بكرة|بكرى|غدا|غداً)', time_str):
        is_tomorrow = True
        time_str = re.sub(r'(بكرة|بكرى|غدا|غداً)\s*', '', time_str).strip()

    # 2. Handle specific time like "9 مساء" or "7 صباحا"
    time_match = re.search(r'(\d+)\s*(مساء|صباحا|صباحاً|م|ص)', time_str)
    if time_match:
        hour = int(time_match.group(1))
        period = time_match.group(2)
        
        if 'مساء' in period or period == 'م':
            if hour < 12: hour += 12
        elif 'صباح' in period or period == 'ص':
            if hour == 12: hour = 0
            
        target_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if is_tomorrow:
            target_time += timedelta(days=1)
        elif target_time < now:
            target_time += timedelta(days=1)
            
        diff = (target_time - now).total_seconds()
        return int(diff)

    # 3. Handle relative durations
    time_map = {
        r'ثانية?': 1, r'ثواني': 1,
        r'دقيقة?': 60, r'دقائق': 60, r'دقايق': 60,
        r'ساعة?': 3600, r'ساعات': 3600,
        r'يوم': 86400, r'أيام': 86400, r'ايام': 86400,
        r'أسبوع': 604800, r'اسبوع': 604800, r'أسابيع': 604800,
        r'شهر': 2592000, r'شهور': 2592000,
    }
    
    special_cases = {
        r'نص ساعة?': 1800, r'نصف ساعة?': 1800,
        r'ربع ساعة?': 900, r'ثلث ساعة?': 1200,
        r'ساعتين': 7200, r'دقيقتين': 120, r'يومين': 172800,
        r'خمس دقايق': 300, r'عشر دقايق': 600,
    }
    
    for pattern, seconds in special_cases.items():
        if re.search(pattern, time_str):
            return seconds
            
    match = re.search(r'(\d+)\s*(.*)', time_str)
    if match:
        number = int(match.group(1))
        unit_part = match.group(2).strip()
        for pattern, seconds in time_map.items():
            if re.search(pattern, unit_part):
                return number * seconds
                
    for pattern, seconds in time_map.items():
        if re.fullmatch(pattern, time_str):
            return seconds
            
    return None

def get_dynamic_timer_buttons(event_name, seconds):
    # Calculate time units
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    # Large top button for event name
    top_button = [InlineKeyboardButton(f"{event_name}", callback_data="none")]
    
    # Dynamic bottom buttons based on remaining time
    if days > 0:
        # Show Days, Hours, Minutes
        bottom_buttons = [
            InlineKeyboardButton(f"{days} يوم", callback_data="none"),
            InlineKeyboardButton(f"{hours} ساعة", callback_data="none"),
            InlineKeyboardButton(f"{minutes} دقيقة", callback_data="none")
        ]
    else:
        # Show Hours, Minutes, Seconds
        bottom_buttons = [
            InlineKeyboardButton(f"{hours} ساعة", callback_data="none"),
            InlineKeyboardButton(f"{minutes} دقيقة", callback_data="none"),
            InlineKeyboardButton(f"{secs} ثانية", callback_data="none")
        ]
        
    return InlineKeyboardMarkup([top_button, bottom_buttons])

@bot.on_message(filters.command(['start', 'help', 'مساعدة']))
async def start(client, message):
    help_text = (
        "أهلاً بك في بوت العداد المطور 👋\n\n"
        "**كيفية الاستخدام:**\n"
        "أرسل: `عداد (الحدث) (بعد المدة)`\n\n"
        "**أمثلة:**\n"
        "• `عداد (مكالمة) (بعد 6 ساعات)`\n"
        "• `عداد (صلاة) (بعد نص ساعة)`\n"
        "• `عداد (اجتماع) (9 مساء)`\n\n"
        "**ميزات إضافية:**\n"
        "• سيطلب منك البوت تحديد مدة التذكير الدوري ⏰\n"
        "• لحذف المؤقت بالكامل، قم بالرد على رسالة البوت بكلمة **(حذف)**"
    )
    await message.reply(help_text)

@bot.on_message(filters.regex(r'^عداد\s+\((.+)\)\s+\((.+)\)$') | filters.regex(r'^عداد\s+(.+)\s+(.+)$'))
async def set_timer_step1(client, message):
    match = re.search(r'^عداد\s+\(?(.+?)\)?\s+\(?(.+?)\)?$', message.text)
    if not match:
        return await message.reply("صيغة غير صحيحة استخدم: `عداد (الحدث) (بعد المدة)` ❌")

    event_name = match.group(1).strip()
    time_str = match.group(2).strip()
    
    total_seconds = parse_advanced_arabic_time(time_str)
    
    if total_seconds is None:
        return await message.reply(f"لم أفهم الوقت: {time_str} ❌")

    user_states[message.from_user.id] = {
        "event": event_name,
        "total_seconds": total_seconds,
        "original_time_str": time_str
    }
    
    await message.reply("حدد مدة التذكير ⏰\n(مثلاً: كل 5 دقائق، كل ساعة، كل 10 ثواني)")

@bot.on_message(filters.text & ~filters.command(['start', 'help', 'مساعدة', 'stop', 'ايقاف']))
async def handle_responses(client, message):
    user_id = message.from_user.id
    
    # 1. Handle "حذف" (Delete) by reply
    if message.text.strip() == "حذف" and message.reply_to_message:
        reply_msg_id = message.reply_to_message.id
        if reply_msg_id in active_timers:
            active_timers[reply_msg_id] = False # Signal to stop the timer
            await message.reply("تم الحذف ✅")
            return
        elif message.reply_to_message.from_user.id == (await client.get_me()).id:
            # If it's a bot message but not in active_timers (maybe finished or just a help msg)
            try:
                await message.reply_to_message.delete()
                await message.reply("تم الحذف ✅")
                return
            except:
                pass

    # 2. Handle Interval Setting
    if user_id in user_states:
        state = user_states.pop(user_id)
        interval_str = message.text.replace("كل", "").strip()
        interval_seconds = parse_advanced_arabic_time(interval_str)
        
        if interval_seconds is None:
            return await message.reply(f"لم أفهم مدة التذكير: {message.text} حاول مرة أخرى بضبط العداد ❌")

        event = state["event"]
        total_seconds = state["total_seconds"]
        
        confirm_msg = await message.reply(f"تم البدء سأذكرك بـ **{event}** كل **{message.text}** ✅")
        
        # Start the background countdown task
        asyncio.create_task(run_countdown(client, message.chat.id, event, total_seconds, interval_seconds))

async def run_countdown(client, chat_id, event, total_seconds, interval_seconds):
    remaining = total_seconds
    timer_id = None
    
    while remaining > 0:
        # Check if timer was deleted
        if timer_id and timer_id in active_timers and active_timers[timer_id] == False:
            del active_timers[timer_id]
            return

        # Format display text
        d = remaining // 86400
        h = (remaining % 86400) // 3600
        m = (remaining % 3600) // 60
        s = remaining % 60
        
        display = ""
        if d > 0: display += f"{d} يوم "
        if h > 0: display += f"{h} ساعة "
        if m > 0: display += f"{m} دقيقة "
        if s > 0 or not display: display += f"{s} ثانية"
        
        text = f"العدّ التنازلي لـ {event} 🌙\nمتبقّي {display.strip()} تقريبي\n\nتهيأوا بالطاعة ✨"
        
        sent_msg = await client.send_message(
            chat_id, 
            text, 
            reply_markup=get_dynamic_timer_buttons(event, remaining)
        )
        
        # Track this message for deletion
        timer_id = sent_msg.id
        active_timers[timer_id] = True
        
        if remaining <= interval_seconds:
            await asyncio.sleep(remaining)
            remaining = 0
        else:
            await asyncio.sleep(interval_seconds)
            remaining -= interval_seconds
            
        # Clean up old tracking if we are sending a new message
        if remaining > 0:
            # We don't delete the old message as per user request (it sends a new one every interval)
            # but we keep tracking the latest one
            pass

    if timer_id in active_timers:
        del active_timers[timer_id]
        
    await client.send_message(chat_id, f"انتهى الوقت 🚨\n\nحان موعد: **{event}**")

if __name__ == "__main__":
    print("Pro Arabic Countdown Bot V2 is starting...")
    bot.run()
