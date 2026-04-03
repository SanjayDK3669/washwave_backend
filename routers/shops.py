from fastapi import APIRouter, HTTPException, Depends
from database import shops_col, ratings_col
from models.schemas import ShopUpdate
from utils.jwt_handler import get_current_user, require_owner
from bson import ObjectId
from datetime import datetime

router = APIRouter()

def serialize(doc):
    doc = dict(doc)
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc

@router.get("/my-shop")
async def get_my_shop(user=Depends(require_owner)):
    shop = await shops_col.find_one({"owner_id": user["user_id"]})
    if not shop:
        raise HTTPException(status_code=404, detail="No shop found")
    return serialize(shop)

@router.put("/my-shop")
async def update_shop(data: ShopUpdate, user=Depends(require_owner)):
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    if "services" in update_data:
        update_data["services"] = [s.value for s in update_data["services"]]
    if "location" in update_data and hasattr(update_data["location"], "dict"):
        update_data["location"] = update_data["location"].dict()
    await shops_col.update_one(
        {"owner_id": user["user_id"]},
        {"$set": {**update_data, "updated_at": datetime.utcnow()}}
    )
    shop = await shops_col.find_one({"owner_id": user["user_id"]})
    return serialize(shop)

@router.get("/nearby")
async def get_nearby_shops(lat: float, lng: float, radius: float = 5000):
    cursor = shops_col.find({
        "location": {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [lng, lat]},
                "$maxDistance": radius
            }
        },
        "is_active": True
    })
    shops = []
    async for shop in cursor:
        shops.append(serialize(shop))
    return shops

@router.get("/all")
async def get_all_shops():
    cursor = shops_col.find({"is_active": True})
    shops = []
    async for shop in cursor:
        shops.append(serialize(shop))
    return shops

@router.get("/{shop_id}")
async def get_shop(shop_id: str):
    shop = await shops_col.find_one({"_id": ObjectId(shop_id)})
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    s = serialize(shop)
    cursor = ratings_col.find({"shop_id": shop_id}).sort("created_at", -1).limit(10)
    reviews = []
    async for r in cursor:
        r["id"] = str(r["_id"]); del r["_id"]
        reviews.append(r)
    s["reviews"] = reviews
    return s
