# -*- coding: utf-8 -*-
# بوت العداد الاحترافي - AL3DAD
# الإصدار: 2.0.1 (نسخة معدلة)

import os
import asyncio
import re
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait

# ====================== إعدادات البوت ======================
API_ID = 34257542
API_HASH = "614a1b5c5b712ac6de5530d5c571c42a"
BOT_TOKEN = "8662063487:AAFhVJQSQCpn52tv98ISkZO0ztAWCDml4UU"

# إعدادات متقدمة
الحد_الأقصى_للمؤقتات = 10  # أقصى عدد مؤقتات لكل مستخدم
أقصى_مدة = 365 * 86400     # سنة كحد أقصى
أقل_فترة_تذكير = 5        # أقل فترة تذكير (ثواني)
نسخة_البوت = "2.0.1"

# ====================== قاعدة البيانات ======================
class قاعدة_البيانات:
    def __init__(self):
        self.اتصال = sqlite3.connect("al3dad.db", check_same_thread=False)
        self.إنشاء_الجداول()
    
    def إنشاء_الجداول(self):
        cursor = self.اتصال.cursor()
        # جدول المؤقتات
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS المؤقتات (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                معرف_المجموعة INTEGER,
                معرف_المستخدم INTEGER,
                الحدث TEXT,
                وقت_الانتهاء INTEGER,
                فترة_التذكير INTEGER,
                معرف_الرسالة INTEGER,
                تاريخ_الإنشاء INTEGER,
                نشط INTEGER DEFAULT 1
            )
        """)
        self.اتصال.commit()
    
    def إضافة_مؤقت(self, معرف_المجموعة, معرف_المستخدم, الحدث, وقت_الانتهاء, فترة_التذكير, معرف_الرسالة):
        cursor = self.اتصال.cursor()
        cursor.execute("""
            INSERT INTO المؤقتات (معرف_المجموعة, معرف_المستخدم, الحدث, وقت_الانتهاء, فترة_التذكير, معرف_الرسالة, تاريخ_الإنشاء)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (معرف_المجموعة, معرف_المستخدم, الحدث, وقت_الانتهاء, فترة_التذكير, معرف_الرسالة, int(datetime.now().timestamp())))
        self.اتصال.commit()
        return cursor.lastrowid
    
    def جلب_المؤقتات_النشطة(self, معرف_المستخدم=None, معرف_المؤقت=None):
        cursor = self.اتصال.cursor()
        if معرف_المؤقت:
            cursor.execute("SELECT * FROM المؤقتات WHERE id = ? AND نشط = 1", (معرف_المؤقت,))
            return cursor.fetchone()
        elif معرف_المستخدم:
            cursor.execute("SELECT * FROM المؤقتات WHERE معرف_المستخدم = ? AND نشط = 1 ORDER BY وقت_الانتهاء", (معرف_المستخدم,))
            return cursor.fetchall()
        else:
            cursor.execute("SELECT * FROM المؤقتات WHERE نشط = 1")
            return cursor.fetchall()
    
    def إلغاء_مؤقت(self, معرف_المؤقت):
        cursor = self.اتصال.cursor()
        cursor.execute("UPDATE المؤقتات SET نشط = 0 WHERE id = ?", (معرف_المؤقت,))
        self.اتصال.commit()
    
    def إلغاء_مؤقتات_المستخدم(self, معرف_المستخدم):
        cursor = self.اتصال.cursor()
        cursor.execute("UPDATE المؤقتات SET نشط = 0 WHERE معرف_المستخدم = ? AND نشط = 1", (معرف_المستخدم,))
        self.اتصال.commit()
        return cursor.rowcount
    
    def تحديث_الرسالة(self, معرف_المؤقت, معرف_الرسالة):
        cursor = self.اتصال.cursor()
        cursor.execute("UPDATE المؤقتات SET معرف_الرسالة = ? WHERE id = ?", (معرف_الرسالة, معرف_المؤقت))
        self.اتصال.commit()

قاعدة = قاعدة_البيانات()

# ====================== الأدوات المساعدة ======================
# تجميع الأنماط العادية لتحسين الأداء
ARABIC_NUMBERS_TRANS = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
START_WORDS_REGEX = re.compile(r'^(بعد|في|خلال)\s+')
TOMORROW_REGEX = re.compile(r'(بكرة|بكرى|غدا)\s*')
TIME_REGEX = re.compile(r'(\d+)\s*(مساء|صباحا|صباحاً|م|ص)')
NUMBER_UNIT_REGEX = re.compile(r'(\d+)\s*(.*)')

def تحليل_الوقت(النص: str) -> Optional[int]:
    """تحليل النص الزمني بالعربية"""
    الآن = datetime.now()
    النص = النص.strip().lower()
    
    # تحويل الأرقام العربية
    النص = النص.translate(ARABIC_NUMBERS_TRANS)
    
    # إزالة كلمات البداية
    النص = START_WORDS_REGEX.sub('', النص)
    
    # التحقق من كلمة بكرة
    بكرة = bool(TOMORROW_REGEX.search(النص))
    if بكرة:
        النص = TOMORROW_REGEX.sub('', النص).strip()
    
    # تحليل الوقت (الساعة)
    وقت_محدد = TIME_REGEX.search(النص)
    if وقت_محدد:
        ساعة = int(وقت_محدد.group(1))
        الفترة = وقت_محدد.group(2)
        if 'مساء' in الفترة or الفترة == 'م':
            if ساعة < 12: ساعة += 12
        elif 'صباح' in الفترة or الفترة == 'ص':
            if ساعة == 12: ساعة = 0
        الوقت_المطلوب = الآن.replace(hour=ساعة, minute=0, second=0, microsecond=0)
        if بكرة or الوقت_المطلوب < الآن:
            الوقت_المطلوب += timedelta(days=1)
        return int((الوقت_المطلوب - الآن).total_seconds())
    
    # الحالات الخاصة
    حالات_خاصة = {
        'نص ساعة': 1800, 'نصف ساعة': 1800,
        'ربع ساعة': 900,
        'ساعتين': 7200, 'دقيقتين': 120, 'يومين': 172800,
        'خمس دقايق': 300, 'عشر دقايق': 600,
    }
    
    for مفتاح, قيمة in حالات_خاصة.items():
        if مفتاح in النص: # استخدام 'in' بدلاً من re.search لتحسين الأداء للحالات البسيطة
            return قيمة
    
    # تحليل الأرقام مع الوحدات
    وحدات_الوقت = {
        'ثانية': 1, 'ثواني': 1,
        'دقيقة': 60, 'دقائق': 60, 'دقايق': 60,
        'ساعة': 3600, 'ساعات': 3600,
        'يوم': 86400, 'أيام': 86400, 'ايام': 86400,
    }
    
    تطابق = NUMBER_UNIT_REGEX.search(النص)
    if تطابق:
        العدد = int(تطابق.group(1))
        الوحدة = تطابق.group(2).strip()
        for نمط, ثواني in وحدات_الوقت.items():
            if نمط in الوحدة: # استخدام 'in' بدلاً من re.search لتحسين الأداء للحالات البسيطة
                return العدد * ثواني
    
    return None

def تنسيق_الوقت(ثواني: int) -> str:
    """تنسيق الوقت بشكل مقروء"""
    أيام = ثواني // 86400
    ساعات = (ثواني % 86400) // 3600
    دقائق = (ثواني % 3600) // 60
    ثوان = ثواني % 60
    
    الأجزاء = []
    if أيام > 0:
        الأجزاء.append(f"{أيام} يوم")
    if ساعات > 0:
        الأجزاء.append(f"{ساعات} ساعة")
    if دقائق > 0:
        الأجزاء.append(f"{دقائق} دقيقة")
    if ثوان > 0 or not الأجزاء:
        الأجزاء.append(f"{ثوان} ثانية")
    
    return ' '.join(الأجزاء)

def أزرار_ديناميكية(الحدث: str, المتبقي: int) -> InlineKeyboardMarkup:
    """إنشاء أزرار ديناميكية"""
    أيام = المتبقي // 86400
    ساعات = (المتبقي % 86400) // 3600
    دقائق = (المتبقي % 3600) // 60
    ثوان = المتبقي % 60
    
    # زر الحدث
    الزر_العلوي = [InlineKeyboardButton(f"{الحدث[:30]} ⏰", callback_data="none")] # نقل الإيموجي بعد النص
    
    # أزرار الوقت
    if أيام > 0:
        الأزرار_السفلية = [
            InlineKeyboardButton(f"{أيام} ي 📅", callback_data="none"), # نقل الإيموجي بعد النص
            InlineKeyboardButton(f"{ساعات} س ⏱️", callback_data="none"), # نقل الإيموجي بعد النص
            InlineKeyboardButton(f"{دقائق} د ⏲️", callback_data="none") # نقل الإيموجي بعد النص
        ]
    else:
        الأزرار_السفلية = [
            InlineKeyboardButton(f"{ساعات} س ⏱️", callback_data="none"), # نقل الإيموجي بعد النص
            InlineKeyboardButton(f"{دقائق} د ⏲️", callback_data="none"), # نقل الإيموجي بعد النص
            InlineKeyboardButton(f"{ثوان} ث ⚡", callback_data="none") # نقل الإيموجي بعد النص
        ]
    
    return InlineKeyboardMarkup([الزر_العلوي, الأزرار_السفلية]))

# ====================== البوت ======================
البوت = Client("AL3DAD", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# تخزين المهام النشطة
المهام_النشطة = {}
حالات_المستخدمين = {}

@البوت.on_message(filters.command(['start', 'help', 'مساعدة']))
async def بدء_البوت(client, message: Message):
    """أمر بدء البوت"""
    نص_الترحيب = (
        "🎯 **مرحباً بك في بوت العداد الاحترافي!**\n\n"
        "✨ **المميزات:**\n"
        "• مؤقتات متعددة لكل مستخدم\n"
        "• تذكير دوري مرن\n"
        "• أزرار تفاعلية ديناميكية\n"
        "• حفظ تلقائي في قاعدة بيانات\n\n"
        "📝 **طريقة الاستخدام:**\n"
        "`عداد (الحدث) (المدة)`\n\n"
        "📌 **أمثلة:**\n"
        "• `عداد (اجتماع) (بعد 30 دقيقة)`\n"
        "• `عداد (صلاة) (الساعة 8 مساء)`\n"
        "• `عداد (مكالمة) (بعد ساعتين)`\n"
        "• `عداد (موعد) (بعد 5 دقائق و10 ثواني)`\n\n"
        "🛠️ **الأوامر:**\n"
        "• `/ايقاف` - إيقاف كل مؤقتاتك\n"
        "• `/قائمة` - عرض مؤقتاتك النشطة\n"
        "• `/الغاء [رقم]` - إلغاء مؤقت محدد\n\n"
        f"📊 **الإصدار:** {نسخة_البوت}"
    )
    await message.reply(نص_الترحيب, parse_mode="HTML")

@البوت.on_message(filters.command(['stop', 'ايقاف']))
async def ايقاف_الكل(client, message: Message):
    """إيقاف جميع المؤقتات"""
    معرف_المستخدم = message.from_user.id
    العدد = قاعدة.إلغاء_مؤقتات_المستخدم(معرف_المستخدم)
    
    # إلغاء المهام النشطة
    for معرف_المؤقت, المهمة in list(المهام_النشطة.items()):
        # يجب التحقق من معرف المستخدم قبل إلغاء المهمة
        # لأن المهام_النشطة قد تحتوي على مؤقتات لمستخدمين آخرين
        مؤقت_قاعدة_البيانات = قاعدة.جلب_المؤقتات_النشطة(معرف_المؤقت=معرف_المؤقت)
        if مؤقت_قاعدة_البيانات and مؤقت_قاعدة_البيانات[2] == معرف_المستخدم:
            if not المهمة.done():
                المهمة.cancel()
            del المهام_النشطة[معرف_المؤقت] # إزالة المهمة الملغاة من القاموس
    
    await message.reply(f"🛑 **تم إيقاف {العدد} مؤقت**\n\nيمكنك بدء مؤقت جديد بأمر `عداد (الحدث) (المدة)`")

@البوت.on_message(filters.command(['list', 'قائمة']))
async def عرض_القائمة(client, message: Message):
    """عرض المؤقتات النشطة"""
    معرف_المستخدم = message.from_user.id
    المؤقتات = قاعدة.جلب_المؤقتات_النشطة(معرف_المستخدم=معرف_المستخدم)
    
    if not المؤقتات:
        await message.reply("📭 **لا يوجد مؤقتات نشطة**\n\nابدأ مؤقتاً جديداً: `عداد (الحدث) (المدة)`")
        return
    
    قائمة_المؤقتات = []
    for مؤقت in المؤقتات:
        المتبقي = max(0, مؤقت[4] - int(datetime.now().timestamp()))
        قائمة_المؤقتات.append(
            f"🔹 **المعرف:** `{مؤقت[0]}`\n"
            f"📌 **الحدث:** {مؤقت[3]}\n"
            f"⏱️ **متبقي:** {تنسيق_الوقت(المتبقي)}\n"
            f"🔔 **تذكير:** كل {تنسيق_الوقت(مؤقت[5])}\n"
        )
    
    النص = f"📋 **مؤقتاتك النشطة:**\n\n{chr(10).join(قائمة_المؤقتات)}\n💡 لإيقاف مؤقت محدد استخدم: `/الغاء [المعرف]`"
    await message.reply(النص, parse_mode="HTML")

@البوت.on_message(filters.command(['cancel', 'الغاء']))
async def الغاء_مؤقت(client, message: Message):
    """إلغاء مؤقت محدد"""
    معرف_المستخدم = message.from_user.id
    
    # استخراج معرف المؤقت من الأمر
    if len(message.command) < 2:
        await message.reply("❌ **يرجى تحديد معرف المؤقت**\n\nمثال: `/الغاء 5`\nاستخدم `/قائمة` لعرض المؤقتات")
        return
    
    try:
        معرف_المؤقت = int(message.command[1])
    except ValueError:
        await message.reply("❌ **معرف غير صحيح**\nالمعرف يجب أن يكون رقماً")
        return
    
    # البحث عن المؤقت
    المؤقت = قاعدة.جلب_المؤقتات_النشطة(معرف_المؤقت=معرف_المؤقت)
    
    if not المؤقت or المؤقت[2] != معرف_المستخدم:
        await message.reply(f"❌ **لم أجد المؤقت** بالمعرف: `{معرف_المؤقت}`\n\nاستخدم `/قائمة` لعرض مؤقتاتك النشطة")
        return
    
    # إلغاء المؤقت
    قاعدة.إلغاء_مؤقت(معرف_المؤقت)
    
    # إلغاء المهمة إذا كانت نشطة
    if معرف_المؤقت in المهام_النشطة and not المهام_النشطة[معرف_المؤقت].done():
        المهام_النشطة[معرف_المؤقت].cancel()
        del المهام_النشطة[معرف_المؤقت] # إزالة المهمة الملغاة من القاموس
    
    await message.reply(f"✅ **تم إلغاء المؤقت** `{معرف_المؤقت}` بنجاح.")

@البوت.on_message(filters.regex(r'^عداد\s+\(?(.+?)\)?\s+\(?(.+?)\)?$')) # تبسيط regex
async def انشاء_مؤقت(client, message: Message):
    """إنشاء مؤقت جديد"""
    معرف_المستخدم = message.from_user.id
    
    # استخراج البيانات
    النص = message.text
    تطابق = re.search(r'^عداد\s+\(?(.+?)\)?\s+\(?(.+?)\)?$', النص)
    # لا حاجة للتحقق من تطابق هنا لأن الفلتر يضمن ذلك
    
    اسم_الحدث = تطابق.group(1).strip()
    مدة_الحدث = تطابق.group(2).strip()
    
    # تحليل الوقت
    ثواني_الحدث = تحليل_الوقت(مدة_الحدث)
    if ثواني_الحدث is None:
        await message.reply(f"❌ **لم أفهم المدة:** `{مدة_الحدث}`\n\nصيغ مقبولة:\n• بعد 30 دقيقة\n• الساعة 8 مساء\n• بعد ساعتين")
        return
    
    # التحقق من المدة
    if ثواني_الحدث > أقصى_مدة:
        await message.reply("⚠️ **المدة طويلة جداً!**\nالحد الأقصى هو سنة واحدة (365 يوم)")
        return
    
    # التحقق من عدد المؤقتات
    المؤقتات_النشطة = قاعدة.جلب_المؤقتات_النشطة(معرف_المستخدم=معرف_المستخدم)
    if len(المؤقتات_النشطة) >= الحد_الأقصى_للمؤقتات:
        await message.reply(f"⚠️ **لديك {len(المؤقتات_النشطة)} مؤقت نشط**\nالحد الأقصى هو {الحد_الأقصى_للمؤقتات} مؤقت لكل مستخدم\n\nاستخدم `/قائمة` لعرض مؤقتاتك أو `/ايقاف` لإيقافها")
        return
    
    # تخزين حالة المستخدم
    حالات_المستخدمين[معرف_المستخدم] = {
        "الحدث": اسم_الحدث,
        "ثواني_الحدث": ثواني_الحدث
    }
    await message.reply("⏰ **حدد مدة التذكير الدوري:**\n\nأمثلة:\n• `كل 5 دقائق`\n• `كل ساعة`\n• `كل 30 ثانية`\n\n✏️ أرسل المدة الآن:")

@البوت.on_message(filters.text & ~filters.command(['start', 'help', 'stop', 'ايقاف', 'list', 'قائمة', 'cancel', 'الغاء']))
async def معالجة_فترة_التذكير(client, message: Message):
    """معالجة تحديد فترة التذكير"""
    معرف_المستخدم = message.from_user.id
    
    # التحقق من وجود حالة
    if معرف_المستخدم not in حالات_المستخدمين:
        return
    
    الحالة = حالات_المستخدمين.pop(معرف_المستخدم)
    
    # تحليل فترة التذكير
    نص_الفترة = message.text.replace("كل", "").strip()
    ثواني_الفترة = تحليل_الوقت(نص_الفترة)
    
    if ثواني_الفترة is None or ثواني_الفترة < أقل_فترة_تذكير:
        await message.reply(f"❌ **لم أفهم المدة:** `{message.text}`\n\nالحد الأدنى للتذكير هو {أقل_فترة_تذكير} ثواني")
        return
    
    # إنشاء المؤقت
    وقت_الانتهاء = int(datetime.now().timestamp()) + الحالة["ثواني_الحدث"]
    الرسالة_المؤقتة = await message.reply("⏳ جاري البدء...")
    
    # حفظ في قاعدة البيانات
    معرف_المؤقت = قاعدة.إضافة_مؤقت(
        message.chat.id, معرف_المستخدم, الحالة["الحدث"],
        وقت_الانتهاء, ثواني_الفترة, الرسالة_المؤقتة.id
    )
    
    await الرسالة_المؤقتة.edit_text(
        f"✅ **تم البدء!**\n\n"
        f"📌 **الحدث:** {الحالة['الحدث']}\n"
        f"⏱️ **المدة:** {تنسيق_الوقت(الحالة['ثواني_الحدث'])}\n"
        f"🔔 **التذكير:** كل {تنسيق_الوقت(ثواني_الفترة)}\n"
        f"🆔 **المعرف:** `{معرف_المؤقت}`\n\n"
        f"💡 استخدم `/الغاء {معرف_المؤقت}` لإيقاف هذا المؤقت",
        parse_mode="HTML"
    )
    
    # تشغيل العد التنازلي
    المهمة = asyncio.create_task(تشغيل_المؤقت(
        client, معرف_المؤقت, message.chat.id, معرف_المستخدم,
        الحالة["الحدث"], وقت_الانتهاء, ثواني_الفترة, الرسالة_المؤقتة.id # تمرير معرف الرسالة الأولية
    ))
    المهام_النشطة[معرف_المؤقت] = المهمة

async def تشغيل_المؤقت(client, معرف_المؤقت, معرف_المجموعة, معرف_المستخدم, الحدث, وقت_الانتهاء, فترة_التذكير, معرف_الرسالة_الأولية):
    """تشغيل العد التنازلي"""
    try:
        # جلب معلومات المستخدم مرة واحدة
        try:
            المستخدم = await client.get_users(معرف_المستخدم)
            منشن = f"[{المستخدم.first_name}](tg://user?id={معرف_المستخدم})"
        except Exception:
            منشن = f"@{معرف_المستخدم}"

        current_message_id = معرف_الرسالة_الأولية

        while True:
            الآن = int(datetime.now().timestamp())
            المتبقي = وقت_الانتهاء - الآن
            
            if المتبقي <= 0:
                # انتهاء الوقت
                معلومات_المؤقت = قاعدة.جلب_المؤقتات_النشطة(معرف_المؤقت=معرف_المؤقت)
                if معلومات_المؤقت and معلومات_المؤقت[8] == 1:
                    await client.send_message(
                        معرف_المجموعة,
                        f"🚨 **انتهى الوقت!** 🚨\n\n📢 **{الحدث}**\n\n{منشن}\n\n⏰ حان الوقت للقيام بالمهمة!",
                        parse_mode="HTML"
                    )
                    قاعدة.إلغاء_مؤقت(معرف_المؤقت)
                break
            
            # إرسال تحديث
            المتبقي_منسق = تنسيق_الوقت(المتبقي)
            try:
                # استخدام edit_message_text بدلاً من delete ثم send
                await client.edit_message_text(
                    معرف_المجموعة,
                    current_message_id,
                    f"⏰ **{الحدث}**\n⏳ متبقي: {المتبقي_منسق}",
                    reply_markup=أزرار_ديناميكية(الحدث, المتبقي),
                    parse_mode="HTML"
                )
                
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                print(f"خطأ في تحديث المؤقت {معرف_المؤقت} (رسالة {current_message_id}): {e}")
            
            # انتظار الفترة المحددة
            await asyncio.sleep(min(فترة_التذكير, المتبقي))
            
    except asyncio.CancelledError:
        pass
    finally:
        if معرف_المؤقت in المهام_النشطة:
            del المهام_النشطة[معرف_المؤقت]

@البوت.on_callback_query()
async def معالجة_الأزرار(client, callback_query: CallbackQuery):
    """معالجة الأزرار"""
    await callback_query.answer()

@البوت.on_message(filters.text & filters.reply)
async def حذف_بالرد(client, message: Message):
    """حذف المؤقت بالرد"""
    if message.text.strip().lower() not in ["حذف", "delete"]:
        return
    
    if not message.reply_to_message:
        return
    
    # البحث عن المؤقت المرتبط بالرسالة
    معرف_الرد = message.reply_to_message.id
    المؤقتات = قاعدة.جلب_المؤقتات_النشطة()
    
    for مؤقت in المؤقتات:
        # مؤقت[6] هو معرف_الرسالة
        # مؤقت[2] هو معرف_المستخدم
        if مؤقت[6] == معرف_الرد and مؤقت[2] == message.from_user.id:
            قاعدة.إلغاء_مؤقت(مؤقت[0])
            if مؤقت[0] in المهام_النشطة:
                المهام_النشطة[مؤقت[0]].cancel()
                del المهام_النشطة[مؤقت[0]]
            
            try:
                await message.reply_to_message.delete()
                await message.reply("🗑️ **تم الحذف بنجاح**")
            except Exception as e:
                print(f"خطأ في حذف الرسالة: {e}")
                await message.reply("❌ **حدث خطأ أثناء حذف الرسالة.**")
            return
    await message.reply("❌ **لم أجد مؤقتًا مرتبطًا بهذه الرسالة أو ليس لديك صلاحية حذفه.**")

if __name__ == "__main__":
    print("🚀 بوت العداد الاحترافي يعمل...")
    print(f"📊 قاعدة البيانات: SQLite")
    print(f"⚙️ الحد الأقصى للمؤقتات: {الحد_الأقصى_للمؤقتات}")
    print(f"📌 الإصدار: {نسخة_البوت}")
    البوت.run()
