import os
from pymongo import MongoClient
from datetime import datetime

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = "hogwarts"

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
points_collection = db["points"]

def add_point(person, house, points, reason):
    doc = {
        "date": datetime.now(),
        "person": person,
        "house": house,
        "points": points,
        "reason": reason
    }
    result = points_collection.insert_one(doc)
    return result.acknowledged

def get_house_scores():
    houses = ["Gryffindor", "Hufflepuff", "Ravenclaw", "Slytherin"]
    scores = {house: 0 for house in houses}
    pipeline = [
        {"$group": {"_id": "$house", "total": {"$sum": "$points"}}}
    ]
    for row in points_collection.aggregate(pipeline):
        house = row["_id"]
        if house in scores:
            scores[house] = row["total"]
    return scores 