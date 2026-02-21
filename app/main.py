from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from telegram import Update

from app.database import connect_to_mongo, close_mongo_connection
from app.dumbledore import speak_like_dumbledore
from app.bot import telegram_app, init_bot, stop_bot

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    await init_bot()
    print("🤖 Bot de Telegram inicializado.")
    yield
    await stop_bot()
    await close_mongo_connection()

app = FastAPI(title="Hogwarts Bot API", lifespan=lifespan)

@app.get("/")
async def root():
    return {"mensaje": "El Gran Comedor está abierto. API funcionando."}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        req_json = await request.json()
        update = Update.de_json(req_json, telegram_app.bot)
        await telegram_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        print(f"❌ Error procesando el webhook: {e}")
        return {"status": "error", "detalle": str(e)}
