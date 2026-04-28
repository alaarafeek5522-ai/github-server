import os, subprocess, sys, asyncio, re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ['TELEGRAM_TOKEN']
OWNER_ID = 7584844132

processes = {}
bot_files = {}
pending_file = {}  # لو المستخدم بعت ملف وبننتظر requirements

def extract_imports(filepath):
    libs = set()
    builtin = {
        'os','sys','re','json','time','datetime','asyncio','subprocess',
        'threading','random','string','math','collections','functools',
        'itertools','pathlib','shutil','glob','io','base64','hashlib',
        'urllib','http','socket','struct','typing','abc','copy','enum',
        'logging','warnings','traceback','inspect','gc','weakref','signal'
    }
    mapping = {
        'telegram': 'python-telegram-bot',
        'telebot': 'pyTelegramBotAPI',
        'flask': 'flask',
        'requests': 'requests',
        'bs4': 'beautifulsoup4',
        'PIL': 'Pillow',
        'cv2': 'opencv-python-headless',
        'numpy': 'numpy',
        'pandas': 'pandas',
        'aiohttp': 'aiohttp',
        'dotenv': 'python-dotenv',
        'sqlalchemy': 'sqlalchemy',
        'pymongo': 'pymongo',
        'redis': 'redis',
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn',
        'pydantic': 'pydantic',
        'httpx': 'httpx',
        'aiogram': 'aiogram',
        'discord': 'discord.py',
        'openai': 'openai',
        'anthropic': 'anthropic',
        'google': 'google-generativeai',
        'sklearn': 'scikit-learn',
        'matplotlib': 'matplotlib',
        'seaborn': 'seaborn',
        'scipy': 'scipy',
        'yaml': 'pyyaml',
        'toml': 'toml',
        'cryptography': 'cryptography',
        'jwt': 'PyJWT',
        'qrcode': 'qrcode',
        'barcode': 'python-barcode',
    }
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                m1 = re.match(r'^import\s+([\w]+)', line)
                m2 = re.match(r'^from\s+([\w]+)', line)
                match = m1 or m2
                if match:
                    lib = match.group(1)
                    if lib not in builtin:
                        libs.add(mapping.get(lib, lib))
    except:
        pass
    return libs

async def install_libs(libs, msg):
    if not libs:
        return True
    failed = []
    for lib in libs:
        await msg.edit_text(f'📦 جاري تثبيت: `{lib}`...', parse_mode='Markdown')
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', lib, '-q', '--no-warn-script-location'],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            failed.append(lib)
    if failed:
        await msg.edit_text(
            f'⚠️ فشل تثبيت:\n' + '\n'.join(f'• `{l}`' for l in failed) +
            '\n\nهشغل البوت على أي حال...',
            parse_mode='Markdown'
        )
        await asyncio.sleep(2)
    return True

async def run_bot(name, path, msg):
    if name in processes and processes[name].poll() is None:
        processes[name].terminate()
        await asyncio.sleep(1)

    p = subprocess.Popen(
        [sys.executable, path],
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes[name] = p
    bot_files[name] = path

    await asyncio.sleep(3)
    still_running = p.poll() is None

    if not still_running:
        stderr = p.stderr.read().decode('utf-8', errors='ignore')[-300:]
        await msg.edit_text(
            f'❌ *{name}* وقف!\n\n'
            f'```\n{stderr}\n```\n\n'
            f'تحقق من التوكن أو المكتبات',
            parse_mode='Markdown',
            reply_markup=kb_bot(name)
        )
    else:
        await msg.edit_text(
            f'✅ *{name}* شغال!\n\n'
            f'🆔 PID: `{p.pid}`\n'
            f'📄 `{path}`',
            parse_mode='Markdown',
            reply_markup=kb_bot(name)
        )

def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📋 بوتاتي', callback_data='list'),
         InlineKeyboardButton('📊 الحالة', callback_data='status')],
        [InlineKeyboardButton('❓ مساعدة', callback_data='help')],
    ])

def kb_bot(name):
    running = name in processes and processes[name].poll() is None
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            '⏹️ إيقاف' if running else '▶️ تشغيل',
            callback_data=f'stop_{name}' if running else f'start_{name}'
        )],
        [InlineKeyboardButton('🗑️ حذف', callback_data=f'delete_{name}'),
         InlineKeyboardButton('📋 معلومات', callback_data=f'info_{name}')],
        [InlineKeyboardButton('🔙 رجوع', callback_data='list')],
    ])

def kb_requirements(name):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('✅ تشغيل بدون requirements', callback_data=f'noreq_{name}')],
    ])

async def start(update: Update, _):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text('⛔ مش مصرح لك')
        return
    await update.message.reply_text(
        '👑 *Bot Hosting Manager*\n\n'
        '📤 ابعتلي:\n'
        '• ملف `.py` - البوت\n'
        '• ملف `requirements.txt` - المكتبات\n'
        '• أو نص بالمكتبات مباشرة\n\n'
        'هثبت كل المكتبات تلقائياً وأشغل البوت!',
        parse_mode='Markdown',
        reply_markup=kb_main()
    )

async def handle_message(update: Update, _):
    if update.effective_user.id != OWNER_ID:
        return
    text = update.message.text
    if not text:
        return

    # لو في بوت منتظر requirements كنص
    if pending_file and text.strip():
        name = list(pending_file.keys())[0]
        path = pending_file.pop(name)
        libs = set(l.strip() for l in text.replace(',', '\n').splitlines() if l.strip())
        msg = await update.message.reply_text(f'📦 جاري تثبيت {len(libs)} مكتبة...')
        await install_libs(libs, msg)
        await run_bot(name, path, msg)

async def handle_file(update: Update, _):
    if update.effective_user.id != OWNER_ID:
        return
    doc = update.message.document
    fname = doc.file_name

    os.makedirs('apps/bots', exist_ok=True)

    # لو ملف requirements.txt
    if fname == 'requirements.txt' or fname.endswith('requirements.txt'):
        path = 'apps/bots/requirements.txt'
        file = await doc.get_file()
        await file.download_to_drive(path)
        with open(path) as f:
            libs = set(l.strip() for l in f if l.strip() and not l.startswith('#'))
        msg = await update.message.reply_text(
            f'📦 requirements.txt\n\n'
            f'المكتبات ({len(libs)}):\n' +
            '\n'.join(f'• `{l}`' for l in libs),
            parse_mode='Markdown'
        )
        await install_libs(libs, msg)
        await msg.edit_text('✅ تم تثبيت كل المكتبات!\nابعتلي ملف البوت دلوقتي 🚀')
        return

    # لو مش .py
    if not fname.endswith('.py'):
        await update.message.reply_text('⚠️ بعتلي ملف .py أو requirements.txt بس!')
        return

    # ملف البوت
    name = fname.replace('.py', '').replace(' ', '_')
    path = f'apps/bots/{name}.py'
    msg = await update.message.reply_text('📥 جاري تحميل الملف...')
    file = await doc.get_file()
    await file.download_to_drive(path)

    # استخراج المكتبات تلقائياً
    auto_libs = extract_imports(path)

    await msg.edit_text(
        f'📄 *{name}.py*\n\n'
        f'🔍 مكتبات مكتشفة تلقائياً:\n' +
        ('\n'.join(f'• `{l}`' for l in auto_libs) if auto_libs else '• لا يوجد') +
        '\n\n📎 ابعتلي `requirements.txt` أو اكتب المكتبات الإضافية\n'
        'أو اضغط تشغيل مباشرة:',
        parse_mode='Markdown',
        reply_markup=kb_requirements(name)
    )

    pending_file[name] = path

    # تثبيت المكتبات المكتشفة في الخلفية
    if auto_libs:
        await install_libs(auto_libs, msg)
        await msg.edit_text(
            f'✅ تم تثبيت المكتبات التلقائية\n\n'
            f'ابعتلي مكتبات إضافية أو اضغط تشغيل:',
            parse_mode='Markdown',
            reply_markup=kb_requirements(name)
        )

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == 'list':
        if not bot_files:
            await q.edit_message_text('📋 *مفيش بوتات*\n\nابعتلي ملف .py!',
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='back')]]))
            return
        kb = []
        for name in bot_files:
            running = name in processes and processes[name].poll() is None
            kb.append([InlineKeyboardButton(f'{"🟢" if running else "🔴"} {name}', callback_data=f'bot_{name}')])
        kb.append([InlineKeyboardButton('🔙 رجوع', callback_data='back')])
        await q.edit_message_text('📋 *بوتاتك:*', parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(kb))

    elif data == 'status':
        running = sum(1 for n,p in processes.items() if p.poll() is None)
        text = f'📊 *الحالة:*\n\n🟢 شغال: {running}\n🔴 موقف: {len(bot_files)-running}\n📦 إجمالي: {len(bot_files)}\n\n'
        for name in bot_files:
            r = name in processes and processes[name].poll() is None
            text += f'{"🟢" if r else "🔴"} `{name}`\n'
        await q.edit_message_text(text, parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='back')]]))

    elif data == 'help':
        await q.edit_message_text(
            '❓ *طريقة الاستخدام:*\n\n'
            '1️⃣ ابعت ملف `.py`\n'
            '2️⃣ هثبت المكتبات تلقائياً\n'
            '3️⃣ لو محتاج مكتبات إضافية:\n'
            '   • ابعت `requirements.txt`\n'
            '   • أو اكتب أسماءها\n'
            '4️⃣ اضغط تشغيل!\n\n'
            '💡 *مثال requirements:*\n'
            '```\nrequests\npyTelegramBotAPI\nbeautifulsoup4\n```',
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 رجوع', callback_data='back')]]))

    elif data == 'back':
        await q.edit_message_text(
            '👑 *Bot Hosting Manager*\n\nابعتلي ملف `.py`!',
            parse_mode='Markdown', reply_markup=kb_main())

    elif data.startswith('noreq_'):
        name = data.replace('noreq_', '')
        path = pending_file.pop(name, bot_files.get(name))
        if path:
            msg = await q.edit_message_text(f'🚀 جاري تشغيل *{name}*...', parse_mode='Markdown')
            await run_bot(name, path, msg)

    elif data.startswith('bot_'):
        name = data.replace('bot_', '')
        running = name in processes and processes[name].poll() is None
        await q.edit_message_text(
            f'🤖 *{name}*\n\n'
            f'الحالة: {"🟢 شغال" if running else "🔴 موقف"}\n'
            f'📄 `{bot_files.get(name, "-")}`',
            parse_mode='Markdown', reply_markup=kb_bot(name))

    elif data.startswith('start_'):
        name = data.replace('start_', '')
        if name in bot_files:
            msg = await q.edit_message_text(f'🚀 جاري تشغيل *{name}*...', parse_mode='Markdown')
            await run_bot(name, bot_files[name], msg)

    elif data.startswith('stop_'):
        name = data.replace('stop_', '')
        if name in processes and processes[name].poll() is None:
            processes[name].terminate()
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
        pending_file.pop(name, None)
        await q.edit_message_text('👑 *Bot Hosting Manager*',
            parse_mode='Markdown', reply_markup=kb_main())

    elif data.startswith('info_'):
        name = data.replace('info_', '')
        libs = extract_imports(bot_files[name]) if name in bot_files else set()
        running = name in processes and processes[name].poll() is None
        await q.edit_message_text(
            f'📋 *{name}*\n\n'
            f'الحالة: {"🟢 شغال" if running else "🔴 موقف"}\n'
            f'📦 المكتبات: {", ".join(f"`{l}`" for l in libs) if libs else "لا يوجد"}\n'
            f'📄 `{bot_files.get(name, "-")}`',
            parse_mode='Markdown', reply_markup=kb_bot(name))

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler('start', start))
app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button))

print('👑 Bot Hosting Manager شغال!')
app.run_polling(drop_pending_updates=True)
