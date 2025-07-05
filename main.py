import os
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import yt_dlp
import telegram

# --- CONFIGURATION ---
# Replace these with your actual credentials
BOT_TOKEN = '7688608495:AAHIY4nf30G5RO49NV-CwZJV6DcBZRratT4'
YOUR_CHAT_ID = '6033677437'
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"

# --- Initialize FastAPI and the Telegram Bot ---
app = FastAPI()
bot = telegram.Bot(token=BOT_TOKEN)

# --- Define the data model for the incoming request ---
class URLRequest(BaseModel):
    url: str

# --- The actual downloading and sending logic ---
async def download_and_send_audio(video_url: str):
    """
    This function runs in the background to download, convert, and send the audio.
    """
    try:
        # Configure yt-dlp to download audio-only, convert to mp3
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'noplaylist': True,
            'cookiefile': 'www.youtube.com_cookies.txt',
             'add_header': f'User-Agent: {USER_AGENT}'
        }

        # Download and process the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            # The filename after conversion will be .mp3
            file_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'

        # Send the audio file to your specified chat
        await bot.send_audio(chat_id=YOUR_CHAT_ID, audio=open(file_path, 'rb'))
        
        # Clean up the downloaded file
        os.remove(file_path)

    except Exception as e:
        # If something goes wrong, send an error message
        error_message = f"Failed to process video: {video_url}\nError: {str(e)}"
        await bot.send_message(chat_id=YOUR_CHAT_ID, text=error_message)


# --- Define the API endpoint ---
@app.post("/process-url/")
async def process_url_endpoint(request: URLRequest, background_tasks: BackgroundTasks):
    """
    This is the endpoint that Make.com will call.
    It receives a URL, immediately returns a success message,
    and starts the download in the background.
    """
    if "youtube.com" in request.url or "youtu.be" in request.url:
        # Add the download task to run in the background
        background_tasks.add_task(download_and_send_audio, request.url)
        # Immediately return a response to Make.com
        return {"status": "success", "message": "Audio processing started in the background."}
    else:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL provided.")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Bot is running."}