import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "hogwarts"

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_manager = Database()

async def connect_to_mongo():
    print("🪄 Conectando a la bóveda...")
    db_manager.client = AsyncIOMotorClient(MONGO_URI)
    db_manager.db = db_manager.client[DB_NAME]
    
    try:
        await db_manager.client.admin.command('ping')
        print("✅ Conexión exitosa a la base de datos de Hogwarts.")
    except Exception as e:
        print(f"❌ Error conectando a MongoDB: {e}")

async def close_mongo_connection():
    print("Cerrando conexión a MongoDB...")
    if db_manager.client:
        db_manager.client.close()
        print("🔒 Conexión cerrada.")
