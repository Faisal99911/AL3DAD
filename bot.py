import asyncio
import re
from datetime import datetime, timedelta

import dateparser
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import Client, filters, enums
from pyrogram.types import Message

# ----------------- الإعدادات ----------------- #

API_ID = 34257542
API_HASH = "614a1b5c5b712ac6de5530d5c571c42a"
BOT_TOKEN = "8618854908:AAE_vNB2Skzqu_1wKCEOZRYQqwjH_oZOWjU"
ADMIN_ID = 1486879970

app = Client("countdown_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
scheduler = AsyncIOScheduler()

# تخزين الحالات والمهام
user_states = {}  # {user_id: {chat_id: {data}}}
active_tasks = {} # {task_id: {data}}
task_counter = 0

# ----------------- الصلاحيات ----------------- #

async def is_allowed(_, __, message: Message):
    if message.from_user and message.from_user.id == ADMIN_ID:
        return True
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        try:
            member = await app.get_chat_member(message.chat.id, message.from_user.id)
            return member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
        except: return False
    return message.chat.type == enums.ChatType.PRIVATE

# ----------------- أدوات التحليل ----------------- #

def parse_time(text):
    return dateparser.parse(
        text,
        languages=["ar", "en"],
        settings={"PREFER_DATES_FROM": "future", "RELATIVE_BASE": datetime.now()}
    )

def parse_interval(text):
    """تحليل المدة الزمنية للتنبيه (مثلاً: كل 5 دقائق)"""
    text = text.replace("كل", "").strip()
    
    # تحويل الكلمات الشائعة لأرقام
    words_map = {
        "دقيقة": 1, "دقيقتين": 2, "دقائق": 1, "دقايق": 1,
        "ساعة": 60, "ساعتين": 120, "ساعات": 60,
        "نص ساعة": 30, "ربع ساعة": 15, "نصف ساعة": 30
    }
    
    # البحث عن رقم في النص
    nums = re.findall(r'\d+', text)
    if nums:
        val = int(nums[0])
        if "ساعة" in text or "ساعات" in text:
            return val * 60
        return val
    
    # البحث عن كلمات بدون أرقام
    for word, mins in words_map.items():
        if word in text:
            return mins
    
    return None

def format_remaining(target):
    diff = target - datetime.now()
    if diff.total_seconds() <= 0: return "انتهى الوقت!"
    days = diff.days
    hours = int(diff.total_seconds() // 3600) % 24
    minutes = int((diff.total_seconds() % 3600) // 60)
    return f"{days} يوم و {hours} ساعة و {minutes} دقيقة"

# ----------------- وظائف التنبيه ----------------- #

async def send_reminder(chat_id, task_id):
    task = active_tasks.get(task_id)
    if not task or not task["active"]: return

    remaining = format_remaining(task["target"])
    if "انتهى" in remaining:
        await app.send_message(chat_id, f"🚨 انتهى الوقت لـ: {task['content']}")
        task["active"] = False
        scheduler.remove_job(str(task_id))
        return

    await app.send_message(chat_id, f"🔔 تنبيه لـ: {task['content']}\n⏳ المتبقي: {remaining}")

# ----------------- معالجة الأوامر ----------------- #

@app.on_message(filters.text & ~filters.reply)
async def handle_message(client, message: Message):
    if not await is_allowed(None, None, message): return
    
    text = message.text.strip()
    user_id = message.from_user.id
    chat_id = message.chat.id

    # أمر التجربة السريع
    if text == "ج":
        return await message.reply("هلا")

    # الحالة 1: استقبال أمر العداد الجديد (مثلاً: عداد مكالمة بعد ساعة)
    if text.startswith("عداد"):
        parts = text.split(" ", 2)
        if len(parts) < 3:
            return await message.reply("يرجى كتابة الأمر كالتالي: عداد [الوصف] [الوقت]\nمثال: عداد مكالمة بعد ساعة")
        
        content = parts[1]
        time_str = parts[2]
        target_time = parse_time(time_str)

        if not target_time:
            return await message.reply(f"❌ لم أفهم الوقت: {time_str}")

        # حفظ الحالة لانتظار الفاصل الزمني
        user_states[user_id] = {
            "step": "waiting_interval",
            "content": content,
            "target": target_time,
            "chat_id": chat_id
        }
        await message


reply(f"✅ تم ضبط عداد لـ ({content}) في وقت {target_time.strftime('%Y-%m-%d %H:%M')}\n\n**متى تبغى أرسل لك تنبيه؟**\n(مثلاً: كل 5 دقائق، كل ساعة، كل نص ساعة)")

    # الحالة 2: استقبال الفاصل الزمني (مثلاً: كل خمس دقائق)
    elif user_id in user_states and user_states[user_id]["step"] == "waiting_interval":
        state = user_states[user_id]
        interval_mins = parse_interval(text)

        if not interval_mins:
            return await message.reply("❌ لم أفهم المدة. جرب: (كل 10 دقائق) أو (كل ساعة)")

        global task_counter
        task_counter += 1
        task_id = task_counter

        active_tasks[task_id] = {
            "content": state["content"],
            "target": state["target"],
            "active": True
        }

        # جدولة التنبيهات المتكررة
        scheduler.add_job(
            send_reminder,
            "interval",
            minutes=interval_mins,
            args=[chat_id, task_id],
            id=str(task_id)
        )

        await message.reply(f"🚀 تم التفعيل! سأرسل تنبيه لـ ({state['content']}) كل {interval_mins} دقيقة حتى يحين الموعد.")
        del user_states[user_id]

@app.on_message(filters.reply & filters.regex("^حذف$"))
async def delete_task(client, message: Message):
    await message.reply("للحذف، يرجى إيقاف البوت أو مسح المهام يدوياً في هذه النسخة.")

# ----------------- تشغيل ----------------- #

async def main():
    if not scheduler.running:
        scheduler.start()
    await app.start()
    print("✅ البوت التفاعلي يعمل الآن...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
