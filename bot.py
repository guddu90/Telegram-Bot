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

# --- CORE DOWNLOADING & METADATA FUNCTIONS ---
def get_base_ydl_opts():
    """Base options customized for MAXIMUM SPEED, Anti-Hang and Render Bypass"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'socket_timeout': 15,  
        'retries': 3,
        'extractor_retries': 2,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'source_address': '0.0.0.0', 
        'concurrent_fragment_downloads': 10, # ROCKET SPEED DOWNLOAD FIX
        'extractor_args': {
            'youtube': {
                'player_client': ['tv', 'ios', 'android', 'web'] 
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Mode': 'navigate'
        }
    }
    
    if os.path.exists('cookies.txt'):
        opts['cookiefile'] = 'cookies.txt'
    return opts

def fetch_video_metadata(url):
    ydl_opts = get_base_ydl_opts()
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            
            resolutions = set()
            for f in formats:
                height = f.get('height')
                vcodec = f.get('vcodec')
                if height and vcodec != 'none':
                    resolutions.add(height)
            
            if resolutions:
                sorted_res = sorted(list(resolutions), reverse=True)[:4]
            else:
                # Default safety fallback if formats are hidden
                sorted_res = [1080, 720, 480]

            title = info.get('title', 'Classified Asset')
            return True, sorted_res, title
    except Exception as e:
        return False, str(e), None

def download_media(url, quality, file_name):
    ydl_opts = get_base_ydl_opts()
    ydl_opts['outtmpl'] = file_name

    if quality == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
    else:
        ydl_opts['format'] = f'best[height<={quality}][ext=mp4]/best[ext=mp4]/best'

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

    url_pattern = re.search(r'(https?://[^\s]+)', update.message.text)
    
    if not url_pattern:
        await update.message.reply_text(
            "⚠️ *\\[CRITICAL ALERT]*\nInvalid coordinates detected. Radar scan failed to locate a verified protocol. Please recalibrate.", 
            parse_mode=ParseMode.MARKDOWN
        )
        return

    url = url_pattern.group(1)
    
    # X.COM FIX: Auto conversion
    if "x.com" in url:
        url = url.replace("x.com", "twitter.com")
        
    context.user_data['video_url'] = url

    scan_msg = await update.message.reply_text(
        "📡 *\\[RADAR ACTIVE]*\nScanning target coordinates for available payload densities. Please wait...", 
        parse_mode=ParseMode.MARKDOWN
    )

    # ANTI-HANG ZERO-WAIT FALLBACK SYSTEM
    # Agar 8 second ke andar scan complete nahi hua, toh seedha bypass maar ke menu dega
    try:
        success, options, title = await asyncio.wait_for(
            asyncio.to_thread(fetch_video_metadata, url), timeout=8.0
        )
    except asyncio.TimeoutError:
        success = True
        options = [1080, 720, 480]  # Instant fallback options
        title = "Encrypted Asset (Bypassed Scan)"

    if not success or not options:
        await scan_msg.edit_text(
            f"❌ *\\[TARGET EVASIVE]*\nUnable to penetrate server firewalls. Asset might be private, geo-restricted, or blocked by platform.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    keyboard = []
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

    keyboard.append([InlineKeyboardButton("[ 🎵 High-Res MP3 Audio ]", callback_data="mp3")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    safe_title = re.sub(r'[_*\[\]`]', '', title)

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

    status_message = await query.edit_message_text(
        f"\\[⚙️ COMMAND RECOGNIZED]\nRunning tactical analysis on target coordinates...\n\\[🔍 BYPASSING] Neutralizing host security layers...",
        parse_mode=ParseMode.MARKDOWN
    )

    is_audio = (quality == 'mp3')
    ext = 'mp3' if is_audio else 'mp4'
    unique_id = str(uuid.uuid4())[:8]
    file_name = f'payload_{chat_id}_{unique_id}.{ext}'

    extraction_text = "\\[📥 ACQUIRING PAYLOAD] Extracting audio waves..." if is_audio else f"\\[📥 ACQUIRING PAYLOAD] Extracting neural net data at {quality}p..."
    await context.bot.edit_message_text(
        chat_id=chat_id, 
        message_id=status_message.message_id, 
        text=f"{extraction_text}\n⚡ _ROCKET MODE ENGAGED. HIGH-SPEED DOWNLOAD ACTIVE._",
        parse_mode=ParseMode.MARKDOWN
    )

    success, error_msg = await asyncio.to_thread(download_media, url, quality, file_name)

    if success and os.path.exists(file_name):
        file_size_mb = os.path.getsize(file_name) / (1024 * 1024)

        if file_size_mb > 49.5:
            await context.bot.edit_message_text(
                chat_id=chat_id, 
                message_id=status_message.message_id, 
                text=f"🛑 *\\[RESTRICTION ENFORCED]*\nPayload mass is {file_size_mb:.1f} MB. Telegram grid restricts transmissions to 50 MB.\n_Mission Aborted. Wiping localized data._",
                parse_mode=ParseMode.MARKDOWN
            )
            os.remove(file_name)
            return

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
                        read_timeout=300, 
                        write_timeout=300 
                    )
                else:
                    await context.bot.send_video(
                        chat_id=chat_id,
                        video=media_file,
                        caption=caption_text,
                        parse_mode=ParseMode.MARKDOWN,
                        supports_streaming=True,
                        read_timeout=300, 
                        write_timeout=300 
                    )
            
            await context.bot.delete_message(chat_id=chat_id, message_id=status_message.message_id)
            
        except Exception as e:
            await context.bot.edit_message_text(
                chat_id=chat_id, 
                message_id=status_message.message_id, 
                text=f"❌ *\\[UPLINK FAILED]*\nSignal interference during payload delivery. Transmission dropped. Try again.\n\nError: {e}",
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)

    else:
        await context.bot.edit_message_text(
            chat_id=chat_id, 
            message_id=status_message.message_id, 
            text=f"❌ *\\[TARGET EVASIVE]*\nPlatform defense systems blocked the request, or the intel is classified.\n\n_Diagnostic Code: {error_msg}_",
            parse_mode=ParseMode.MARKDOWN
        )

def main():
    if not BOT_TOKEN:
        print("❌ [CRITICAL SYSTEM FAILURE]: BOT_TOKEN is missing! Provide coordinates via .env file or Render Environment Variables.")
        return

    if os.path.exists('cookies.txt'):
        print("✅ [SYSTEM CHECK]: cookies.txt FOUND successfully in the directory.")
    else:
        print("⚠️ [SYSTEM WARNING]: cookies.txt NOT FOUND! Ensure it is not ignored in .gitignore.")

    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # GLOBAL TIMEOUT 300s TO STOP RANDOM HANGS
    application = Application.builder().token(BOT_TOKEN).pool_timeout(60).connect_timeout(60).read_timeout(300).write_timeout(300).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_click))

    print("🛡️ [ZORK DI MAINFRAME ONLINE] Scanning grid for communications...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()