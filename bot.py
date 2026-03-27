#Copyright ©️ 2021 TeLe TiPs. All Rights Reserved
#Polished for Arabic support, Dynamic Buttons, Group Mentions, and Full History Deletion by Manus AI

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

def parse_advanced_arabic_time(time_str):
    now = datetime.now()
    time_str = time_str.strip().lower()
    # إزالة الأسطر الجديدة والمسافات الزائدة من وقت العداد لضمان التحليل الصحيح
    time_str = " ".join(time_str.split())
    
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

def get_dynamic_timer_buttons(seconds):
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if days > 0:
        bottom_buttons = [
            InlineKeyboardButton(f"{hours} ساعة ⏰", callback_data="none"),
            InlineKeyboardButton(f"{days} يوم 📅", callback_data="none"),
            InlineKeyboardButton(f"{minutes} دقيقة ⏳", callback_data="none")
        ]
    else:
        bottom_buttons = [
            InlineKeyboardButton(f"{hours} ساعة ⏰", callback_data="none"),
            InlineKeyboardButton(f"{minutes} دقيقة ⏳", callback_data="none"),
            InlineKeyboardButton(f"{secs} ثانية ⏱", callback_data="none")
        ]
    
    bottom_buttons.reverse()
    return InlineKeyboardMarkup([bottom_buttons])

@bot.on_message(filters.command(['start', 'help', 'مساعدة']))
async def start(client, message):
    help_text = (
        "أهلاً بك في بوت العداد المطور 👋\n\n"
        "**كيفية الاستخدام:**\n"
        "أرسل: `عداد (الحدث) (بعد المدة)`\n\n"
        "**أمثلة:**\n"
        "• `عداد (مكالمة تعالو سرريييييع يالله) (بعد ساعة)`\n"
        "• `عداد (صلاة) (بعد نص ساعة)`\n"
        "• `عداد (اجتماع) (9 مساء)`\n\n"
        "**ميزات إضافية:**\n"
        "• سيطلب منك البوت تحديد مدة التذكير الدوري ⏰\n"
        "• لحذف المؤقت بالكامل، قم بالرد على رسالة البوت بكلمة **(حذف)**\n"
        "• عند انتهاء الوقت، سيقوم البوت بعمل منشن ذكي للجميع 🔊"
    )
    await message.reply(help_text)

# تحسين الفلتر ليدعم الأسطر الجديدة (re.DOTALL)
@bot.on_message(filters.regex(r'^عداد\s*\(.*?\)\s*\(.*?\)$', re.DOTALL) | filters.regex(r'^عداد\s+.*?\s+.*?$', re.DOTALL))
async def set_timer_step1(client, message):
    # استخراج النصوص بين الأقواس بدقة حتى مع وجود أسطر جديدة
    parts = re.findall(r'\((.*?)\)', message.text, re.DOTALL)
    
    if len(parts) >= 2:
        event_name = parts[0].strip()
        time_str = parts[1].strip()
    else:
        # محاولة الاستخراج بدون أقواس في حال لم تتوفر
        match = re.search(r'^عداد\s+(.+?)\s+(.+?)$', message.text, re.DOTALL)
        if match:
            event_name = match.group(1).strip()
            time_str = match.group(2).strip()
        else:
            return await message.reply("صيغة غير صحيحة استخدم: `عداد (الحدث) (بعد المدة)` ❌")
        
    total_seconds = parse_advanced_arabic_time(time_str)
    
    if total_seconds is None:
        return await message.reply(f"لم أفهم الوقت: {time_str} ❌")

    user_states[message.from_user.id] = {
        "event": event_name,
        "total_seconds": total_seconds,
        "messages_to_delete": [message.id]
    }
    sent_msg = await message.reply("حدد مدة التذكير ⏰\n(مثلاً: كل 5 دقائق، كل ساعة، كل 10 ثواني)")
    user_states[message.from_user.id]["messages_to_delete"].append(sent_msg.id)

@bot.on_message(filters.text & ~filters.command(['start', 'help', 'مساعدة', 'stop', 'ايقاف']))
async def handle_responses(client, message):
    user_id = message.from_user.id
    
    if message.text.strip() == "حذف" and message.reply_to_message:
        reply_msg_id = message.reply_to_message.id
        found_timer_key = None
        for timer_key in list(active_timers.keys()):
            if reply_msg_id in active_timers[timer_key]["messages"]:
                found_timer_key = timer_key
                break
        
        if found_timer_key:
            active_timers[found_timer_key]["active"] = False
            for msg_id in active_timers[found_timer_key]["messages"]:
                try:
                    await client.delete_messages(message.chat.id, msg_id)
                except: pass
            try:
                await message.delete()
            except: pass
            del active_timers[found_timer_key]
            return
        else:
            if message.reply_to_message.from_user.id == (await client.get_me()).id:
                try:
                    await message.reply_to_message.delete()
                    await message.delete()
                except: pass
        return

    if user_id in user_states:
        state = user_states.pop(user_id)
        interval_str = message.text.replace("كل", "").strip()
        interval_seconds = parse_advanced_arabic_time(interval_str)
        
        if interval_seconds is None:
            user_states[user_id] = state
            sent_err = await message.reply(f"لم أفهم مدة التذكير: {message.text} حاول مرة أخرى (مثلاً: كل 5 دقائق) ❌")
            state["messages_to_delete"].append(message.id)
            state["messages_to_delete"].append(sent_err.id)
            return

        event = state["event"]
        total_seconds = state["total_seconds"]
        state["messages_to_delete"].append(message.id)
        
        start_msg = await message.reply(f"تم البدء سأذكرك بـ **{event}** كل **{message.text}** ✅")
        state["messages_to_delete"].append(start_msg.id)
        
        asyncio.create_task(run_countdown(client, message.chat.id, event, total_seconds, interval_seconds, state["messages_to_delete"]))

async def run_countdown(client, chat_id, event, total_seconds, interval_seconds, initial_messages):
    remaining = total_seconds
    timer_key = f"{chat_id}_{event}_{datetime.now().timestamp()}"
    active_timers[timer_key] = {
        "active": True, 
        "messages": initial_messages
    }
    
    while remaining > 0:
        if not active_timers[timer_key]["active"]:
            return

        d = remaining // 86400
        h = (remaining % 86400) // 3600
        m = (remaining % 3600) // 60
        s = remaining % 60
        
        display = ""
        if d > 0: display += f"{d} يوم "
        if h > 0: display += f"{h} ساعة "
        if m > 0: display += f"{m} دقيقة "
        if s > 0 or not display: display += f"{s} ثانية"
        
        text = f"**{event}**\n⏳ الوقت المتبقي: {display.strip()}"
        
        sent_msg = await client.send_message(
            chat_id, 
            text, 
            reply_markup=get_dynamic_timer_buttons(remaining)
        )
        
        active_timers[timer_key]["messages"].append(sent_msg.id)
        
        if remaining <= interval_seconds:
            await asyncio.sleep(remaining)
            remaining = 0
        else:
            await asyncio.sleep(interval_seconds)
            remaining -= interval_seconds

    if timer_key in active_timers and active_timers[timer_key]["active"]:
        try:
            members = []
            async for member in client.get_chat_members(chat_id):
                if not member.user.is_bot:
                    members.append(member.user.mention)
            
            final_text = f"**{event}**\n\nانتهـى الوقـت 🙅🏻‍♂️\nيا شـبـاب🔔"
            await client.send_message(chat_id, final_text)
            
            for i in range(0, len(members), 5):
                chunk = members[i:i+5]
                chunk_msg = " ".join(chunk)
                await client.send_message(chat_id, chunk_msg)
                await asyncio.sleep(1)
                
        except Exception as e:
            await client.send_message(chat_id, f"**{event}**\n\nانتهـى الوقـت 🙅🏻‍♂️\nيا شـبـاب🔔\n\n@all")
            
        del active_timers[timer_key]

@bot.on_message(filters.photo)
async def handle_photo(client, message):
    await message.reply("وصلت الصورة، لكنني بوت عداد تنازلي فقط. أرسل `عداد (الحدث) (المدة)` للبدء! ⏳")

if __name__ == "__main__":
    print("Polished Arabic Countdown Bot is starting...")
    bot.run()
