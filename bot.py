import os
import re
import threading
import telebot
import yt_dlp
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from flask import Flask

# .env file se variables load kar rahe hain
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
PORT = int(os.getenv('PORT', 8080)) # Render ke liye port fetch karna, default 8080

if not TOKEN:
    print("❌ BOT_TOKEN nahi mila! Please .env file check karo.")
    exit()

# ======= FLASK SERVER SETUP (Render Health Check ke liye) =======
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly!"

def run_flask():
    # Flask ko 0.0.0.0 par chalana zaroori hai taaki external connections (Render) check kar sakein
    app.run(host="0.0.0.0", port=PORT)

# Flask server ko ek background thread me start kar rahe hain
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
print(f"✅ Web server port {PORT} par start ho gaya hai (Render health check pass karne ke liye).")
# ================================================================

# Bot initialize kar rahe hain
bot = telebot.TeleBot(TOKEN)
print("✅ Telegram Bot successfully start ho gaya hai...")

# User requests temporarily store karne ke liye dictionary
user_requests = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hello! 👋 Mujhe Twitter (X) ka koi bhi video link bhejo, main tumhe quality select karne ka option dunga.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text
    chat_id = message.chat.id
    if not text:
        return
    
    # Twitter ya X link detect karna
    twitter_regex = r"(https?:\/\/(?:www\.)?(?:twitter\.com|x\.com)\/[a-zA-Z0-9_]+\/status\/[0-9]+)"
    match = re.search(twitter_regex, text, re.IGNORECASE)

    if match:
        original_url = match.group(1)
        wait_msg = bot.reply_to(message, "⏳ Fetching available qualities... please wait.")

        # yt-dlp options (sirf info nikalne ke liye)
        ydl_opts = {
            'cookiefile': 'cookies.txt', # Login bypass ke liye
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(original_url, download=False)
                formats = info.get('formats', [])
                
                available_qualities = {}
                
                # Formats filter karna jo mp4 hain aur jinme height hai
                for f in formats:
                    height = f.get('height')
                    ext = f.get('ext')
                    format_id = f.get('format_id')
                    
                    if height and ext == 'mp4':
                        available_qualities[f"{height}p"] = format_id

                if not available_qualities:
                    bot.edit_message_text("❌ Is video me alag-alag qualities nahi mili ya format support nahi kar raha.", chat_id, wait_msg.message_id)
                    return

                # Session me save kar rahe hain
                user_requests[chat_id] = {
                    'url': original_url,
                    'qualities': available_qualities,
                    'msg_id': wait_msg.message_id
                }

                # Inline Buttons banana
                markup = InlineKeyboardMarkup()
                for quality, f_id in available_qualities.items():
                    button = InlineKeyboardButton(text=quality, callback_data=f"dl_{quality}")
                    markup.add(button)

                bot.edit_message_text("🎥 Video available hai! Niche se quality select karo:", chat_id, wait_msg.message_id, reply_markup=markup)

        except Exception as e:
            print(f"❌ yt-dlp Fetch Error: {e}")
            bot.edit_message_text("❌ Details fetch karne me error aayi. Cookies ya link verify karo.", chat_id, wait_msg.message_id)
            
    elif not text.startswith('/'):
        bot.reply_to(message, "❌ Please sirf valid Twitter (X) ka link hi bhejo.")

# Button click handle karna
@bot.callback_query_handler(func=lambda call: call.data.startswith("dl_"))
def handle_download(call):
    chat_id = call.message.chat.id
    quality_selected = call.data.split("_")[1]
    
    if chat_id not in user_requests:
        bot.answer_callback_query(call.id, "❌ Session expire ho gaya hai. Link wapas bhejo.", show_alert=True)
        return
    
    user_data = user_requests[chat_id]
    original_url = user_data['url']
    format_id = user_data['qualities'].get(quality_selected)
    msg_id = user_data['msg_id']
    
    if not format_id:
        bot.answer_callback_query(call.id, "❌ Quality ID nahi mili.", show_alert=True)
        return

    bot.answer_callback_query(call.id)
    bot.edit_message_text(f"⏳ Downloading video in {quality_selected}...\nPlease wait, high quality me thoda time lag sakta hai.", chat_id, msg_id)
    
    # Download background thread me daalna
    threading.Thread(target=download_and_send_video, args=(chat_id, original_url, format_id, msg_id)).start()

def download_and_send_video(chat_id, url, format_id, msg_id):
    temp_filename = f"temp_video_{chat_id}_{msg_id}.mp4"
    
    ydl_opts = {
        'cookiefile': 'cookies.txt',
        'format': f"{format_id}+bestaudio/best",
        'outtmpl': temp_filename,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        bot.edit_message_text("📤 Uploading to Telegram... Lagbhag ho gaya!", chat_id, msg_id)
        
        with open(temp_filename, 'rb') as video_file:
            bot.send_video(chat_id, video_file, caption=f"✅ Downloaded successfully!")
            
        bot.delete_message(chat_id, msg_id)
        
    except Exception as e:
        print(f"❌ Download Error: {e}")
        try:
            bot.edit_message_text("❌ Download ya upload me error aa gayi.", chat_id, msg_id)
        except:
            pass
    finally:
        # Storage bachane ke liye local file delete karna
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            print(f"🗑️ File delete kar di: {temp_filename}")
        
        if chat_id in user_requests:
            del user_requests[chat_id]

if __name__ == "__main__":
    try:
        # Bot ko run karna
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Bot crash ho gaya: {e}")