import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import files, chat

from db import init_db
from contextlib import asynccontextmanager

# import bridge so we can start it on app startup
from api.kafka_ws_bridge import bridge

@asynccontextmanager
async def lifespan(app: FastAPI):
    # initialize DB tables
    try:
        init_db()
    except Exception:
        pass
    # start Kafka consumer bridge
    try:
        bridge.start_in_background()
    except Exception:
        pass
    yield
    # shutdown logic can be added here if needed

app = FastAPI(title="Multi-Agent GreenTech Lawyer Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
