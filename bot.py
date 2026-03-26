# نفس إعداداتك بدون تغيير 🔒
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio, re
from datetime import datetime
from pyrogram.errors import FloodWait

API_ID = 34257542
API_HASH = "614a1b5c5b712ac6de5530d5c571c42a"
BOT_TOKEN = "8662063487:AAFhVJQSQCpn52tv98ISkZO0ztAWCDml4UU"

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_states = {}
active_timers = {}

# ----------- الوقت -----------

def parse_time(text):
    text = text.replace("كل", "").strip()

    if "ثاني" in text:
        return int(re.search(r'\d+', text).group()) if re.search(r'\d+', text) else None
    if "دقيق" in text:
        return int(re.search(r'\d+', text).group()) * 60 if re.search(r'\d+', text) else None
    if "ساع" in text:
        return int(re.search(r'\d+', text).group()) * 3600 if re.search(r'\d+', text) else None

    return None

def format_time(s):
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60

    parts = []
    if h: parts.append(f"{h} ساعة")
    if m: parts.append(f"{m} دقيقة")
    if sec or not parts: parts.append(f"{sec} ثانية")

    return " • ".join(parts)

# ----------- أزرار -----------

def buttons(event, s):
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(event, callback_data="x")],
        [
            InlineKeyboardButton(f"{h} ساعة", callback_data="x"),
            InlineKeyboardButton(f"{m} دقيقة", callback_data="x"),
            InlineKeyboardButton(f"{sec} ثانية", callback_data="x"),
        ]
    ])

# ----------- البداية -----------

@bot.on_message(filters.regex(r'^عداد\s+\((.+)\)\s+\((.+)\)$'))
async def start_timer(client, message):
    event = re.search(r'\((.+)\)', message.text).group(1)
    time_text = re.findall(r'\((.+)\)', message.text)[1]

    total = parse_time(time_text)
    if not total:
        return await message.reply("❌ ما فهمت الوقت")

    user_states[message.from_user.id] = {
        "event": event,
        "total": total
    }

    await message.reply("اكتب مدة التذكير ⏱️")

# ----------- الرد -----------

@bot.on_message(filters.text)
async def handle(client, message):
    user_id = message.from_user.id

    # حذف شامل
    if message.text == "حذف" and message.reply_to_message:
        msg_id = message.reply_to_message.id

        for key in list(active_timers):
            if msg_id in active_timers[key]["msgs"]:
                for m in active_timers[key]["msgs"]:
                    try: await client.delete_messages(message.chat.id, m)
                    except: pass
                for m in active_timers[key]["user_msgs"]:
                    try: await client.delete_messages(message.chat.id, m)
                    except: pass
                del active_timers[key]
                return await message.reply("تم الحذف ✅")

    # التذكير
    if user_id in user_states:
        state = user_states[user_id]

        interval = parse_time(message.text)
        if not interval:
            return await message.reply("❌ اكتب مثل: كل 10 ثواني")

        del user_states[user_id]

        key = str(datetime.now().timestamp())
        active_timers[key] = {
            "msgs": [],
            "user_msgs": [message.id],
            "event": state["event"]
        }

        await message.reply(f"{state['event']} ⏳\n\nبدأ العداد ✅")

        asyncio.create_task(run(client, message.chat.id, key, state["event"], state["total"], interval))

# ----------- العداد -----------

async def run(client, chat_id, key, event, total, interval):
    remaining = total

    while remaining > 0:
        text = f"{event} ⏳\n\n{format_time(remaining)} ⏱️"

        try:
            msg = await client.send_message(chat_id, text, reply_markup=buttons(event, remaining))
        except FloodWait as e:
            await asyncio.sleep(e.value)
            continue

        active_timers[key]["msgs"] = [msg.id]

        await asyncio.sleep(min(interval, remaining))
        remaining -= interval

    # منشن ذكي
    members = []
    async for m in client.get_chat_members(chat_id):
        if not m.user.is_bot:
            if m.user.username:
                members.append(f"@{m.user.username}")

    for i in range(0, len(members), 5):
        chunk = " ".join(members[i:i+5])
        await client.send_message(chat_id, f"🚨 انتهى الوقت\n\n{event}\n\n{chunk}")

    if key in active_timers:
        del active_timers[key]

# -----------

bot.run()
