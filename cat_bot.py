import telebot
import anthropic
import os

# ============================================================
#  SETTINGS — Sirf yahan apni details hain
# ============================================================
BOT_TOKEN = "7602960171:AAENSFjXspMuuKBdaLIDW1yVPcsvRWZm2EM"
API_KEY   = "sk-NyILCdh7_VSR7tJhPw45npYufj5qroqwnW9-IjJ66nA"
BASE_URL  = "https://freeaiapikey.com"
# ============================================================

def load_course_info():
    """course_info.txt file padhta hai aur AI ke liye ready karta hai"""
    try:
        # Bot file ke saath wali folder mein course_info.txt dhundho
        folder = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(folder, "course_info.txt")
        
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Comments (#) wali lines ignore karo, baaki rakho
        info_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                info_lines.append(stripped)
        
        course_text = "\n".join(info_lines)
        print("✅ course_info.txt successfully load ho gaya!")
        return course_text
        
    except FileNotFoundError:
        print("⚠️  course_info.txt nahi mila! Default info use ho rahi hai.")
        return "Course: HY CAT Course, Price: 999, Demo available"

# Course info load karo
COURSE_INFO = load_course_info()

# AI ko diya jaane wala instruction
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
- After giving PAYMENT_LINK, tell them: payment ke baad screenshot yahan bhejo, instant access milega

LANGUAGE: Reply in the same language the student uses — Hindi, English, or Hinglish.
TONE: Friendly, like a helpful elder brother. Short replies — max 4-5 lines only.
"""

# Bot aur AI client setup
bot = telebot.TeleBot(BOT_TOKEN)
client = anthropic.Anthropic(api_key=API_KEY, base_url=BASE_URL)

# Har user ki conversation history store karo
user_histories = {}

def get_ai_reply(user_id, user_message):
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    user_histories[user_id].append({"role": "user", "content": user_message})
    
    # Sirf last 10 messages rakho memory bachane ke liye
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
    user_name = message.from_user.first_name or "Student"
    welcome = f"""Heyy {user_name}! 👋

Main Rishabh hoon — HY CAT Course ka counselor! 😊

CAT ki taiyari ke liye aap sahi jagah aaye ho! Hamare course mein 300+ students already enroll kar chuke hain. 🎯

Kya aap course ke baare mein jaanna chahte ho, ya pehle demo dekhna chahoge?

Bas batao — main poori help karunga! ✨"""
    bot.send_message(message.chat.id, welcome)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    user_text = message.text
    bot.send_chat_action(message.chat.id, 'typing')
    reply = get_ai_reply(user_id, user_text)
    bot.send_message(message.chat.id, reply)

print("✅ HY CAT Course Bot chal gaya! Telegram pe test karo.")
print("📄 Course info update karni ho toh course_info.txt kholo aur save karo.")
print("❌ Band karne ke liye Ctrl+C dabaao.")
bot.infinity_polling()
