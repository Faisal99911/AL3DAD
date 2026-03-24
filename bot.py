import re
from datetime import datetime

import dateparser
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import Client, filters

# ----------------- الإعدادات ----------------- #

API_ID = 34257542
API_HASH = "614a1b5c5b712ac6de5530d5c571c42a"
BOT_TOKEN = "8618854908:AAE_vNB2Skzqu_1wKCEOZRYQqwjH_oZOWjU"
ADMIN_ID = 1486879970

app = Client("countdown_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
scheduler = AsyncIOScheduler()

tasks = {}
task_counter = 0

# ----------------- الصلاحيات ----------------- #

async def is_allowed(_, __, message):
    if message.from_user.id == ADMIN_ID:
        return True

    if message.chat.type in ["group", "supergroup"]:
        member = await app.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ["administrator", "creator"]

    return False


allowed = filters.create(is_allowed)

# ----------------- أدوات ----------------- #

def parse_time(text):
    return dateparser.parse(
        text,
        languages=["ar", "en"],
        settings={
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": datetime.now(),
        },
    )


def format_time(diff):
    days = diff.days
    hours = int(diff.total_seconds() // 3600) % 24
    minutes = int((diff.total_seconds() % 3600) // 60)
    seconds = int(diff.total_seconds() % 60)

    return (
        f"⏳ باقي:\n"
        f"📅 {days} يوم\n"
        f"⏰ {hours} ساعة\n"
        f"⌛ {minutes} دقيقة\n"
        f"⏱️ {seconds} ثانية"
    )


async def update_counter(client, chat_id, message_id, task_id):
    task = tasks.get(task_id)

    if not task or not task["active"]:
        return

    diff = task["target"] - datetime.now()

    # انتهاء العداد
    if diff.total_seconds() <= 0:
        try:
            await client.edit_message_text(
                chat_id,
                message_id,
                f"⏰ انتهى الوقت!\n{task['content']}"
            )
            await client.send_message(chat_id, "🚨 انتهى العداد!")
        except:
            pass

        task["active"] = False
        return

    try:
        await client.edit_message_text(
            chat_id,
            message_id,
            format_time(diff)
        )
    except:
        pass


# ----------------- إنشاء العداد ----------------- #

@app.on_message(allowed & filters.regex(r"عداد \((.*)\) \((.*)\)"))
async def start_counter(client, message):
    global task_counter

    text = message.matches[0].group(1)
    time_str = message.matches[0].group(2)

    target = parse_time(time_str)

    if not target:
        return await message.reply("❌ ما فهمت الوقت")

    sent = await message.reply("⏳ جاري بدء العداد...")

    task_counter += 1
    task_id = task_counter

    tasks[task_id] = {
        "target": target,
        "content": text,
        "chat_id": message.chat.id,
        "message_id": sent.id,
        "active": True,
    }

    scheduler.add_job(
        update_counter,
        "interval",
        seconds=1,
        args=[client, message.chat.id, sent.id, task_id],
        id=str(task_id),
    )


# ----------------- حذف العداد ----------------- #

@app.on_message(allowed & filters.reply & filters.regex("حذف"))
async def delete_counter(client, message):
    replied = message.reply_to_message

    for tid, task in list(tasks.items()):
        if (
            task["chat_id"] == message.chat.id
            and task["message_id"] == replied.id
        ):
            try:
                scheduler.remove_job(str(tid))
            except:
                pass

            try:
                await replied.delete()
                await message.delete()
            except:
                pass

            del tasks[tid]
            return


# ----------------- تشغيل ----------------- #

if __name__ == "__main__":
    scheduler.start()
    app.run()
