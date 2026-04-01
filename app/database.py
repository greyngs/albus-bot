import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from typing import Optional
from datetime import datetime, timezone, timedelta

BOT_TZ = timezone(timedelta(hours=-5))

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

async def get_all_students() -> list[dict]:
    collection = db_manager.db["students"]
    cursor = collection.find({})
    return await cursor.to_list(length=None)

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

async def update_house_points(student_id: int, points: int, reason: str, teacher_name: str) -> dict:
    students_col = db_manager.db["students"]
    student = await students_col.find_one({"telegram_id": student_id})
    
    if not student:
        return None
        
    house = student["house"]
    student_name = student["name"]

    # 1. Update Student Points
    await students_col.update_one(
        {"telegram_id": student_id},
        {"$inc": {"total_points": points}}
    )

    # 2. Update House Points
    houses_col = db_manager.db["houses"]
    await houses_col.update_one(
        {"house": house},
        {"$inc": {"total_points": points}},
        upsert=True
    )
    # 3. Add History Record
    history_col = db_manager.db["points_history"]
    await history_col.insert_one({
        "student_id": student_id,
        "student_name": student_name,
        "house": house,
        "points": points,
        "reason": reason,
        "given_by": teacher_name,
        "timestamp": datetime.now(timezone.utc)
    })
    
    # Calculate monthly total to show properly in the chat
    now = datetime.now(BOT_TZ)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=BOT_TZ)
    pipeline = [
        {"$match": {"house": house, "timestamp": {"$gte": start_of_month}}},
        {"$group": {"_id": "$house", "monthly_total": {"$sum": "$points"}}}
    ]
    cursor = history_col.aggregate(pipeline)
    result = await cursor.to_list(length=1)
    monthly_total = result[0]["monthly_total"] if result else 0
    
    return {"house": house, "new_total": monthly_total, "student_name": student_name}

async def get_scoreboard() -> dict:
    history_col = db_manager.db["points_history"]
    
    now = datetime.now(BOT_TZ)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=BOT_TZ)
    
    pipeline = [
        {"$match": {"timestamp": {"$gte": start_of_month}}},
        {"$group": {"_id": "$house", "monthly_total": {"$sum": "$points"}}}
    ]
    
    scores = {"Gryffindor": 0, "Hufflepuff": 0, "Ravenclaw": 0, "Slytherin": 0}
    cursor = history_col.aggregate(pipeline)
    
    async for doc in cursor:
        if doc["_id"] in scores:
            scores[doc["_id"]] = doc["monthly_total"]
            
    return scores

async def add_cat_points(telegram_id: int, points: int, cat_type: str) -> dict:
    students_col = db_manager.db["students"]
    
    await students_col.update_one(
        {"telegram_id": telegram_id},
        {"$inc": {"cat_points": points}}
    )
    
    student = await students_col.find_one({"telegram_id": telegram_id})
    if not student:
        return None
        
    student_name = student["name"]
    
    history_col = db_manager.db["cat_history"]
    await history_col.insert_one({
        "student_id": telegram_id,
        "student_name": student_name,
        "cat_type": cat_type,
        "points": points,
        "timestamp": datetime.now(timezone.utc)
    })
    
    now = datetime.now(BOT_TZ)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=BOT_TZ)
    pipeline = [
        {"$match": {"student_id": telegram_id, "timestamp": {"$gte": start_of_month}}},
        {"$group": {"_id": "$student_id", "monthly_total": {"$sum": "$points"}}}
    ]
    cursor = history_col.aggregate(pipeline)
    result = await cursor.to_list(length=1)
    monthly_total = result[0]["monthly_total"] if result else 0
    
    return {"student_name": student_name, "new_total": monthly_total}

async def get_cat_scoreboard() -> list[dict]:
    history_col = db_manager.db["cat_history"]
    now = datetime.now(BOT_TZ)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=BOT_TZ)
    
    pipeline = [
        {"$match": {"timestamp": {"$gte": start_of_month}}},
        {"$group": {
            "_id": "$student_id",
            "name": {"$first": "$student_name"},
            "monthly_total": {"$sum": "$points"}
        }},
        {"$sort": {"monthly_total": -1}}
    ]
    
    cursor = history_col.aggregate(pipeline)
    
    scoreboard = []
    async for doc in cursor:
        scoreboard.append({
            "name": doc["name"],
            "points": doc["monthly_total"]
        })
        
    return scoreboard