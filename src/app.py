import os

import uvicorn
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.tts.gen_tts import generate_audio_from_text
from utils.document_process import process_file

BASE_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, os.pardir))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs")

os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/")
async def root():
    return {"message": "Welcome to the Document Processing API"}


@app.get("/app", response_class=HTMLResponse)
async def ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/process")
async def process(file: UploadFile = File(None)):
    try:
        os.makedirs("./data", exist_ok=True)

        file_path = ""
        if file:
            file_path = f"./data/{file.filename}"

            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

        response = process_file(file_path)
        audio_paths = generate_audio_from_text(response, name_hint=file.filename)
        audio_path = audio_paths[0]

        return {"status": "success", "response": response, "audio": audio_path}

    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
