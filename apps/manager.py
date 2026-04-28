import os, subprocess, sys, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ['TELEGRAM_TOKEN']
OWNER_ID = 7584844132

processes = {}  # {name: process}
bot_files = {}  # {name: filepath}

def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📋 بوتاتي', callback_data='list'),
         InlineKeyboardButton('📊 الحالة', callback_data='status')],
        [InlineKeyboardButton('❓ مساعدة', callback_data='help')],
    ])

def kb_bot(name):
    running = name in processes and processes[name].poll() is None
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('⏹️ إيقاف' if running else '▶️ تشغيل',
         callback_data=f'stop_{name}' if running else f'start_{name}')],
        [InlineKeyboardButton('🗑️ حذف', callback_data=f'delete_{name}'),
         InlineKeyboardButton('📄 اسم الملف', callback_data=f'info_{name}')],
        [InlineKeyboardButton('🔙 رجوع', callback_data='list')],
    ])

async def start(update: Update, _):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text('⛔ مش مصرح لك')
        return
    await update.message.reply_text(
        '👑 *Bot Hosting Manager*\n\n'
        'ابعتلي ملف `.py` وهشغله فوراً!\n\n'
        '📌 الأوامر:\n'
        '/start - القائمة الرئيسية\n'
        '/list - كل البوتات\n'
        '/status - الحالة',
        parse_mode='Markdown',
        reply_markup=kb_main()
    )

async def handle_file(update: Update, _):
    if update.effective_user.id != OWNER_ID:
        return
    doc = update.message.document
    if not doc.file_name.endswith('.py'):
        await update.message.reply_text('⚠️ بعتلي ملف .py بس!')
        return

    name = doc.file_name.replace('.py', '').replace(' ', '_')
    path = f'apps/bots/{name}.py'
    os.makedirs('apps/bots', exist_ok=True)

    file = await doc.get_file()
    await file.download_to_drive(path)

    msg = await update.message.reply_text(f'📥 جاري رفع *{name}*...', parse_mode='Markdown')

    if name in processes and processes[name].poll() is None:
        processes[name].terminate()

    p = subprocess.Popen([sys.executable, path], env=os.environ.copy())
    processes[name] = p
    bot_files[name] = path

    await msg.edit_text(
        f'✅ *{name}* شغال!\n\n'
        f'🆔 PID: `{p.pid}`\n'
        f'📄 الملف: `{path}`',
        parse_mode='Markdown',
        reply_markup=kb_bot(name)
    )

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == 'list':
        if not bot_files:
            await q.edit_message_text(
                '📋 *مفيش بوتات لحد دلوقتي*\n\nابعتلي ملف .py!',
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='back')]])
            )
            return
        kb = []
        for name in bot_files:
            running = name in processes and processes[name].poll() is None
            status = '🟢' if running else '🔴'
            kb.append([InlineKeyboardButton(f'{status} {name}', callback_data=f'bot_{name}')])
        kb.append([InlineKeyboardButton('🔙 رجوع', callback_data='back')])
        await q.edit_message_text('📋 *بوتاتك:*', parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(kb))

    elif data == 'status':
        running = sum(1 for n,p in processes.items() if p.poll() is None)
        stopped = len(bot_files) - running
        text = (
            f'📊 *إحصائيات:*\n\n'
            f'🟢 شغال: {running}\n'
            f'🔴 موقف: {stopped}\n'
            f'📦 إجمالي: {len(bot_files)}\n\n'
        )
        for name in bot_files:
            r = name in processes and processes[name].poll() is None
            pid = processes[name].pid if r else '-'
            text += f'{"🟢" if r else "🔴"} `{name}` | PID: {pid}\n'
        await q.edit_message_text(text, parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='back')]]))

    elif data == 'help':
        await q.edit_message_text(
            '❓ *طريقة الاستخدام:*\n\n'
            '1️⃣ ابعتلي ملف `.py` مباشرة\n'
            '2️⃣ هرفعه وأشغله تلقائياً\n'
            '3️⃣ تحكم فيه من لوحة التحكم\n\n'
            '⚠️ *ملاحظات:*\n'
            '• الملف لازم يكون بوت تيليغرام\n'
            '• التوكن يكون جوا الملف\n'
            '• كل بوت بيشتغل مستقل',
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='back')]]))

    elif data == 'back':
        await q.edit_message_text(
            '👑 *Bot Hosting Manager*\n\nابعتلي ملف `.py` وهشغله فوراً!',
            parse_mode='Markdown', reply_markup=kb_main())

    elif data.startswith('bot_'):
        name = data.replace('bot_', '')
        running = name in processes and processes[name].poll() is None
        await q.edit_message_text(
            f'🤖 *{name}*\n\n'
            f'الحالة: {"🟢 شغال" if running else "🔴 موقف"}\n'
            f'الملف: `{bot_files.get(name, "-")}`',
            parse_mode='Markdown', reply_markup=kb_bot(name))

    elif data.startswith('start_'):
        name = data.replace('start_', '')
        if name in bot_files:
            p = subprocess.Popen([sys.executable, bot_files[name]], env=os.environ.copy())
            processes[name] = p
            await q.answer(f'✅ {name} شغال!', show_alert=True)
            await q.edit_message_text(
                f'🤖 *{name}*\n\nالحالة: 🟢 شغال\nPID: `{p.pid}`',
                parse_mode='Markdown', reply_markup=kb_bot(name))

    elif data.startswith('stop_'):
        name = data.replace('stop_', '')
        if name in processes and processes[name].poll() is None:
            processes[name].terminate()
            await q.answer(f'⏹️ {name} وقف', show_alert=True)
            await q.edit_message_text(
                f'🤖 *{name}*\n\nالحالة: 🔴 موقف',
                parse_mode='Markdown', reply_markup=kb_bot(name))

    elif data.startswith('delete_'):
        name = data.replace('delete_', '')
        if name in processes and processes[name].poll() is None:
            processes[name].terminate()
        if name in bot_files:
            try: os.remove(bot_files[name])
            except: pass
            del bot_files[name]
        if name in processes:
            del processes[name]
        await q.answer(f'🗑️ {name} اتحذف', show_alert=True)
        await q.edit_message_text(
            '👑 *Bot Hosting Manager*',
            parse_mode='Markdown', reply_markup=kb_main())

    elif data.startswith('info_'):
        name = data.replace('info_', '')
        await q.answer(f'📄 {bot_files.get(name, "-")}', show_alert=True)

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('list', lambda u,c: button(u,c) if setattr(u.callback_query if hasattr(u,'callback_query') else type('',(),{'data':'list','answer':asyncio.coroutine(lambda *a,**k: None),'edit_message_text':asyncio.coroutine(lambda *a,**k: None)})(), 'data', 'list') or True else None))
app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
app.add_handler(CallbackQueryHandler(button))

print('👑 Bot Hosting Manager شغال!')
app.run_polling(drop_pending_updates=True)
