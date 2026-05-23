import os
import threading
import asyncio
import uuid
import re
from flask import Flask
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import yt_dlp

# --- FLASK SERVER (Render.com 24/7 Setup) ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "ZORK DI Media Extraction Node is ACTIVE and running at elite capacity."

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- BOT CONFIGURATION ---
# Token environment variable se lega, agar nahi mila toh default fallback use karega
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8352970733:AAEUrMk-cUY0su4yygscDHAGLBN_2XaGZ7k")

# --- CORE DOWNLOADING FUNCTION (Runs in Background) ---
def download_media(url, quality, file_name):
    """
    Yeh function yt-dlp ko chalayega. Ise hum thread mein run karenge taaki bot hang na ho.
    Universal platform support ke liye format strictly best available filter karega.
    """
    format_string = f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best'
    
    ydl_opts = {
        'format': format_string,
        'outtmpl': file_name,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'socket_timeout': 30,
        'retries': 5,
        'merge_output_format': 'mp4', # Ensure final output is mp4
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            return True, None
    except Exception as e:
        return False, str(e)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "⚡ *ZORK DI Secure Node Connected*\n\n"
        "Greetings. I am the advanced *Media Extraction Framework*.\n"
        "Engineered for high-performance, universal media retrieval across all major grids (YouTube, X, Instagram, Facebook).\n\n"
        "🔗 *Directive:* Please drop a valid URL to initiate the secure retrieval sequence."
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    # --- ZORK DI IDENTITY LOGIC (Smart Personality) ---
    identity_keywords = ["who made you", "creator", "naam kya hai", "who are you", "zork di", "banaya kisne", "boss"]
    if any(keyword in text for keyword in identity_keywords):
        identity_text = (
            "🛡️ *Identity Confirmed.*\n\n"
            "I am an elite AI extraction protocol, engineered by the masterminds at *ZORK DI*.\n"
            "My intelligence outpaces standard bots, designed strictly for high-end, fail-proof media retrieval.\n\n"
            "Awaiting your command, Sir."
        )
        await update.message.reply_text(identity_text, parse_mode=ParseMode.MARKDOWN)
        return

    # --- SMART URL EXTRACTION ---
    # Koi text ke beech mein bhi link dega toh bot nikal lega
    url_pattern = re.search(r'(https?://[^\s]+)', update.message.text)
    
    if not url_pattern:
        await update.message.reply_text(
            "⚠️ *System Alert:* No valid protocol detected.\nPlease provide a verified HTTP/HTTPS URL.", 
            parse_mode=ParseMode.MARKDOWN
        )
        return

    url = url_pattern.group(1)
    context.user_data['video_url'] = url

    # --- VERTICAL ENTERPRISE UI (Premium Look) ---
    keyboard = [
        [InlineKeyboardButton("✨ 1080p  |  ULTRA HD EXTRACTION", callback_data='1080')],
        [InlineKeyboardButton("⚡ 720p   |  STANDARD HD SEQUENCE", callback_data='720')],
        [InlineKeyboardButton("🔋 480p   |  OPTIMIZED PAYLOAD", callback_data='480')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎯 *Target Locked.*\nSelect the desired resolution for payload extraction:", 
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 

    quality = query.data
    url = context.user_data.get('video_url')
    chat_id = query.message.chat_id

    if not url:
        await query.edit_message_text(
            "❌ *System Fault:* Target URL purged from memory. Please re-initialize the request.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Step 1: Initialize (Jarvis Style)
    status_message = await query.edit_message_text(
        f"\[⚙️ INITIALIZING] Analyzing target coordinates...\n"
        f"\[🔍 BYPASSING] Negotiating server security protocols...",
        parse_mode=ParseMode.MARKDOWN
    )

    # Unique file name to prevent clash between concurrent users
    unique_id = str(uuid.uuid4())[:8]
    file_name = f'payload_{chat_id}_{unique_id}.mp4'

    # Step 2: Extraction
    await context.bot.edit_message_text(
        chat_id=chat_id, 
        message_id=status_message.message_id, 
        text=f"\[📥 EXTRACTING] Downloading {quality}p neural payload...\n⚠️ _Please stand by, background thread active._",
        parse_mode=ParseMode.MARKDOWN
    )

    # RUNNING IN BACKGROUND THREAD (Bot won't freeze)
    success, error_msg = await asyncio.to_thread(download_media, url, quality, file_name)

    if success and os.path.exists(file_name):
        file_size_mb = os.path.getsize(file_name) / (1024 * 1024)

        # Telegram Limit Check (50 MB)
        if file_size_mb > 49.5:
            await context.bot.edit_message_text(
                chat_id=chat_id, 
                message_id=status_message.message_id, 
                text=f"🛑 *Limit Exceeded:*\nThe extracted file is {file_size_mb:.1f} MB. Telegram restricts bots to a maximum of 50 MB uploads.\n_Task Aborted._",
                parse_mode=ParseMode.MARKDOWN
            )
            os.remove(file_name)
            return

        # Step 3: Uploading
        await context.bot.edit_message_text(
            chat_id=chat_id, 
            message_id=status_message.message_id, 
            text="\[🚀 UPLOADING] Encryption complete. Establishing secure uplink to Telegram...",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            with open(file_name, 'rb') as video:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video,
                    caption=(
                        f"✅ *Extraction Successful*\n"
                        f"▫️ **Resolution:** {quality}p\n"
                        f"▫️ **Size:** {file_size_mb:.1f} MB\n"
                        f"🛡️ **Powered by:** ZORK DI"
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                    supports_streaming=True,
                    read_timeout=120, 
                    write_timeout=120 
                )
            
            # Clean up logs after success
            await context.bot.delete_message(chat_id=chat_id, message_id=status_message.message_id)
            
        except Exception as e:
            await context.bot.edit_message_text(
                chat_id=chat_id, 
                message_id=status_message.message_id, 
                text=f"❌ *Upload Failed:*\nNetwork error during payload delivery. Please try again.",
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            # File deletion to keep server space clean (Important for Render.com)
            if os.path.exists(file_name):
                os.remove(file_name)

    else:
        # Handling yt-dlp extraction failure cleanly
        await context.bot.edit_message_text(
            chat_id=chat_id, 
            message_id=status_message.message_id, 
            text=f"❌ *Extraction Failed.*\nTarget platform might have blocked the request or URL is private/geo-restricted.\n\n_System Diagnostics: {error_msg}_",
            parse_mode=ParseMode.MARKDOWN
        )

def main():
    # Start Flask Server
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # Build Application
    application = Application.builder().token(BOT_TOKEN).pool_timeout(60).connect_timeout(60).read_timeout(60).write_timeout(60).build()

    # Register Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_click))

    print("🛡️ ZORK DI Core System ONLINE. Intercepting communications...")
    application.run_polling()

if __name__ == '__main__':
    main()