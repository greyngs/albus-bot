from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import connect_to_mongo, close_mongo_connection
from app.dumbledore import speak_like_dumbledore

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title="Hogwarts Bot API", lifespan=lifespan)

@app.get("/")
async def root():
    return {"mensaje": "El Gran Comedor está abierto. API funcionando."}

@app.get("/test-magia")
async def probar_magia(
    mensaje: str = "Profesor, mi bot de telegram ya casi esta listo", 
    nombre: str = "Jorge", 
    casa: str = "Hufflepuff"
):
    respuesta = await speak_like_dumbledore(mensaje, nombre, casa)
    return {"Dumbledore dice": respuesta}
