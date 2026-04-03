from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import GEOSPHERE
import os
from dotenv import load_dotenv
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")#, "mongodb://localhost:27017")
DB_NAME = "washwave"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Collections
users_col = db["users"]
shops_col = db["shops"]
orders_col = db["orders"]
ratings_col = db["ratings"]

async def create_indexes():
    await shops_col.create_index([("location", GEOSPHERE)])
    await users_col.create_index([("phone", 1), ("role", 1)], unique=True)
    await shops_col.create_index("owner_id")
    await orders_col.create_index("customer_id")
    await orders_col.create_index("shop_id")
