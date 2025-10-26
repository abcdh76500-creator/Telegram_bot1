from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from telegram.constants import ChatType
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

# ========== Health Check للتشغيل 24/7 ==========
def start_health_check():
    async def handle_health_check(request):
        return web.Response(text="🟢 لولو البوت شغالة تمام! 🌸")
    
    async def handle_stats(request):
        return web.json_response({
            "status": "online",
            "bot": "لولو - البوت المصري",
            "version": "3.0",
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS group_links
                 (group_id INTEGER PRIMARY KEY, group_title TEXT, 
                  invite_link TEXT, created_date TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_profiles
                 (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
                  last_name TEXT, points INTEGER, level INTEGER, joined_date TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS exams
                 (id INTEGER PRIMARY KEY, name TEXT, questions TEXT, 
                  created_by INTEGER, created_date TEXT, is_active BOOLEAN)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS exam_results
                 (id INTEGER PRIMARY KEY, user_id INTEGER, exam_id INTEGER,
                  score INTEGER, total_questions INTEGER, taken_date TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

# ========== شخصية لولو المحسنة ==========
class LuluPersonality:
    def __init__(self):
        self.responses = {
            'greetings': [
                "أهلاً يا قمر! 🌸 أنا لولو البنت المصرية الجدعة!",
                "مرحباااات! 🥰 إزيك يا حبيبي؟ أنا لولو جاية أخدمك!",
                "أهلاً وسهلاً بيك يا عسل! 💕 أنا لولو، قوليلي إزيك؟",
                "ياااه! أخيرا كلمتني! 😍 أنا لولو، إزيك يا حبيبي؟",
                "أهلاً بيك يا حبيبي! 🌹 لولو موجودة علشانك!"
            ],
            'help': [
                "تعالي يا حبيبي أقولك على الأوامر! 💫",
                "ماشي يا قمر! هقولك إنت تقدّم تعمل إيه معايا! 🌟",
                "أكيد يا عسل! هدلك على كل حاجة! 🎀",
                "يا قلبي عليك! 🤗 تعال أشرحلك كل حاجة!"
            ],
            'protection': [
                "متفكرش حتى تتكلم كلمة وحشة! أنا هنا 🛡️",
                "الجروب نظيف ومحمي يا حبيبي! 💪",
                "مافيش حد هيقدر يقول حاجة وحشة وأنا موجودة! 😎",
                "الحماية شغالة 100% يا قمر! 🔒"
            ],
            'lulu_called': [
                "نعمتي يا حبيبي! 🌸 في إيه؟ عايز حاجة؟",
                "ياااه! ناديتيلي! 😍 قوليلي يا قمر، إزيك؟",
                "أنا هنا يا عسل! 💕 قول لي عايز إيه؟",
                "جاية يا حبيبي! 🥰 إنت اللي تناديني ويا رباني!",
                "يا قلبي عليك! 😘 ناديت لولو؟ قوليلي فينك؟"
            ],
            'special_owner': [
                "ياااه! الريس نفسه! 😍🌹 إزيك يا حبيبي؟",
                "أهلاً وسهلاً بمالكي الجميل! 💫 أنتظر أوامرك!",
                "يا رباني! الريس كلمني! 🥰 قوليلي إزيك يا حبيبي؟",
                "أنت اللي أمرك نافذ يا ريس! 💕 في إيه؟"
            ],
            'link_responses': [
                "ياااه! عايز رابط الجروب؟ هجيبلك ياه يا قمر! 🌸",
                "ماشي يا حبيبي! هبعتلك رابط الجروب دلوقتي! 💫",
                "أكيد يا عسل! رابط الجروب جاي في ثواني! 🎀",
                "هوووب! علشان إنت طلب يا جميل! رابط الجروب تحت! 🥰"
            ],
            'music': [
                "هشغّللك أجمل حاجة! 🎵",
                "ماشي يا قمر! هبدأ الأغاني الحلوة دلوقتي! 🎶",
                "هتسمع أجمل أغنية في الدنيا! 🎧",
                "الأغنية جاية يا حبيبي! استمتع! 🎤"
            ],
            'exam': [
                "هختبر ذكائك يا عبقري! 🧠",
                "تعال أشوف مستواك إزاي! 📚",
                "استعد للامتحان يا ذكي! 💫",
                "هتتفوق يا قمر! أنا متأكدة! 🌟"
            ]
        }
        
        self.psychological_questions = [
            "إيه أكتر حاجة بتخاف منها في الحياة؟ 🤔",
            "لو قدرة تغير حاجة واحدة في الماضي، هتغير إيه؟ 💭",
            "إيه أكتر قرار ندمت عليه؟ 😔",
            "إيه اللي بيخليك تحس بالأمان؟ 🛡️",
            "بتعبر عن مشاعرك بسهولة ولا بتحبسها جواك؟ 🎭",
            "إيه أكتر حاجة بتفتخر بيها في نفسك؟ 🌟",
            "بتعتبر نفسك شخص اجتماعي ولا انطوائي؟ 🎪",
            "إيه أكتر حاجة بتسعدك في الحياة؟ 😊",
            "بتعتمد على عقلك أكتر ولا على مشاعرك؟ 🧠❤️",
            "إيه حلمك في الحياة؟ 🌈"
        ]
    
    def get_response(self, response_type):
        return random.choice(self.responses.get(response_type, ["مش فاهمة يا حبيبي! 🥺"]))
    
    def get_psychological_question(self):
        return random.choice(self.psychological_questions)

lulu = LuluPersonality()

# ========== نظام إدارة الروابط ==========
class LinkManager:
    def __init__(self):
        pass
    
    def save_group_link(self, group_id, group_title, invite_link):
        conn = sqlite3.connect('lulu_bot.db')
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO group_links 
                     (group_id, group_title, invite_link, created_date)
                     VALUES (?, ?, ?, ?)''',
                  (group_id, group_title, invite_link, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def get_group_link(self, group_id):
        conn = sqlite3.connect('lulu_bot.db')
        c = conn.cursor()
        c.execute("SELECT invite_link FROM group_links WHERE group_id = ?", (group_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

link_manager = LinkManager()

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
    
    def add_banned_word(self, word, user_id):
        conn = sqlite3.connect('lulu_bot.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO banned_words (word, added_by, added_date) VALUES (?, ?, ?)",
                  (word.lower(), user_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        self.load_banned_words()
        return True
    
    def remove_banned_word(self, word):
        conn = sqlite3.connect('lulu_bot.db')
        c = conn.cursor()
        c.execute("DELETE FROM banned_words WHERE word = ?", (word.lower(),))
        conn.commit()
        conn.close()
        self.load_banned_words()
        return True
    
    def get_banned_words(self):
        return self.banned_words
    
    async def check_message(self, update: Update, context: CallbackContext):
        if update.effective_chat.type in ['group', 'supergroup']:
            message = update.message
            if message.text:
                text = message.text.lower()
                for word in self.banned_words:
                    if word in text:
                        await message.delete()
                        responses = [
                            "يا حبيبي، الكلام ده مش منظم! 🚫",
                            "آه يا قلبي، مينفعش نتكلم كده! 🙅‍♀️",
                            "يا جميل، في ألفاظ أحلى من كده! 🌸"
                        ]
                        await message.reply_text(random.choice(responses))
                        return True
        return False

protection = ProtectionSystem()

# ========== نظام إرسال الروابط ==========
async def handle_group_link_request(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user
    
    # تأكد أن الأمر في جروب
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text(
            "❌ هذا الأمر متاح فقط في الجروبات يا قمر! 🌸"
        )
        return
    
    try:
        # محاولة الحصول على رابط الدعوة
        chat_member = await context.bot.get_chat_member(chat.id, user.id)
        
        can_invite = chat_member.status in ['administrator', 'creator']
        
        if can_invite:
            try:
                invite_link = await context.bot.create_chat_invite_link(chat.id, creates_join_request=False)
                link = invite_link.invite_link
            except Exception:
                try:
                    invite_link = await context.bot.export_chat_invite_link(chat.id)
                    link = invite_link
                except Exception:
                    link = None
        else:
            link = link_manager.get_group_link(chat.id)
            
            if not link:
                try:
                    invite_link = await context.bot.export_chat_invite_link(chat.id)
                    link = invite_link
                    link_manager.save_group_link(chat.id, chat.title, link)
                except Exception:
                    link = None
        
        if link:
            keyboard = [
                [InlineKeyboardButton("🔗 اضغط للانضمام للجروب", url=link)],
                [InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={link}&text=انضم%20لجروبنا%20الحلو!%20🌸")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"{lulu.get_response('link_responses')}\n\n"
                f"🏷️ *اسم الجروب:* {chat.title}\n"
                f"👥 *عدد الأعضاء:* {await chat.get_member_count()}\n\n"
                f"🔗 *رابط الجروب:*\n`{link}`\n\n"
                f"💫 *شارك الرابط مع أصدقائك علشان الجروب يكبر!*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            link_manager.save_group_link(chat.id, chat.title, link)
            
        else:
            await update.message.reply_text(
                "😔 للأسف مفيش صلاحيات لإنشاء رابط دعوة للجروب.\n\n"
                "📋 *الحلول:*\n"
                "• اطلب من أدمن الجروب يبعث الرابط\n"
                "• أو يديلي صلاحية إنشاء روابط دعوة\n\n"
                "💕 لولو عايزة أساعدك أكتر!",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error generating group link: {e}")
        await update.message.reply_text(
            "🚫 للأسف مقدرش أجيب رابط الجروب دلوقتي.\n"
            "جرب تاني بعد شوية أو كلم أدمن الجروب!"
        )

# ========== الأوامر الأساسية ==========
async def start_command(update: Update, context: CallbackContext):
    user = update.effective_user
    
    welcome_text = f"""
🎀 *مرحباً بك يا {user.first_name}!* 🎀

*🌸 أنا لولو - البوت المصري متعدد المهام 🌸*

*📖 عن لولو:*
• بنت مصرية جدعة ودلعة 💕
• بوت ذكي بيقدر يعمل كل حاجة 🧠
• صديقتك اللي عمرك ما هتستغنى عنها! 🥰

*🎯 المميزات الرئيسية:*

*🛡️ نظام الحماية المتقدم:*
• منع الكلمات السيئة 🚫
• حماية الجروب من السبام 📢
• مراقبة المحتوى تلقائياً 👀

*🎵 نظام الموسيقى:*
• تشغيل الأغاني من اليوتيوب 🎶
• قوائم تشغيل مخصصة 🎼

*📝 نظام الامتحانات:*
• إنشاء امتحانات مخصصة ✏️
• قوالب جاهزة للامتحانات 📚
• تصحيح تلقائي للنتائج ✅

*🎮 مميزات ترفيهية:*
• أسئلة نفسية 🧠
• نكت مصرية 😂
• تحليل الشخصية 🔮

*🔧 الأوامر المتاحة:*

*في الجروب والخاص:*
• `بداية` - رسالة الترحيب
• `مساعدة` - قائمة المساعدة
• `معلومات` - معلومات عنك
• `لولو` - نداء لولو
• `كات` - أسئلة نفسية

*في الجروب فقط:*
• `رابط` - إرسال رابط الجروب
• `حماية` - إعدادات حماية
• `قواعد` - قواعد الجروب

*💞 لولو: جنبك دايماً علشان تستمتع وتتطور!*
    """
    
    keyboard = [
        [InlineKeyboardButton("🛡️ نظام الحماية", callback_data="protection_system"),
         InlineKeyboardButton("🎵 الموسيقى", callback_data="music_system")],
        [InlineKeyboardButton("📝 الامتحانات", callback_data="exam_system"),
         InlineKeyboardButton("🎮 الترفيه", callback_data="fun_system")],
        [InlineKeyboardButton("🔗 روابط الجروبات", callback_data="links_system"),
         InlineKeyboardButton("📞 الدعم", callback_data="support_system")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

async def help_command(update: Update, context: CallbackContext):
    help_text = """
🎀 *أوامر لولو - المساعدة الشاملة* 🎀

*🌐 الأوامر العامة (شغالة في كل مكان):*
• `بداية` - رسالة الترحيب والتعريف
• `مساعدة` - قائمة المساعدة
• `معلومات` - معلومات عنك
• `لولو` - نداء لولو
• `كات` - أسئلة نفسية

*🛡️ أوامر الجروب (شغالة في الجروبات فقط):*
• `رابط` - إرسال رابط الجروب 🌐
• `الرابط` - إرسال رابط الجروب 🔗
• `حماية` - إعدادات حماية الجروب
• `اضافة كلمة [كلمة]` - إضافة كلمة ممنوعة
• `قواعد` - قواعد الجروب

*🎵 أوامر الموسيقى (قريباً):*
• `شغل [اسم الأغنية]` - تشغيل أغنية
• `قائمة أغاني` - قائمة الأغاني

*📝 أوامر الامتحانات (قريباً):*
• `إنشاء امتحان` - إنشاء امتحان جديد
• `امتحاناتي` - الامتحانات اللي عملتها

*💫 ملاحظة:*
لولو بتقدر تميز بين الجروب والخاص وعشان كده بعض الأوامر بتكون متاحة في أماكن معينة!
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.lower().strip()
    user = update.effective_user
    chat = update.effective_chat
    
    # المعاملة الخاصة للمالك
    if user.id == OWNER_ID:
        if any(word in text for word in ["لولو", "بوت", "ريس", "مالك"]):
            await update.message.reply_text(lulu.get_response('special_owner'))
            return
    
    if text == "لولو":
        await update.message.reply_text(lulu.get_response('lulu_called'))
    
    elif text in ["معلومات", "انا مين", "مين انا"]:
        user_info = f"""
🎀 *معلومات عنك يا قمر!* 🎀

*👤 معلومات الشخصية:*
• **الاسم:** {user.first_name} {user.last_name or ''}
• **اليوزر:** @{user.username or 'مافيش'}
• **الآيدي:** `{user.id}`

*💬 معلومات الدردشة:*
• **نوع الدردشة:** {'جروب' if chat.type in ['group', 'supergroup'] else 'خاص'}
• **اسم الدردشة:** {chat.title if hasattr(chat, 'title') else 'دردشة خاصة'}

*🌸 لولو:*
بتتمنى لك يوم سعيد يا قمر! 💕
"""
        await update.message.reply_text(user_info, parse_mode='Markdown')
    
    elif text in ["كات", "سؤال نفسي"]:
        question = lulu.get_psychological_question()
        await update.message.reply_text(
            f"🎭 *سؤال نفسي من لولو:*\n\n{question}\n\n"
            "اقعد مع نفسك وفكر فيه كويس! 💭",
            parse_mode='Markdown'
        )
    
    # معالجة طلبات الروابط
    elif text in ["رابط", "الرابط", "رابط الجروب", "رابط جروب", "link", "invite"]:
        await handle_group_link_request(update, context)
    
    # أوامر الجروبات فقط
    elif chat.type in ['group', 'supergroup']:
        if text in ["حماية", "حمايه", "protection"]:
            await protection_command(update, context)
        elif text.startswith("اضافة كلمة"):
            await add_banned_word_command(update, context)
        elif text in ["قواعد", "القواعد"]:
            await group_rules_command(update, context)

async def protection_command(update: Update, context: CallbackContext):
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ هذا الأمر متاح فقط في الجروبات!")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة كلمة ممنوعة", callback_data="add_banned_word"),
         InlineKeyboardButton("📋 الكلمات الممنوعة", callback_data="list_banned_words")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"{lulu.get_response('protection')}\n\n"
        "*إعدادات حماية الجروب:*\n"
        "• منع الكلمات السيئة 🚫\n"
        "• حماية من السبام 📢\n"
        "• مراقبة المحتوى 🔍",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def add_banned_word_command(update: Update, context: CallbackContext):
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ هذا الأمر متاح فقط في الجروبات!")
        return
    
    if context.args:
        word = ' '.join(context.args)
        protection.add_banned_word(word, update.effective_user.id)
        await update.message.reply_text(f"✅ تم إضافة '{word}' للكلمات الممنوعة!")
    else:
        await update.message.reply_text("❌ استخدم: اضافة كلمة [الكلمة]")

async def group_rules_command(update: Update, context: CallbackContext):
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ هذا الأمر متاح فقط في الجروبات!")
        return
    
    rules_text = """
📜 *قواعد الجروب الأساسية:*

1. ✅ الاحترام المتبادل بين جميع الأعضاء
2. 🚫 ممنوع السبام أو الإعلانات بدون إذن
3. 🌸 استخدم لغة مهذبة في الحوار
4. 📚 المشاركة البناءة مفضلة
5. 🔗 مشاركة المحتوى المفيد مسموح

🎀 *لولو هتساعد في تطبيق القواعد!*
"""
    await update.message.reply_text(rules_text, parse_mode='Markdown')

# ========== معالجة الأزرار ==========
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "protection_system":
        await query.edit_message_text(
            "🛡️ *نظام الحماية المتقدم*\n\n"
            "*المميزات:*\n"
            "• منع الكلمات السيئة تلقائياً 🚫\n"
            "• حذف الرسائل المخالفة ⚡\n"
            "• حماية من السبام والإعلانات 📢\n"
            "• إعدادات مرنة لكل جروب ⚙️\n\n"
            "*الاستخدام:*\n"
            "اكتب `حماية` في الجروب للتحكم في الإعدادات",
            parse_mode='Markdown'
        )
    elif data == "music_system":
        await query.edit_message_text(
            "🎵 *نظام الموسيقى*\n\n"
            "جاري التطوير يا قمر! 🤗\n"
            "هقدر أشغّل أغاني في الجروبات قريب جداً!\n\n"
            "*المميزات القادمة:*\n"
            "• تشغيل من اليوتيوب 📺\n"
            "• قوائم تشغيل مخصصة 🎼\n"
            "• تحميل الأغاني 📥\n"
            "• بحث سريع 🔍",
            parse_mode='Markdown'
        )
    elif data == "exam_system":
        await query.edit_message_text(
            "📝 *نظام الامتحانات*\n\n"
            "جاري التطوير يا عبقري! 🧠\n"
            "هتقدر تعمل امتحانات وتختبر أصدقائك!\n\n"
            "*المميزات القادمة:*\n"
            "• إنشاء امتحانات مخصصة ✏️\n"
            "• قوالب جاهزة 📚\n"
            "• تصحيح تلقائي ✅\n"
            "• إحصائيات مفصلة 📊",
            parse_mode='Markdown'
        )
    elif data == "fun_system":
        await query.edit_message_text(
            "🎮 *النظام الترفيهي*\n\n"
            "*المميزات المتاحة:*\n"
            "• أسئلة نفسية 🧠 (اكتب `كات`)\n"
            "• نداء لولو 💕 (اكتب `لولو`)\n"
            "• معلومات شخصية 👤 (اكتب `معلومات`)\n\n"
            "*المميزات القادمة:*\n"
            "• نكت مصرية 😂\n"
            "• ألعاب تفاعلية 🎯\n"
            "• تحليل الشخصية 🔮",
            parse_mode='Markdown'
        )
    elif data == "links_system":
        await query.edit_message_text(
            "🔗 *نظام روابط الجروبات*\n\n"
            "*المميزات:*\n"
            "• إرسال رابط الجروب بسهولة 🌐\n"
            "• مشاركة سريعة مع الأصدقاء 📤\n"
            "• حفظ الروابط تلقائياً 💾\n\n"
            "*الاستخدام:*\n"
            "اكتب `رابط` في أي جروب وانا هبعتلك الرابط!",
            parse_mode='Markdown'
        )
    elif data == "support_system":
        await query.edit_message_text(
            "📞 *نظام الدعم والمساندة*\n\n"
            "لولو دايماً موجودة علشانك! 💕\n\n"
            "*طرق المساعدة:*\n"
            "• اكتب `مساعدة` لأوامر كاملة\n"
            "• اكتب `بداية` لرسالة الترحيب\n"
            "• جرب الأوامر المختلفة 🎪\n\n"
            "🌸 *لولو: جنبك في كل خطوة!*",
            parse_mode='Markdown'
        )
    elif data == "main_menu":
        await start_command(update, context)

def main():
    # بدء نظام المراقبة
    start_health_check()
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("رابط", handle_group_link_request))
    
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # مراقبة الرسائل في الجروبات للحماية
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, protection.check_message))
    
    # بدء البوت
    print("🌸 لولو البوت بدأت التشغيل...")
    print("✅ النظام جاهز للاستخدام!")
    application.run_polling()

if __name__ == '__main__':
    main()
