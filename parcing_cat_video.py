import googleapiclient.discovery
import os
import time
import subprocess
import cv2
import numpy as np
from ultralytics import YOLO
import re

# 🔹 Включить режим отладки (True = больше логов)
DEBUG = True  

# 🔹 YouTube API-ключ
API_KEY = "YOUTUBE_API_KEY"

# 🔹 Настройки
MAX_VIDEOS = 500  
MAX_DOWNLOADS = 50  
VIDEO_DIR = "cat_videos/"  
PROCESSED_VIDEOS_FILE = "processed_videos.txt"  
LOG_FILE = "logs.txt"  

# 🔹 Ключевые слова для поиска
queries = ["funny cat", "cute kitten", "crazy cat moments", "kitten exploring"]

# 🔹 Фильтр AI-генерированных видео и анимаций
ban_words = ["compilation", "mix", "AI", "GAN", "animation", "dance", "CGI", "cartoon", "plasticine", "synthesized", "3d model"]

# 🔹 Инициализация YouTube API
youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)

# 🔹 Загружаем YOLOv8
model = YOLO("yolov8s.pt")

# 🔹 Функция логирования
def log(msg):
    if DEBUG:
        print(msg)

def log_rejection(video_url, reason):
    with open(LOG_FILE, "a") as f:
        f.write(f"{video_url} - ОТКЛОНЕНО: {reason}\n")

# 🔹 Получение длительности видео
def get_video_duration(video_id):
    request = youtube.videos().list(part="contentDetails", id=video_id)
    response = request.execute()

    if "items" in response and len(response["items"]) > 0:
        duration_str = response["items"][0]["contentDetails"]["duration"]
        match = re.match(r'PT(?:(\d+)M)?(?:(\d+)S)?', duration_str)

        if match:
            minutes = int(match.group(1)) if match.group(1) else 0
            seconds = int(match.group(2)) if match.group(2) else 0
            return minutes * 60 + seconds  # Конвертируем в секунды

    return None  

# 🔹 Фильтрация по заголовку и длительности
def search_cat_videos(query, max_results=50):
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
            video_title = item["snippet"]["title"].lower()
            video_id = item["id"]["videoId"]
            video_link = f"https://www.youtube.com/watch?v={video_id}"

            # Проверка длительности
            duration = get_video_duration(video_id)
            if duration is None or duration > 30:
                log(f"⏭ Пропускаем {video_link} (длиннее 30 секунд, {duration} сек)")
                continue  

            # Фильтр AI-контента по названию
            if any(word in video_title for word in ban_words):
                log(f"⏭ Пропускаем {video_link} (AI-контент)")
                continue

            videos.append(video_link)
        
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break  

    return videos[:max_results]

# 🔹 Функция скачивания видео
def download_video(video_url, output_path):
    try:
        command = ["yt-dlp", "-f", "best[ext=mp4]", "-o", output_path, video_url]
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError:
        log(f"❌ Ошибка загрузки {video_url}")
        return False

# 🔹 Функция обработки видео
def extract_frames(video_path, frame_rate=10):
    cap = cv2.VideoCapture(video_path)
    frames = []
    count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if count % frame_rate == 0:
            frames.append(frame)
        count += 1
    cap.release()
    return frames

# 🔹 Определение котов
def detect_cat(frame):
    results = model(frame, imgsz=640)
    for obj in results[0].boxes:
        if int(obj.cls[0]) == 15:  # Кот
            return True
    return False

# 🔹 Проверка на ИИ-контент по текстуре
def detect_texture(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian > 120  # Если <120 — это скорее всего ИИ-кот

# 🔹 Проверка видео
def check_video_for_cats(video_url, save_path):
    if not download_video(video_url, save_path):
        log_rejection(video_url, "Ошибка загрузки")
        return False

    frames = extract_frames(save_path)
    if len(frames) == 0:
        log_rejection(video_url, "Видео не содержит кадров")
        os.remove(save_path)
        return False

    cat_count = sum(detect_cat(frame) for frame in frames)
    cat_probability = cat_count / len(frames)

    texture_good = sum(detect_texture(frame) for frame in frames) / len(frames) > 0.5

    if cat_probability < 0.5:
        log_rejection(video_url, "Котов в кадре < 50%")
        os.remove(save_path)
        return False

    if not texture_good:
        log_rejection(video_url, "Изображение слишком гладкое (ИИ)")
        os.remove(save_path)
        return False

    print(f"✅ Видео сохранено: {save_path}")
    with open(PROCESSED_VIDEOS_FILE, "a") as f:
        f.write(video_url + "\n")
    return True

# 🔹 Основной процесс
downloaded_videos = 0
for query in queries:
    videos = search_cat_videos(query)
    log(f"🔍 Найдено {len(videos)} видео по запросу '{query}'")

    for video in videos:
        if downloaded_videos >= MAX_DOWNLOADS:
            break

        video_filename = f"{VIDEO_DIR}cat_video_{downloaded_videos + 1}.mp4"
        log(f"🔄 Проверка: {video}")

        if check_video_for_cats(video, video_filename):
            downloaded_videos += 1

print(f"🎉 Готово! Сохранено {downloaded_videos} видео с котами.")
