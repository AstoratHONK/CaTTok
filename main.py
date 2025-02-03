from fastapi import FastAPI
import subprocess
import uvicorn
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
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

