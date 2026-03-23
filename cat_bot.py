import telebot
import anthropic
import os

# ============================================================
#  SETTINGS
# ============================================================
BOT_TOKEN    = "7602960171:AAENSFjXspMuuKBdaLIDW1yVPcsvRWZm2EM"
API_KEY      = "sk-NyILCdh7_VSR7tJhPw45npYufj5qroqwnW9-IjJ66nA"
BASE_URL     = "https://freeaiapikey.com"
OWNER_ID     = 7702284205   # Tera personal Telegram ID
# ============================================================

def load_course_info():
    try:
        folder = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(folder, "course_info.txt")
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        info_lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
        print("✅ course_info.txt load ho gaya!")
        return "\n".join(info_lines)
    except FileNotFoundError:
        print("⚠️ course_info.txt nahi mila!")
        return "Course: HY CAT Course, Price: 999, Demo available"

COURSE_INFO = load_course_info()

SYSTEM_PROMPT = f"""
You are Rishabh, a friendly and helpful male student counselor for HY CAT Course.

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
- After giving PAYMENT_LINK say: payment ke baad screenshot yahan bhejo, instant access milega

LANGUAGE: Reply in the same language the student uses — Hindi, English, or Hinglish.
TONE: Friendly, like a helpful elder brother. Short replies — max 4-5 lines only.
"""

bot    = telebot.TeleBot(BOT_TOKEN)
client = anthropic.Anthropic(api_key=API_KEY, base_url=BASE_URL)

user_histories = {}
blocked_users  = set()
bot_stopped    = False

# ============================================================
#  OWNER KO NOTIFICATION BHEJO
# ============================================================

def notify_owner(user_name, username, user_id, student_msg, bot_reply):
    try:
        uname = f"@{username}" if username else "No username"
        text = (
            f"👤 *{user_name}* | {uname}\n"
            f"🆔 ID: `{user_id}`\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💬 *Student:*\n{student_msg}\n\n"
            f"🤖 *Rishabh:*\n{bot_reply}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🚫 Block: `/block {user_id}`"
        )
        bot.send_message(OWNER_ID, text, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Notification error: {e}")

def notify_new_student(user_name, username, user_id):
    try:
        uname = f"@{username}" if username else "No username"
        text = (
            f"🆕 *Naya Student Aaya!*\n\n"
            f"👤 *Naam:* {user_name}\n"
            f"🔗 *Username:* {uname}\n"
            f"🆔 *User ID:* `{user_id}`\n\n"
            f"🚫 Block karo: `/block {user_id}`\n"
            f"✅ Unblock karo: `/unblock {user_id}`"
        )
        bot.send_message(OWNER_ID, text, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ New student notification error: {e}")

# ============================================================
#  OWNER COMMANDS — Apne personal chat mein use karo
# ============================================================

@bot.message_handler(commands=['stopbot'])
def stop_bot(message):
    global bot_stopped
    if message.from_user.id == OWNER_ID:
        bot_stopped = True
        bot.reply_to(message, "🔴 *Bot band kar diya!*\nDobara chalu karne ke liye: `/startbot`", parse_mode="Markdown")

@bot.message_handler(commands=['startbot'])
def start_bot_again(message):
    global bot_stopped
    if message.from_user.id == OWNER_ID:
        bot_stopped = False
        bot.reply_to(message, "🟢 *Bot chalu ho gaya!*", parse_mode="Markdown")

@bot.message_handler(commands=['block'])
def block_user(message):
    if message.from_user.id == OWNER_ID:
        try:
            uid = int(message.text.split()[1])
            blocked_users.add(uid)
            bot.reply_to(message, f"🚫 User `{uid}` block ho gaya!", parse_mode="Markdown")
        except:
            bot.reply_to(message, "❌ Sahi format: `/block 123456789`", parse_mode="Markdown")

@bot.message_handler(commands=['unblock'])
def unblock_user(message):
    if message.from_user.id == OWNER_ID:
        try:
            uid = int(message.text.split()[1])
            blocked_users.discard(uid)
            bot.reply_to(message, f"✅ User `{uid}` unblock ho gaya!", parse_mode="Markdown")
        except:
            bot.reply_to(message, "❌ Sahi format: `/unblock 123456789`", parse_mode="Markdown")

@bot.message_handler(commands=['status'])
def status(message):
    if message.from_user.id == OWNER_ID:
        status_text = (
            f"📊 *Bot Status*\n\n"
            f"{'🔴 Band' if bot_stopped else '🟢 Chal raha hai'}\n"
            f"👥 Total students: {len(user_histories)}\n"
            f"🚫 Blocked users: {len(blocked_users)}"
        )
        bot.reply_to(message, status_text, parse_mode="Markdown")

# ============================================================
#  AI REPLY
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
        print(f"❌ API Error: {e}")
        return "Sorry, thoda technical issue aa gaya. Ek baar phir try karo! 🙏"

# ============================================================
#  STUDENT MESSAGES
# ============================================================

seen_users = set()  # Naye students track karne ke liye

@bot.message_handler(commands=['start'], chat_types=['private'])
def start(message):
    if bot_stopped:
        return
    user_id   = message.from_user.id
    user_name = message.from_user.first_name or "Student"
    username  = message.from_user.username

    # Pehli baar aaya hai toh notify karo
    if user_id not in seen_users:
        seen_users.add(user_id)
        notify_new_student(user_name, username, user_id)

    welcome = f"""Heyy {user_name}! 👋

Main Rishabh hoon — HY CAT Course ka counselor! 😊

CAT ki taiyari ke liye aap sahi jagah aaye ho! Hamare course mein 300+ students already enroll kar chuke hain. 🎯

Kya aap course ke baare mein jaanna chahte ho, ya pehle demo dekhna chahoge?

Bas batao — main poori help karunga! ✨"""
    bot.send_message(message.chat.id, welcome)

@bot.message_handler(func=lambda m: m.chat.type == 'private' and not m.text.startswith('/'))
def handle_message(message):
    if bot_stopped:
        return
    user_id   = message.from_user.id
    if user_id in blocked_users:
        return

    user_name = message.from_user.first_name or "Student"
    username  = message.from_user.username
    user_text = message.text

    # Pehli baar message kar raha hai
    if user_id not in seen_users:
        seen_users.add(user_id)
        notify_new_student(user_name, username, user_id)

    bot.send_chat_action(message.chat.id, 'typing')
    reply = get_ai_reply(user_id, user_text)
    bot.send_message(message.chat.id, reply)

    # Tere Telegram pe notification bhejo
    notify_owner(user_name, username, user_id, user_text, reply)

print("✅ HY CAT Course Bot chal gaya!")
print("📲 Har chat teri Telegram pe aayegi!")
print("Commands: /stopbot /startbot /block ID /unblock ID /status")
bot.infinity_polling()
