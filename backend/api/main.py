import uvicorn
from fastapi import FastAPI
from .routes import upload, chat

app = FastAPI(title="Multi-Agent GreenTech Lawyer Backend")

app.include_router(upload.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
