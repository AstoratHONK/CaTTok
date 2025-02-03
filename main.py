from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
import os
import uuid
import subprocess
import time
import random
import googleapiclient.discovery

app = FastAPI()
VIDEO_DIR = "videos"
PROCESSED_VIDEOS_FILE = "processed_videos.txt"
LOG_FILE = "logs.txt"
API_KEY = os.environ.get("YOUTUBE_API_KEY")

youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)

if not os.path.exists(VIDEO_DIR):
    os.makedirs(VIDEO_DIR)

# Список случайных запросов о котах
cat_queries = [
    "funny cat", "кот приколы", "gato lindo", "ねこ おもしろい", "котенок играется",
    "cute kitten", "crazy cat", "кот мурчит", "chat drole", "katze lustig"
]

# Функция поиска видео
def search_cat_videos(max_results=50):
    query = random.choice(cat_queries)  # Выбираем случайный запрос
    videos = []
    next_page_token = None

    while len(videos) < max_results:
        request = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=50,
            videoDuration="short",
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response.get("items", []):
            video_id = item["id"]["videoId"]
            video_link = f"https://www.youtube.com/watch?v={video_id}"
            videos.append(video_link)

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return videos[:max_results]

# Функция загрузки видео (первые 30 секунд)
def download_video(video_url, output_path):
    try:
        command = ["yt-dlp", "-f", "best[ext=mp4]", "--postprocessor-args", "-t 30", "-o", output_path, video_url]
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

# Фоновая задача парсера
def run_parser():
    downloaded_videos = 0
    while downloaded_videos < 100:
        videos = search_cat_videos()
        for video in videos:
            if downloaded_videos >= 100:
                break
            video_filename = os.path.join(VIDEO_DIR, f"cat_video_{downloaded_videos + 1}.mp4")
            if download_video(video, video_filename):
                downloaded_videos += 1
    time.sleep(43200)  # Ждём 12 часов
    for file in os.listdir(VIDEO_DIR):
        os.remove(os.path.join(VIDEO_DIR, file))
    run_parser()  # Перезапускаем

@app.get("/")
def read_root():
    return {"message": "Сервер работает!"}

@app.post("/start_parser")
def start_parser(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_parser)
    return {"status": "Парсер запущен!"}

@app.get("/videos")
def list_videos():
    videos = [
        {"id": file.split(".")[0], "url": f"/video/{file.split('.')[0]}"}
        for file in os.listdir(VIDEO_DIR) if file.endswith(".mp4")
    ]
    return JSONResponse(content={"videos": videos})

@app.get("/video/{video_id}")
def get_video(video_id: str):
    file_path = os.path.join(VIDEO_DIR, f"{video_id}.mp4")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="video/mp4")
    return JSONResponse(content={"error": "Видео не найдено"}, status_code=404)

# 🔹 API для просмотра файлов в директории
@app.get("/list_dir")
def list_directory(path: str = Query("videos")):
    if os.path.exists(path) and os.path.isdir(path):
        return {"files": os.listdir(path)}
    return JSONResponse(content={"error": "Директория не найдена"}, status_code=404)

# 🔹 API для просмотра логов
@app.get("/logs")
def get_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return {"logs": f.readlines()}
    return JSONResponse(content={"error": "Лог-файл не найден"}, status_code=404)

# 🔹 API для скачивания видео
@app.get("/download/{video_id}")
def download_video_file(video_id: str):
    file_path = os.path.join(VIDEO_DIR, f"{video_id}.mp4")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="video/mp4", filename=f"{video_id}.mp4")
    return JSONResponse(content={"error": "Видео не найдено"}, status_code=404)

# Автоматический запуск парсера при старте сервера
run_parser()
