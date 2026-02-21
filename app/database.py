import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from typing import Optional
from datetime import datetime, timezone

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

async def get_user(telegram_id: int) -> Optional[dict]:
    collection = db_manager.db["students"] 
    user = await collection.find_one({"telegram_id": telegram_id})
    return user

async def register_user(telegram_id: int, name: str, house: str, profession: str) -> bool:
    collection = db_manager.db["students"]
    
    existing_user = await collection.find_one({"telegram_id": telegram_id})
    if existing_user:
        return False
        
    new_student = {
        "telegram_id": telegram_id,
        "name": name,
        "house": house,
        "profession": profession,
        "total_points": 0  
    }
    
    await collection.insert_one(new_student)
    return True

async def update_house_points(house: str, points: int, reason: str, teacher_name: str) -> int:
    houses_col = db_manager.db["houses"]
    await houses_col.update_one(
        {"house": house},
        {"$inc": {"total_points": points}},
        upsert=True
    )
    
    updated_house = await houses_col.find_one({"house": house})
    nuevo_total = updated_house["total_points"]
    
    history_col = db_manager.db["points_history"]
    await history_col.insert_one({
        "house": house,
        "points": points,
        "reason": reason,
        "given_by": teacher_name,
        "timestamp": datetime.now(timezone.utc)
    })
    
    return nuevo_total

async def get_scoreboard() -> dict:
    houses_col = db_manager.db["houses"]
    cursor = houses_col.find({})
    
    scores = {"Gryffindor": 0, "Hufflepuff": 0, "Ravenclaw": 0, "Slytherin": 0}
    
    async for doc in cursor:
        scores[doc["house"]] = doc.get("total_points", 0)
        
    return scores