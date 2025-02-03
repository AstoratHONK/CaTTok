from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
import os
import subprocess
import time
import random
import googleapiclient.discovery

app = FastAPI()
VIDEO_DIR = "videos"
LOG_FILE = "logs.txt"
API_KEY = os.environ.get("YOUTUBE_API_KEY")

youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)

if not os.path.exists(VIDEO_DIR):
    os.makedirs(VIDEO_DIR)

cat_queries = ["funny cat", "кот приколы", "gato lindo", "ねこ おもしろい", "котенок играется"]

def search_cat_videos():
    query = random.choice(cat_queries)
    request = youtube.search().list(q=query, part="snippet", type="video", maxResults=50, videoDuration="short")
    response = request.execute()
    return [f"https://www.youtube.com/watch?v={item['id']['videoId']}" for item in response.get("items", [])]

def download_video(video_url, output_path):
    try:
        command = ["yt-dlp", "--cookies", "cookies.txt", "-f", "best[ext=mp4]", "-o", output_path, video_url]
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def run_parser():
    try:
        while True:
            videos = search_cat_videos()
            for i, video in enumerate(videos[:100]):
                video_filename = os.path.join(VIDEO_DIR, f"cat_video_{i+1}.mp4")
                download_video(video, video_filename)
            time.sleep(43200)  # Ждать 12 часов
            for file in os.listdir(VIDEO_DIR):
                os.remove(os.path.join(VIDEO_DIR, file))
    except Exception as e:
        with open(LOG_FILE, "a") as log_file:
            log_file.write(f"Ошибка парсера: {e}\n")

@app.get("/")
def read_root():
    return {"message": "Сервер работает!"}

@app.post("/start_parser")
def start_parser(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_parser)
    return {"status": "Парсер запущен!"}

@app.get("/videos")
def list_videos():
    return JSONResponse(content={"videos": os.listdir(VIDEO_DIR)})

@app.get("/logs")
def get_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return {"logs": f.readlines()}
    return JSONResponse(content={"error": "Лог-файл не найден"}, status_code=404)

# ✅ Сначала сервер, потом в фоне парсер
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
