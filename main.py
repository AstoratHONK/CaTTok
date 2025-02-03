from fastapi import FastAPI
import subprocess

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Сервер работает!"}

@app.post("/run_parser")
def run_parser():
    try:
        subprocess.run(["python", "parcing_cat_video.py"], check=True)
        return {"status": "Парсер запущен!"}
    except Exception as e:
        return {"error": str(e)}

