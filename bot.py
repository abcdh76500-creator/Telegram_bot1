from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import os
import logging
import sqlite3
import random
import json
from datetime import datetime
import asyncio
from aiohttp import web
import threading

# ========== الإعدادات الأساسية ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', 0))

# ========== Health Check لضمان التشغيل 24/7 ==========
def start_health_check():
    async def handle_health_check(request):
        return web.Response(text="🟢 لولو البوت شغالة تمام! 🌸")
    
    async def handle_stats(request):
        return web.json_response({
            "status": "online",
            "bot": "لولو - البوت المصري",
            "version": "2.0",
            "developer": "لولو تيم"
        })
    
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    app.router.add_get('/health', handle_health_check)
    app.router.add_get('/stats', handle_stats)
    
    def run_app():
        try:
            web.run_app(app, host='0.0.0.0', port=8080, access_log=None)
        except Exception as e:
            print(f"Health check error: {e}")
    
    thread = threading.Thread(target=run_app, daemon=True)
    thread.start()
    print("✅ نظام المراقبة بدأ على البورت 8080")

# ========== قاعدة البيانات ==========
def init_db():
    conn = sqlite3.connect('lulu_bot.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS banned_words
                 (id INTEGER PRIMARY KEY, word TEXT, added_by INTEGER, added_date TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_profiles
                 (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
                  last_name TEXT, points INTEGER, level INTEGER, joined_date TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

# ========== شخصية لولو ==========
class LuluPersonality:
    def __init__(self):
        self.responses = {
            'greetings': [
                "أهلاً يا قمر! 🌸 أنا لولو البنت المصرية الجدعة!",
                "مرحباااات! 🥰 إزيك يا حبيبي؟ أنا لولو جاية أخدمك!",
                "أهلاً وسهلاً بيك يا عسل! 💕 أنا لولو، قوليلي إزيك؟"
            ],
            'help': [
                "تعالي يا حبيبي أقولك على الأوامر! 💫",
                "ماشي يا قمر! هقولك إنت تقدّم تعمل إيه معايا! 🌟"
            ]
        }
    
    def get_response(self, response_type):
        return random.choice(self.responses.get(response_type, ["مش فاهمة يا حبيبي! 🥺"]))

lulu = LuluPersonality()

# ========== نظام الحماية ==========
class ProtectionSystem:
    def __init__(self):
        self.banned_words = []
        self.load_banned_words()
    
    def load_banned_words(self):
        conn = sqlite3.connect('lulu_bot.db')
        c = conn.cursor()
        c.execute("SELECT word FROM banned_words")
        self.banned_words = [row[0].lower() for row in c.fetchall()]
        conn.close()
    
    async def check_message(self, update: Update, context: CallbackContext):
        if update.effective_chat.type in ['group', 'supergroup']:
            message = update.message
            if message.text:
                text = message.text.lower()
                for word in self.banned_words:
                    if word in text:
                        await message.delete()
                        await message.reply_text("🚫 الكلام ده مش منظم يا حبيبي!")
                        return True
        return False

protection = ProtectionSystem()

# ========== الأوامر الأساسية ==========
async def start_command(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("🛡️ حماية الجروب", callback_data="protection"),
         InlineKeyboardButton("🎵 تشغيل أغاني", callback_data="music")],
        [InlineKeyboardButton("📝 إنشاء امتحان", callback_data="exam"),
         InlineKeyboardButton("🎮 أسئلة نفسية", callback_data="psych")],
        [InlineKeyboardButton("📞 الدعم", callback_data="support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"{lulu.get_response('greetings')}\n\n"
        "إختر من الأزرار تحت علشان تبدأ:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: CallbackContext):
    help_text = """
🎀 *أوامر لولو* 🎀

*الأوامر العامة:*
• `بداية` - قائمة البداية
• `مساعدة` - هذه القائمة
• `معلومات` - معلومات عنك
• `لولو` - نداء لولو

*في الجروبات:*
• `حماية` - إعدادات الحماية
• `اضافة كلمة [كلمة]` - إضافة كلمة ممنوعة

*في الخاص:*
• `إنشاء امتحان` - عمل امتحان جديد
• `قائمة أغاني` - قائمة الأغاني

🎭 *لولو: جنبك دايماً!* 💕
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.lower()
    
    if text == "لولو":
        responses = [
            "نعمتي يا حبيبي! 🌸 في إيه؟",
            "أيوة يا قمر! 🥰 قوليلي إزيك؟",
            "جاية يا حبيبي! 💕 في إيه؟"
        ]
        await update.message.reply_text(random.choice(responses))
    
    elif text == "معلومات":
        user = update.effective_user
        info_text = f"""
🎀 *معلومات عنك* 🎀

👤 *الاسم:* {user.first_name}
📛 *اليوزر:* @{user.username or 'مافيش'}
🆔 *الآيدي:* `{user.id}`

💫 *لولو بتحبك!* 🌸
        """
        await update.message.reply_text(info_text, parse_mode='Markdown')

async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == "protection":
        await query.edit_message_text(
            "🛡️ *نظام حماية الجروب*\n\n"
            "أنا هحمي الجروب من:\n"
            "• الكلمات السيئة 🚫\n"
            "• السبام 📢\n"
            "• المحتوى غير المناسب 🔞\n\n"
            "عايز تضيف كلمة ممنوعة؟ ابعت: /addword الكلمة",
            parse_mode='Markdown'
        )
    elif query.data == "music":
        await query.edit_message_text(
            "🎵 *نظام الأغاني*\n\n"
            "لسة بتطوّر يا حبيبي! 🤗\n"
            "هقدر أشغّل أغاني في الجروبات قريب جداً!",
            parse_mode='Markdown'
        )

def main():
    # بدء نظام المراقبة
    start_health_check()
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # مراقبة الرسائل في الجروبات
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, protection.check_message))
    
    # بدء البوت
    print("🌸 لولو البوت بدأت التشغيل...")
    application.run_polling()

if __name__ == '__main__':
    main()
