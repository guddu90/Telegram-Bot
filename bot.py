import os
import threading
import asyncio
import uuid
import re
import aiohttp
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
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

# --- CORE DOWNLOADING FUNCTIONS ---

async def fetch_from_cobalt(url):
    """Bypasses limits using Cobalt API to fetch the absolute best available quality instantly"""
    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "url": url,
        "vQuality": "max", # Automatically grabs the highest available resolution (4K, 1080p, whatever exists)
        "filenamePattern": "classic"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") in ["redirect", "stream"]:
                        return data.get("url")
    except Exception as e:
        print(f"[COBALT API ERROR]: {e}")
    return None

def download_with_ytdlp(url, file_name):
    """Fallback Engine: Uses optimized yt-dlp if API fails"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        # BUG FIXED: Added ext= before m4a to resolve invalid filter specification
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': file_name,
        'max_filesize': 49.5 * 1024 * 1024, # Stops Render server from hanging on massive files
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        },
        'sleep_interval': 1,
        'max_sleep_interval': 3
    }
    
    if os.path.exists('cookies.txt'):
        opts['cookiefile'] = 'cookies.txt'

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
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
        "📍 *Directive:* Transmit target coordinates (URL) to initiate immediate extraction."
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    # ZORK DI Identity Logic
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
            "⚠️ *\\[CRITICAL ALERT]*\nInvalid coordinates detected. Radar scan failed. Please recalibrate.", 
            parse_mode=ParseMode.MARKDOWN
        )
        return

    url = url_pattern.group(1)
    
    # Twitter Fast-Route Fix
    if "x.com" in url:
        url = url.replace("x.com", "twitter.com")

    chat_id = update.message.chat_id

    # Instant Action - No Buttons
    status_message = await update.message.reply_text(
        "🎯 *\\[TARGET LOCKED - INSTANT MODE]*\n"
        "\\[⚙️ COMMAND RECOGNIZED] Auto-detecting maximum available quality...\n"
        "\\[🔍 BYPASSING] Neutralizing host security layers...",
        parse_mode=ParseMode.MARKDOWN
    )

    caption_text = (
        f"✅ *TACTICAL EXTRACTION COMPLETE*\n\n"
        f"▫️ **Asset Mode:** Max Available Resolution\n"
        f"▫️ **Security Status:** CLEARED\n\n"
        f"🛡️ **Commanded by:** ZORK DI"
    )

    # 1st Attempt: Ultra-Fast API Bypass
    direct_url = await fetch_from_cobalt(url)

    if direct_url:
        try:
            await context.bot.send_video(
                chat_id=chat_id,
                video=direct_url,
                caption=caption_text,
                parse_mode=ParseMode.MARKDOWN,
                read_timeout=120,
                write_timeout=120
            )
            await status_message.delete()
            return
        except Exception as e:
            print(f"[DIRECT UPLOAD FAILED]: {e}. Falling back to deep extraction.")

    # 2nd Attempt: yt-dlp Deep Extraction Fallback
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=status_message.message_id,
        text="⚠️ *\\[API EVADED]*\nTarget platform is resisting. Initiating deep extraction via backup engine...\n_Please hold, compiling maximum available format..._",
        parse_mode=ParseMode.MARKDOWN
    )

    unique_id = str(uuid.uuid4())[:8]
    file_name = f'payload_{chat_id}_{unique_id}.mp4'

    try:
        success, error_msg = await asyncio.wait_for(
            asyncio.to_thread(download_with_ytdlp, url, file_name), timeout=300.0
        )
    except asyncio.TimeoutError:
        await context.bot.edit_message_text(
            chat_id=chat_id, 
            message_id=status_message.message_id, 
            text="❌ *\\[DOWNLOAD TIMEOUT]*\nHost server is tarpitting the connection. Operation force-aborted.",
            parse_mode=ParseMode.MARKDOWN
        )
        if os.path.exists(file_name):
            os.remove(file_name)
        return

    if success and os.path.exists(file_name):
        file_size_mb = os.path.getsize(file_name) / (1024 * 1024)

        if file_size_mb > 49.5:
            await context.bot.edit_message_text(
                chat_id=chat_id, 
                message_id=status_message.message_id, 
                text=f"🛑 *\\[RESTRICTION ENFORCED]*\nPayload mass is {file_size_mb:.1f} MB. Telegram grid restricts transmissions to 50 MB.\n_Mission Aborted._",
                parse_mode=ParseMode.MARKDOWN
            )
            os.remove(file_name)
            return

        await context.bot.edit_message_text(
            chat_id=chat_id, 
            message_id=status_message.message_id, 
            text="\\[📡 ESTABLISHING UPLINK]\nAES-256 applied. Uploading payload to secure Telegram grid...",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            with open(file_name, 'rb') as media_file:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=media_file,
                    caption=caption_text + f"\n▫️ **Payload Mass:** {file_size_mb:.1f} MB",
                    parse_mode=ParseMode.MARKDOWN,
                    read_timeout=120, 
                    write_timeout=120 
                )
            await status_message.delete()
        except Exception as e:
            await context.bot.edit_message_text(
                chat_id=chat_id, 
                message_id=status_message.message_id, 
                text=f"❌ *\\[UPLINK FAILED]*\nSignal interference during payload delivery.\n\nError: {e}",
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)
    else:
        await context.bot.edit_message_text(
            chat_id=chat_id, 
            message_id=status_message.message_id, 
            text=f"❌ *\\[TARGET EVASIVE]*\nPlatform defense systems blocked the request.\n\n_Diagnostic Code: {error_msg}_",
            parse_mode=ParseMode.MARKDOWN
        )

def main():
    if not BOT_TOKEN:
        print("❌ [CRITICAL SYSTEM FAILURE]: BOT_TOKEN is missing!")
        return

    if os.path.exists('cookies.txt'):
        print("✅ [SYSTEM CHECK]: cookies.txt FOUND successfully in the directory.")
    else:
        print("⚠️ [SYSTEM WARNING]: cookies.txt NOT FOUND! YouTube downloads might be restricted.")

    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    application = Application.builder().token(BOT_TOKEN).pool_timeout(60).connect_timeout(60).read_timeout(120).write_timeout(120).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🛡️ [ZORK DI MAINFRAME ONLINE] Cobalt API Bypass Active...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()