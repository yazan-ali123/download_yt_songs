import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp
import telegram
from telegram.request import HTTPXRequest

# --- CONFIGURATION ---
BOT_TOKEN = '7688608495:AAHIY4nf30G5RO49NV-CwZJV6DcBZRratT4'
YOUR_CHAT_ID = '6033677437'
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0"

# --- APPLICATION SETUP ---
work_queue = asyncio.Queue()

async def worker():
    """The single worker that processes URLs from the queue one by one."""
    print("Worker started. Waiting for jobs...")
    while True:
        video_url = await work_queue.get()
        print(f"Worker picked up job: {video_url}")
        
        file_path = ""
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': '%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'noplaylist': True,
                'cookiefile': 'cookies.txt',
                'add_header': f'User-Agent: {USER_AGENT}',
                'sleep_interval': 5,          
                'max_sleep_interval': 15, 
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                file_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
            
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

            if file_size_mb > 49:
                warning_message = f"Download complete, but the file is {file_size_mb:.2f} MB. This is too large to send (50 MB limit)."
                await bot.send_message(chat_id=YOUR_CHAT_ID, text=warning_message)
            else:
                await bot.send_audio(chat_id=YOUR_CHAT_ID, audio=open(file_path, 'rb'))

        except Exception as e:
            error_message = f"Failed to process: {video_url}\n\nError: {str(e)}"
            print(error_message)
        
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            work_queue.task_done()
            print(f"Worker finished job: {video_url}")
            # --- NEW: Add a delay between jobs to avoid rate limiting ---
            await asyncio.sleep(5) # Wait 5 seconds before starting the next job


@asynccontextmanager
async def lifespan(app: FastAPI):
    """This function runs when the application starts."""
    asyncio.create_task(worker())
    yield


# --- Initialize FastAPI and the Telegram Bot ---
app = FastAPI(lifespan=lifespan)

# --- NEW: Increase timeouts for the bot ---
# Default is 5s, we'll increase it to 180s (3 minutes) for uploads
bot_request = HTTPXRequest(read_timeout=180, write_timeout=180, connect_timeout=30)
bot = telegram.Bot(token=BOT_TOKEN, request=bot_request)


class URLRequest(BaseModel):
    url: str


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Bot is running with a job queue."}


@app.post("/process-url/")
async def process_url_endpoint(request: URLRequest):
    """This endpoint now just adds a URL to the queue."""
    if "youtube.com" in request.url or "youtu.be" in request.url:
        await work_queue.put(request.url)
        return {"status": "success", "message": "URL has been added to the processing queue."}
    else:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL provided.")