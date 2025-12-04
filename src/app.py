import os

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from utils.document_process import download_file, process_file

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Welcome to the Document Processing API"}


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
        return {"status": "success", "response": response}

    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
