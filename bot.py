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
from dotenv import load_dotenv

# --- LOCAL ENVIRONMENT SETUP ---
# Yeh local PC par testing ke liye .env file se token uthayega
load_dotenv()

# --- FLASK SERVER (Render.com 24/7 Setup) ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "[SYSTEM STATUS: ONLINE] ZORK DI Tactical Extraction Node is running at optimal capacity."

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- BOT CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# --- YOUTUBE ANTI-BLOCK SYSTEM ---
def get_base_ydl_opts():
    """
    Smart config function: Sets up client spoofing and uses cookies.txt if available.
    """
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        # Android aur Web client ko spoof kar rahe hain taaki bot block na ho
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
    }
    # Agar cookies.txt file exist karti hai, toh bot automatically use karega
    if os.path.exists('cookies.txt'):
        opts['cookiefile'] = 'cookies.txt'
    return opts

# --- CORE DOWNLOADING & METADATA FUNCTIONS ---
def fetch_video_metadata(url):
    """
    Smart Background Process: Extracts video metadata and available dynamic resolutions.
    Detects 4K, 2K, 1080p based on actual availability.
    """
    ydl_opts = get_base_ydl_opts()
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            
            # Scan for all available unique heights (resolutions)
            resolutions = set()
            for f in formats:
                height = f.get('height')
                vcodec = f.get('vcodec')
                if height and vcodec != 'none':
                    resolutions.add(height)
            
            # Sort descending to show highest quality first
            sorted_res = sorted(list(resolutions), reverse=True)
            
            # Keep up to top 4 highest unique resolutions to maintain a premium UI
            available_options = sorted_res[:4]

            # Get video title safely
            title = info.get('title', 'Classified Asset')
            return True, available_options, title
    except Exception as e:
        return False, str(e), None

def download_media(url, quality, file_name):
    """
    Actual extraction protocol running in background thread.
    Handles both Video resolutions and MP3 Audio with Anti-Block features.
    """
    ydl_opts = get_base_ydl_opts()
    ydl_opts['outtmpl'] = file_name
    ydl_opts['socket_timeout'] = 30
    ydl_opts['retries'] = 5

    if quality == 'mp3':
        # Audio Only Setup
        ydl_opts['format'] = 'bestaudio/best'
    else:
        # Video + Audio Setup
        format_string = f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best'
        ydl_opts['format'] = format_string
        ydl_opts['merge_output_format'] = 'mp4'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            return True, None
    except Exception as e:
        return False, str(e)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "📟 `\\[SYSTEM BOOT SEQUENCE INITIATED]`\n"
        "📡 `\\[CONNECTING TO ZORK DI MAINFRAME...]`\n"
        "🔐 `\\[SECURE HANDSHAKE: SUCCESS]`\n\n"
        "Greetings, Operator. I am the *Tactical Media Extraction Node*.\n"
        "Engineered for high-tier payload retrieval across global network grids.\n\n"
        "📍 *Directive:* Transmit target coordinates (URL) to initiate surveillance."
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    # --- ZORK DI IDENTITY LOGIC (Smart Personality) ---
    identity_keywords = ["who made you", "creator", "naam kya hai", "who are you", "zork di", "banaya kisne", "boss", "command"]
    if any(keyword in text for keyword in identity_keywords):
        identity_text = (
            "🛡️ *\\[CLEARANCE LEVEL VERIFIED]*\n\n"
            "I am an elite cybernetic extraction protocol, forged by the architects at *ZORK DI*.\n"
            "My neural processing outpaces civilian models. I exist to execute flawless data retrieval.\n\n"
            "Awaiting your next directive, Commander."
        )
        await update.message.reply_text(identity_text, parse_mode=ParseMode.MARKDOWN)
        return

    # --- SMART URL EXTRACTION ---
    url_pattern = re.search(r'(https?://[^\s]+)', update.message.text)
    
    if not url_pattern:
        await update.message.reply_text(
            "⚠️ *\\[CRITICAL ALERT]*\nInvalid coordinates detected. Radar scan failed to locate a verified protocol. Please recalibrate.", 
            parse_mode=ParseMode.MARKDOWN
        )
        return

    url = url_pattern.group(1)
    context.user_data['video_url'] = url

    # --- DYNAMIC RADAR SCAN PHASE ---
    scan_msg = await update.message.reply_text(
        "📡 *\\[RADAR ACTIVE]*\nScanning target coordinates for available payload densities. Please wait...", 
        parse_mode=ParseMode.MARKDOWN
    )

    # Fetch available resolutions and title dynamically
    success, options, title = await asyncio.to_thread(fetch_video_metadata, url)

    if not success or not options:
        await scan_msg.edit_text(
            f"❌ *\\[TARGET EVASIVE]*\nUnable to penetrate server firewalls. Asset might be private, geo-restricted, or unsupported.\n\n_System Diagnostics: {options}_",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # --- DYNAMIC TACTICAL UI BUILDER ---
    keyboard = []
    
    # Video Options
    for res in options:
        if res >= 2160:
            label = f"[ 🌌 {res}p | 4K ULTRA OMEGA ]"
        elif res >= 1440:
            label = f"[ ☄️ {res}p | 2K QUAD HD ]"
        elif res >= 1080:
            label = f"[ 🛰️ {res}p | MAXIMUM OVERRIDE ]"
        elif res >= 720:
            label = f"[ ⚡ {res}p | STANDARD PROTOCOL ]"
        else:
            label = f"[ 🔋 {res}p | OPTIMIZED BANDWIDTH ]"
        
        keyboard.append([InlineKeyboardButton(label, callback_data=str(res))])

    # Audio Option (MP3)
    keyboard.append([InlineKeyboardButton("[ 🎵 High-Res MP3 Audio ]", callback_data="mp3")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Clean title for Markdown formatting
    safe_title = title.replace('*', '').replace('_', '').replace('[', '').replace(']', '').replace('`', '')

    await scan_msg.edit_text(
        f"🎯 *\\[TARGET LOCKED]*\n*Asset:* `{safe_title}`\n\nSelect payload density for immediate extraction:", 
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
            "❌ *\\[SYSTEM FAULT]*\nTarget URL purged from temporary memory to prevent tracing. Re-initialize the sequence.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Step 1: Initialize
    status_message = await query.edit_message_text(
        f"\\[⚙️ COMMAND RECOGNIZED]\nRunning tactical analysis on target coordinates...\n\\[🔍 BYPASSING] Neutralizing host security layers...",
        parse_mode=ParseMode.MARKDOWN
    )

    # Unique ID generation & File Extension Check
    is_audio = (quality == 'mp3')
    ext = 'mp3' if is_audio else 'mp4'
    unique_id = str(uuid.uuid4())[:8]
    file_name = f'payload_{chat_id}_{unique_id}.{ext}'

    # Step 2: Extraction Phase
    extraction_text = "\\[📥 ACQUIRING PAYLOAD] Extracting audio waves..." if is_audio else f"\\[📥 ACQUIRING PAYLOAD] Extracting neural net data at {quality}p..."
    await context.bot.edit_message_text(
        chat_id=chat_id, 
        message_id=status_message.message_id, 
        text=f"{extraction_text}\n⚠️ _Background extraction active. Do not terminate connection._",
        parse_mode=ParseMode.MARKDOWN
    )

    # Background Thread execution
    success, error_msg = await asyncio.to_thread(download_media, url, quality, file_name)

    if success and os.path.exists(file_name):
        file_size_mb = os.path.getsize(file_name) / (1024 * 1024)

        # Telegram 50MB Limit Check
        if file_size_mb > 49.5:
            await context.bot.edit_message_text(
                chat_id=chat_id, 
                message_id=status_message.message_id, 
                text=f"🛑 *\\[RESTRICTION ENFORCED]*\nPayload mass is {file_size_mb:.1f} MB. Telegram grid restricts transmissions to 50 MB.\n_Mission Aborted. Wiping localized data._",
                parse_mode=ParseMode.MARKDOWN
            )
            os.remove(file_name)
            return

        # Step 3: Secure Uplink
        await context.bot.edit_message_text(
            chat_id=chat_id, 
            message_id=status_message.message_id, 
            text="\\[📡 ESTABLISHING UPLINK]\nEncryption algorithm: AES-256 applied. Uploading payload to secure Telegram grid...",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            with open(file_name, 'rb') as media_file:
                caption_text = (
                    f"✅ *TACTICAL EXTRACTION COMPLETE*\n\n"
                    f"▫️ **Asset Type:** {'MP3 Audio' if is_audio else f'{quality}p Video'}\n"
                    f"▫️ **Payload Mass:** {file_size_mb:.1f} MB\n"
                    f"▫️ **Security Status:** CLEARED\n\n"
                    f"🛡️ **Commanded by:** ZORK DI"
                )

                if is_audio:
                    await context.bot.send_audio(
                        chat_id=chat_id,
                        audio=media_file,
                        caption=caption_text,
                        parse_mode=ParseMode.MARKDOWN,
                        read_timeout=120, 
                        write_timeout=120 
                    )
                else:
                    await context.bot.send_video(
                        chat_id=chat_id,
                        video=media_file,
                        caption=caption_text,
                        parse_mode=ParseMode.MARKDOWN,
                        supports_streaming=True,
                        read_timeout=120, 
                        write_timeout=120 
                    )
            
            # Wipe telemetry logs after successful operation
            await context.bot.delete_message(chat_id=chat_id, message_id=status_message.message_id)
            
        except Exception as e:
            await context.bot.edit_message_text(
                chat_id=chat_id, 
                message_id=status_message.message_id, 
                text=f"❌ *\\[UPLINK FAILED]*\nSignal interference during payload delivery. Transmission dropped. Try again.\n\nError: {e}",
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            # Clean up local node space
            if os.path.exists(file_name):
                os.remove(file_name)

    else:
        # Handling extraction failures (Private/Geo-blocked)
        await context.bot.edit_message_text(
            chat_id=chat_id, 
            message_id=status_message.message_id, 
            text=f"❌ *\\[TARGET EVASIVE]*\nPlatform defense systems blocked the request, or the intel is classified.\n\n_Diagnostic Code: {error_msg}_",
            parse_mode=ParseMode.MARKDOWN
        )

def main():
    # Validating environment integrity
    if not BOT_TOKEN:
        print("❌ [CRITICAL SYSTEM FAILURE]: BOT_TOKEN is missing! Provide coordinates via .env file or Render Environment Variables.")
        return

    # Booting daemon server
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # Initializing Mainframe
    application = Application.builder().token(BOT_TOKEN).pool_timeout(60).connect_timeout(60).read_timeout(60).write_timeout(60).build()

    # Deploying Protocol Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_click))

    print("🛡️ [ZORK DI MAINFRAME ONLINE] Scanning grid for communications...")
    application.run_polling()

if __name__ == '__main__':
    main()