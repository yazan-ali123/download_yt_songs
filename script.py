import os
import logging
import re
import asyncio # Import the asyncio library
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --- Basic Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = '7688608495:AAHIY4nf30G5RO49NV-CwZJV6DcBZRratT4'
YOUTUBE_URL_REGEX = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'


async def process_audio_task(url: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    The actual heavy-lifting function that runs in the background.
    This downloads, converts, and sends the audio.
    """
    try:
        # Let the user know the download is starting
        processing_message = await update.message.reply_text("🎧 Starting download and conversion... this might take a moment.")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '%(title)s.%(ext)s',
            'noplaylist': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
        
        # Edit the message to let the user know the upload is starting
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=processing_message.message_id, text="⬆️ Uploading audio...")
        
        await update.message.reply_audio(audio=open(filename, 'rb'))
        
        # Clean up by deleting the message and the file
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_message.message_id)
        os.remove(filename)

    except Exception as e:
        logger.error(f"Error processing {url}: {e}")
        # If an error happens in the background, inform the user.
        await update.message.reply_text("Sorry, I couldn't process this audio. Please check the link or try another.")


async def audio_downloader_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    This is the main handler. It responds instantly and schedules the background task.
    """
    message_text = update.message.text
    match = re.search(YOUTUBE_URL_REGEX, message_text)

    if match:
        url = match.group(0)
        
        # 1. ACKNOWLEDGE IMMEDIATELY - This is the key to avoiding timeouts.
        await update.message.reply_text("✅ Link received! I'll get to work on your audio.")
        
        # 2. SCHEDULE THE TASK - Run the heavy work in the background.
        asyncio.create_task(process_audio_task(url, update, context))


def main():
    """Starts the bot."""
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Filters for any message containing a YouTube link
    url_filter = filters.Regex(YOUTUBE_URL_REGEX)
    application.add_handler(MessageHandler(url_filter & ~filters.COMMAND, audio_downloader_handler))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()