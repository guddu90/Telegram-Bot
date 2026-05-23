import os
import threading
from flask import Flask
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# --- FLASK SERVER (Render.com 24/7 Setup) ---
# Yeh chhota sa server background mein chalega taaki Render isko website samajh kar live rakhe.
app = Flask(__name__)

@app.route('/')
def health_check():
    return "ZORK DI Media Extraction Node is ACTIVE and running at optimal capacity."

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- BOT CONFIGURATION ---
BOT_TOKEN = "8352970733:AAEUrMk-cUY0su4yygscDHAGLBN_2XaGZ7k"

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Greetings. I am the ZORK DI Media Extraction Protocol. 🤖\n\n"
        "Engineered for high-performance media retrieval. "
        "Please initialize the process by providing a target video URL."
    )
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    # --- ZORK DI IDENTITY LOGIC ---
    identity_keywords = ["who made you", "creator", "naam kya hai", "who are you", "zork di", "banaya kisne"]
    if any(keyword in text for keyword in identity_keywords):
        identity_text = (
            "I am an advanced media extraction AI, engineered and deployed by the elite developers at ZORK DI. 🛡️\n\n"
            "My core directive is to provide seamless, high-speed media downloads with absolute precision. "
            "How may I assist you today?"
        )
        await update.message.reply_text(identity_text)
        return

    url = update.message.text

    # URL Check
    if "http" not in url:
        await update.message.reply_text("System Error: Invalid protocol. Please provide a verified HTTP/HTTPS URL.")
        return

    context.user_data['video_url'] = url

    keyboard = [
        [
            InlineKeyboardButton("1080p [ULTRA HD]", callback_data='1080'),
            InlineKeyboardButton("720p [STANDARD HD]", callback_data='720'),
            InlineKeyboardButton("480p [OPTIMIZED]", callback_data='480')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Target acquired. Select extraction resolution:", reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 

    quality = query.data
    url = context.user_data.get('video_url')
    chat_id = query.message.chat_id

    if not url:
        await query.edit_message_text("System Fault: Target URL purged from memory. Please re-initialize the request.")
        return

    status_message = await query.edit_message_text(f"⏳ Initiating {quality}p Neural Download Protocol. Bypassing restrictions... Please stand by.")

    format_string = f'best[height<={quality}][ext=mp4]/best[ext=mp4]/best'

    ydl_opts = {
        'format': format_string,
        'outtmpl': f'video_{chat_id}.%(ext)s',
        'quiet': True,
        'noplaylist': True,
        'socket_timeout': 60, 
        'retries': 10, 
        'fragment_retries': 10,
        'nocheckcertificate': True,
    }

    file_name = f'video_{chat_id}.mp4'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        await context.bot.edit_message_text(
            chat_id=chat_id, 
            message_id=status_message.message_id, 
            text="🚀 Extraction Complete. Encrypting payload and establishing secure uplink to Telegram..."
        )

        with open(file_name, 'rb') as video:
            await context.bot.send_video(
                chat_id=chat_id,
                video=video,
                caption=f"✅ **Extraction Successful**\nResolution: {quality}p\nPowered by: **ZORK DI**",
                supports_streaming=True,
                read_timeout=120, 
                write_timeout=120 
            )

        await context.bot.delete_message(chat_id=chat_id, message_id=status_message.message_id)

    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=chat_id, 
            message_id=status_message.message_id, 
            text=f"❌ Extraction Failed. Critical Error Log: {str(e)}"
        )
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

def main():
    # Render ke liye Flask server ko alag thread mein start karna
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    application = Application.builder().token(BOT_TOKEN).pool_timeout(60).connect_timeout(60).read_timeout(60).write_timeout(60).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_click))

    print("ZORK DI Media Extraction Node is ONLINE. Awaiting commands...")
    application.run_polling()

if __name__ == '__main__':
    main()