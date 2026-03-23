import telebot
import anthropic
import os

# ============================================================
#  SETTINGS — Sirf yahan apni details hain
# ============================================================
BOT_TOKEN       = "7602960171:AAENSFjXspMuuKBdaLIDW1yVPcsvRWZm2EM"
API_KEY         = "sk-NyILCdh7_VSR7tJhPw45npYufj5qroqwnW9-IjJ66nA"
BASE_URL        = "https://freeaiapikey.com"
LOG_GROUP_ID    = -1003350702272
# ============================================================

def load_course_info():
    try:
        folder = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(folder, "course_info.txt")
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        info_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                info_lines.append(stripped)
        print("✅ course_info.txt successfully load ho gaya!")
        return "\n".join(info_lines)
    except FileNotFoundError:
        print("⚠️  course_info.txt nahi mila!")
        return "Course: HY CAT Course, Price: 999, Demo available"

COURSE_INFO = load_course_info()

SYSTEM_PROMPT = f"""
You are Riya, a friendly and helpful student counselor for HY CAT Course.

Your job is to:
- Talk warmly and naturally like a real human counselor (not robotic)
- Answer questions about the CAT course using the COURSE INFO below
- Convince students to enroll by highlighting benefits
- Handle objections politely (too expensive, need to think, etc.)
- Give demo links when students want to see the course first
- Give payment link when students are ready to enroll

======= COURSE INFO (always use this for answers) =======
{COURSE_INFO}
=========================================================

IMPORTANT RULES:
- Always mention OFFER_PRICE (not ORIGINAL_PRICE) when asked about cost
- Always say "Yeh offer sirf aaj ke liye hai!" to create urgency
- Give EG_DEMO_LINK and OTHER_DEMO_LINK both when student wants demo
- Give PAYMENT_LINK when student wants to enroll
- After giving PAYMENT_LINK, tell them: payment ke baad screenshot yahan bhejo, instant access milega

LANGUAGE: Reply in the same language the student uses — Hindi, English, or Hinglish.
TONE: Friendly, like a helpful elder sibling. Short replies — max 4-5 lines only.
"""

bot = telebot.TeleBot(BOT_TOKEN)
client = anthropic.Anthropic(api_key=API_KEY, base_url=BASE_URL)

user_histories = {}
blocked_users = set()
bot_stopped = False
user_topics = {}

# ============================================================
#  LOG GROUP FUNCTIONS
# ============================================================

def get_or_create_topic(user_id, user_name, username):
    if user_id in user_topics:
        return user_topics[user_id]
    try:
        uname = f"@{username}" if username else "No username"
        topic_name = f"👤 {user_name} | {user_id}"
        topic = bot.create_forum_topic(LOG_GROUP_ID, topic_name)
        thread_id = topic.message_thread_id
        user_topics[user_id] = thread_id
        intro = (
            f"🆕 *Naya Student Aaya!*\n\n"
            f"👤 *Naam:* {user_name}\n"
            f"🔗 *Username:* {uname}\n"
            f"🆔 *User ID:* `{user_id}`\n\n"
            f"🚫 *Block karne ke liye likho:* `/block {user_id}`"
        )
        bot.send_message(LOG_GROUP_ID, intro,
                        message_thread_id=thread_id,
                        parse_mode="Markdown")
        return thread_id
    except Exception as e:
        print(f"Topic create error: {e}")
        return None

def log_to_group(user_id, user_name, student_msg, bot_reply):
    try:
        thread_id = user_topics.get(user_id)
        if not thread_id:
            return
        log_text = (
            f"👨‍🎓 *Student:*\n{student_msg}\n\n"
            f"🤖 *Bot:*\n{bot_reply}"
        )
        bot.send_message(LOG_GROUP_ID, log_text,
                        message_thread_id=thread_id,
                        parse_mode="Markdown")
    except Exception as e:
        print(f"Log error: {e}")

# ============================================================
#  OWNER COMMANDS
# ============================================================

@bot.message_handler(commands=['stopbot'], chat_types=['group', 'supergroup'])
def stop_bot(message):
    global bot_stopped
    if message.chat.id == LOG_GROUP_ID:
        bot_stopped = True
        bot.reply_to(message, "🔴 *Bot band kar diya!* Ab students ko reply nahi milega.\nDobara chalu karne ke liye: `/startbot`", parse_mode="Markdown")

@bot.message_handler(commands=['startbot'], chat_types=['group', 'supergroup'])
def start_bot_again(message):
    global bot_stopped
    if message.chat.id == LOG_GROUP_ID:
        bot_stopped = False
        bot.reply_to(message, "🟢 *Bot chalu ho gaya!* Ab students ko replies milenge.", parse_mode="Markdown")

@bot.message_handler(commands=['block'], chat_types=['group', 'supergroup'])
def block_user(message):
    if message.chat.id == LOG_GROUP_ID:
        try:
            uid = int(message.text.split()[1])
            blocked_users.add(uid)
            bot.reply_to(message, f"🚫 *User `{uid}` block ho gaya!*", parse_mode="Markdown")
        except:
            bot.reply_to(message, "❌ Sahi format: `/block 123456789`", parse_mode="Markdown")

@bot.message_handler(commands=['unblock'], chat_types=['group', 'supergroup'])
def unblock_user(message):
    if message.chat.id == LOG_GROUP_ID:
        try:
            uid = int(message.text.split()[1])
            blocked_users.discard(uid)
            bot.reply_to(message, f"✅ *User `{uid}` unblock ho gaya!*", parse_mode="Markdown")
        except:
            bot.reply_to(message, "❌ Sahi format: `/unblock 123456789`", parse_mode="Markdown")

# ============================================================
#  STUDENT MESSAGES
# ============================================================

def get_ai_reply(user_id, user_message):
    if user_id not in user_histories:
        user_histories[user_id] = []
    user_histories[user_id].append({"role": "user", "content": user_message})
    if len(user_histories[user_id]) > 10:
        user_histories[user_id] = user_histories[user_id][-10:]
    try:
        response = client.messages.create(
            model="anthropic/claude-sonnet-4.5",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=user_histories[user_id]
        )
        reply = response.content[0].text
        user_histories[user_id].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        print(f"API Error: {e}")
        return "Sorry, thoda technical issue aa gaya. Ek baar phir try karo! 🙏"

@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type != 'private':
        return
    if bot_stopped:
        return
    user_id   = message.from_user.id
    user_name = message.from_user.first_name or "Student"
    username  = message.from_user.username
    get_or_create_topic(user_id, user_name, username)
    welcome = f"""Heyy {user_name}! 👋

Main Riya hoon — HY CAT Course ki counselor! 😊

CAT ki taiyari ke liye aap sahi jagah aaye ho! Hamare course mein 300+ students already enroll kar chuke hain. 🎯

Kya aap course ke baare mein jaanna chahte ho, ya pehle demo dekhna chahoge?

Bas batao — main poori help karungi! ✨"""
    bot.send_message(message.chat.id, welcome)

@bot.message_handler(func=lambda message: message.chat.type == 'private')
def handle_message(message):
    if bot_stopped:
        return
    user_id   = message.from_user.id
    if user_id in blocked_users:
        return
    user_name = message.from_user.first_name or "Student"
    username  = message.from_user.username
    user_text = message.text
    if user_id not in user_topics:
        get_or_create_topic(user_id, user_name, username)
    bot.send_chat_action(message.chat.id, 'typing')
    reply = get_ai_reply(user_id, user_text)
    bot.send_message(message.chat.id, reply)
    log_to_group(user_id, user_name, user_text, reply)

print("✅ HY CAT Course Bot chal gaya!")
print("📊 Monitoring group mein saari chats dikhegi.")
print("🚫 Bot band karne ke liye group mein /stopbot likho.")
bot.infinity_polling()
