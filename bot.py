import os
import re
import telebot
import yt_dlp
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import threading

# .env file se variables load kar rahe hain
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

if not TOKEN:
    print("❌ BOT_TOKEN nahi mila! Please .env file check karo.")
    exit()

# Bot initialize kar rahe hain
bot = telebot.TeleBot(TOKEN)
print("✅ Naya bot successfully start ho gaya hai (yt-dlp + buttons + auto-delete)...")

# User requests temporarily store karne ke liye dictionary taaki callback data limit cross na ho
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

        # yt-dlp options (sirf info nikalne ke liye, download nahi)
        ydl_opts = {
            'cookiefile': 'cookies.txt', # Tumhari file jo login issues rokegi
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(original_url, download=False)
                formats = info.get('formats', [])
                
                available_qualities = {}
                
                # Formats filter karna jo mp4 hain aur jinme height (resolution) hai
                for f in formats:
                    height = f.get('height')
                    ext = f.get('ext')
                    format_id = f.get('format_id')
                    
                    # Duplicate heights hata kar sirf valid mp4 store kar rahe hain
                    if height and ext == 'mp4':
                        available_qualities[f"{height}p"] = format_id

                if not available_qualities:
                    bot.edit_message_text("❌ Is video me alag-alag qualities nahi mili ya format support nahi kar raha.", chat_id, wait_msg.message_id)
                    return

                # Callback me poora URL bhejna possible nahi hota (64 byte limit), isliye session me save kar rahe hain
                user_requests[chat_id] = {
                    'url': original_url,
                    'qualities': available_qualities,
                    'msg_id': wait_msg.message_id
                }

                # Inline Buttons banana
                markup = InlineKeyboardMarkup()
                for quality, f_id in available_qualities.items():
                    # Callback data me quality bhejenge
                    button = InlineKeyboardButton(text=quality, callback_data=f"dl_{quality}")
                    markup.add(button)

                bot.edit_message_text("🎥 Video available hai! Niche se quality select karo:", chat_id, wait_msg.message_id, reply_markup=markup)

        except Exception as e:
            print(f"❌ yt-dlp Fetch Error: {e}")
            bot.edit_message_text("❌ Details fetch karne me error aayi. Cookies ya link verify karo.", chat_id, wait_msg.message_id)
            
    elif not text.startswith('/'):
        bot.reply_to(message, "❌ Please sirf valid Twitter (X) ka link hi bhejo.")

# Button click (callback) handle karna
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
    
    # Download process ko background thread me daal rahe hain taaki bot baki users ke liye block na ho
    threading.Thread(target=download_and_send_video, args=(chat_id, original_url, format_id, msg_id)).start()

# Asynchronous download aur send function
def download_and_send_video(chat_id, url, format_id, msg_id):
    # Ek unique temporary filename bana rahe hain
    temp_filename = f"temp_video_{chat_id}_{msg_id}.mp4"
    
    ydl_opts = {
        'cookiefile': 'cookies.txt',
        'format': f"{format_id}+bestaudio/best", # Video ke sath best audio merge karega
        'outtmpl': temp_filename,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        # Video local drive me download ho rahi hai
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        # Download done, ab Telegram par send karna hai
        bot.edit_message_text("📤 Uploading to Telegram... Lagbhag ho gaya!", chat_id, msg_id)
        
        with open(temp_filename, 'rb') as video_file:
            bot.send_video(chat_id, video_file, caption=f"✅ Downloaded successfully!")
            
        # Success ke baad purana processing message delete kar do
        bot.delete_message(chat_id, msg_id)
        
    except Exception as e:
        print(f"❌ Download Error: {e}")
        try:
            bot.edit_message_text("❌ Download ya upload me error aa gayi. Shayad server timeout ya FFmpeg missing hai.", chat_id, msg_id)
        except:
            pass
    finally:
        # ✅ STORAGE BACHANE KA MAIN LOGIC
        # Jaise hi video send ho jaye ya error aaye, local file ko delete kar do
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            print(f"🗑️ System drive ko full hone se bacha liya. File delete kar di: {temp_filename}")
        
        # Memory se user session clear kar do
        if chat_id in user_requests:
            del user_requests[chat_id]

# Bot ko continuously chalane ke liye
if __name__ == "__main__":
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Bot crash ho gaya: {e}")