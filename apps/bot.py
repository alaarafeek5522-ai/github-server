"""
bot.py
بوت تليجرام لإدارة مفاتيح التفعيل (License Keys) عن طريق GitHub Gist
كل الإعدادات الحساسة (التوكنات) بتتقرأ من متغيرات البيئة، مش مكتوبة في الكود.
"""

import os
import json
import random
import string
import logging
from datetime import datetime, timedelta

import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ------------------------------------------------------------------
# الإعدادات - بتتقرأ من متغيرات البيئة (Environment Variables)
# ------------------------------------------------------------------
BOT_TOKEN = os.environ["7882229756:AAFdnemAbt75LvCm7dtrrKbuOxkiR4lqsCk"]          # توكن بوت تليجرام
GIST_ID = os.environ["c3271d0dced87c1e4e46ab073b885cbf"]              # آيدي الـ Gist
GITHUB_TOKEN = os.environ["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"]    # توكن GitHub
FILE_NAME = os.environ.get("GIST_FILE_NAME", "keys.json")

# قايمة آيدي المستخدمين المسموح لهم يستخدموا البوت (الأدمنز)
# مثال في Railway: ADMIN_IDS=123456789,987654321
ADMIN_IDS = {
    int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()
}

GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# دوال التعامل مع GitHub Gist
# ------------------------------------------------------------------
def get_data():
    r = requests.get(
        f"https://api.github.com/gists/{GIST_ID}",
        headers=GITHUB_HEADERS,
        timeout=20,
    )
    r.raise_for_status()
    gist = r.json()
    content = gist["files"][FILE_NAME]["content"]
    return json.loads(content) if content.strip() else {"keys": {}}


def save_data(data):
    r = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers=GITHUB_HEADERS,
        json={
            "files": {
                FILE_NAME: {
                    "content": json.dumps(data, ensure_ascii=False, indent=2)
                }
            }
        },
        timeout=20,
    )
    r.raise_for_status()


def calc_expiry(duration, unit):
    now = datetime.now()
    if unit == "hours":
        return now + timedelta(hours=duration)
    if unit == "weeks":
        return now + timedelta(weeks=duration)
    if unit == "months":
        return now + timedelta(days=30 * duration)
    return now + timedelta(days=duration)


def random_block():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=4))


def generate_key(prefix):
    return f"{prefix}-{random_block()}-{random_block()}"


# ------------------------------------------------------------------
# صلاحيات
# ------------------------------------------------------------------
def is_admin(user_id: int) -> bool:
    # لو محدش متسجل في ADMIN_IDS، خلي البوت مفتوح لأي حد (احتياطي)
    if not ADMIN_IDS:
        return True
    return user_id in ADMIN_IDS


async def deny(update: Update):
    await update.message.reply_text("❌ مش معاك صلاحية تستخدم البوت ده.")


# ------------------------------------------------------------------
# أوامر البوت
# ------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 أهلاً بيك في بوت إدارة مفاتيح التفعيل\n\n"
        "الأوامر المتاحة:\n"
        "/list — عرض كل المفاتيح\n"
        "/add KEY DURATION UNIT — إضافة مفتاح جديد\n"
        "  مثال: /add ABCD-1234-XYZ0 30 days\n"
        "/block KEY — حظر مفتاح\n"
        "/unblock KEY — إلغاء حظر مفتاح\n"
        "/delete KEY — حذف مفتاح\n"
        "/reset KEY — إعادة تعيين الجهاز المرتبط بالمفتاح\n"
        "/renew KEY DURATION UNIT — تجديد مفتاح\n"
        "/bulk — توليد 90 مفتاح (30 شهري / 30 أسبوعي / 30 يومي)\n"
    )
    await update.message.reply_text(text)


async def list_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await deny(update)

    data = get_data()
    keys = data.get("keys", {})
    if not keys:
        return await update.message.reply_text("لا يوجد أي مفاتيح مسجلة حتى الآن.")

    lines = []
    for k, v in keys.items():
        status = "✅ مفعل" if v.get("active") else "🚫 محظور"
        lines.append(f"`{k}` | {status} | {v.get('duration','-')} {v.get('unit','-')}")

    # تليجرام بيحدد طول الرسالة، فهنقسمها لو كبيرة
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) > 3500:
            await update.message.reply_text(chunk, parse_mode="Markdown")
            chunk = ""
        chunk += line + "\n"
    if chunk:
        await update.message.reply_text(chunk, parse_mode="Markdown")


async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await deny(update)

    args = context.args
    if len(args) != 3:
        return await update.message.reply_text(
            "الاستخدام:\n/add KEY DURATION UNIT\nمثال: /add ABCD-1234-XYZ0 30 days"
        )

    key, duration_str, unit = args[0].upper(), args[1], args[2].lower()
    if unit not in ("hours", "days", "weeks", "months"):
        return await update.message.reply_text("الوحدة لازم تكون: hours / days / weeks / months")

    try:
        duration = int(duration_str)
    except ValueError:
        return await update.message.reply_text("المدة لازم تكون رقم.")

    data = get_data()
    data.setdefault("keys", {})

    if key in data["keys"]:
        return await update.message.reply_text("⚠️ المفتاح ده موجود بالفعل.")

    data["keys"][key] = {
        "active": True,
        "device_id": None,
        "registered_at": None,
        "expires_at": None,
        "duration": duration,
        "unit": unit,
    }
    save_data(data)
    await update.message.reply_text(f"✅ تم إضافة المفتاح:\n`{key}`", parse_mode="Markdown")


async def _toggle_block(update: Update, context: ContextTypes.DEFAULT_TYPE, state: bool):
    if not is_admin(update.effective_user.id):
        return await deny(update)

    if len(context.args) != 1:
        return await update.message.reply_text("الاستخدام: /block KEY أو /unblock KEY")

    key = context.args[0].upper()
    data = get_data()
    if key not in data.get("keys", {}):
        return await update.message.reply_text("المفتاح مش موجود.")

    data["keys"][key]["active"] = state
    save_data(data)
    msg = "✅ تم إلغاء الحظر." if state else "🚫 تم حظر المفتاح."
    await update.message.reply_text(msg)


async def block_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _toggle_block(update, context, False)


async def unblock_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _toggle_block(update, context, True)


async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await deny(update)

    if len(context.args) != 1:
        return await update.message.reply_text("الاستخدام: /delete KEY")

    key = context.args[0].upper()
    data = get_data()
    if key not in data.get("keys", {}):
        return await update.message.reply_text("المفتاح مش موجود.")

    del data["keys"][key]
    save_data(data)
    await update.message.reply_text("🗑️ تم حذف المفتاح.")


async def reset_device(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await deny(update)

    if len(context.args) != 1:
        return await update.message.reply_text("الاستخدام: /reset KEY")

    key = context.args[0].upper()
    data = get_data()
    if key not in data.get("keys", {}):
        return await update.message.reply_text("المفتاح مش موجود.")

    data["keys"][key]["device_id"] = None
    data["keys"][key]["registered_at"] = None
    save_data(data)
    await update.message.reply_text("♻️ تم إعادة تعيين الجهاز المرتبط بالمفتاح.")


async def renew_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await deny(update)

    args = context.args
    if len(args) != 3:
        return await update.message.reply_text(
            "الاستخدام:\n/renew KEY DURATION UNIT\nمثال: /renew ABCD-1234-XYZ0 30 days"
        )

    key, duration_str, unit = args[0].upper(), args[1], args[2].lower()
    if unit not in ("hours", "days", "weeks", "months"):
        return await update.message.reply_text("الوحدة لازم تكون: hours / days / weeks / months")

    try:
        duration = int(duration_str)
    except ValueError:
        return await update.message.reply_text("المدة لازم تكون رقم.")

    data = get_data()
    if key not in data.get("keys", {}):
        return await update.message.reply_text("المفتاح مش موجود.")

    data["keys"][key].update({
        "duration": duration,
        "unit": unit,
        "registered_at": None,
        "expires_at": None,
        "device_id": None,
        "active": True,
    })
    save_data(data)
    await update.message.reply_text("🔄 تم تجديد المفتاح. العداد هيبدأ من أول تفعيل.")


async def bulk_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await deny(update)

    data = get_data()
    data.setdefault("keys", {})

    categories = [
        (30, 1, "months", "MONTH"),
        (30, 1, "weeks", "WEEK"),
        (30, 1, "days", "DAY"),
    ]

    generated = []
    for count, duration, unit, prefix in categories:
        for _ in range(count):
            while True:
                key = generate_key(prefix)
                if key not in data["keys"]:
                    break
            data["keys"][key] = {
                "active": True,
                "device_id": None,
                "registered_at": None,
                "expires_at": None,
                "duration": duration,
                "unit": unit,
            }
            generated.append(key)

    save_data(data)

    text = f"✅ تم توليد {len(generated)} مفتاح.\n\nهيتبعتلك ملف فيه كل المفاتيح."
    await update.message.reply_text(text)

    # بعت المفاتيح في ملف نصي عشان الرسالة متبقاش طويلة أوي
    file_content = "\n".join(generated)
    with open("/tmp/generated_keys.txt", "w", encoding="utf-8") as f:
        f.write(file_content)
    await update.message.reply_document(document=open("/tmp/generated_keys.txt", "rb"))


# ------------------------------------------------------------------
# تشغيل البوت
# ------------------------------------------------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_keys))
    app.add_handler(CommandHandler("add", add_key))
    app.add_handler(CommandHandler("block", block_key))
    app.add_handler(CommandHandler("unblock", unblock_key))
    app.add_handler(CommandHandler("delete", delete_key))
    app.add_handler(CommandHandler("reset", reset_device))
    app.add_handler(CommandHandler("renew", renew_key))
    app.add_handler(CommandHandler("bulk", bulk_generate))

    logger.info("البوت شغال دلوقتي...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
