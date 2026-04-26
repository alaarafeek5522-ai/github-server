import os, logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ['TELEGRAM_TOKEN']

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 أهلاً {name}!\n\n"
        "أنا بوت شغال على GitHub Actions 🚀\n\n"
        "الأوامر:\n"
        "/start - البداية\n"
        "/ping - تحقق من السيرفر\n"
        "/echo - كرر كلامك"
    )

async def ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ البوت شغال!\n🖥️ Server: GitHub Actions")

async def echo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"↩️ {update.message.text}")

async def unknown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ أمر غير معروف، جرب /start")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ping", ping))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
app.add_handler(MessageHandler(filters.COMMAND, unknown))

print("🤖 Bot started!")
app.run_polling(drop_pending_updates=True)
