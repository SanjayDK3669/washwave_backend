from fastapi import APIRouter, HTTPException, Depends
from database import ratings_col, shops_col, orders_col
from models.schemas import RatingCreate
from utils.jwt_handler import require_customer
from bson import ObjectId
from datetime import datetime

router = APIRouter()

@router.post("/")
async def add_rating(data: RatingCreate, user=Depends(require_customer)):
    # Verify order belongs to this customer and is delivered
    order = await orders_col.find_one({
        "_id": ObjectId(data.order_id),
        "customer_id": user["user_id"]
    })
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] != "delivered":
        raise HTTPException(status_code=400, detail="Can only rate after delivery")

    # Check not already rated
    existing = await ratings_col.find_one({"order_id": data.order_id, "customer_id": user["user_id"]})
    if existing:
        raise HTTPException(status_code=400, detail="Already rated this order")

    rating = {
        "shop_id": data.shop_id,
        "order_id": data.order_id,
        "customer_id": user["user_id"],
        "rating": data.rating,
        "review": data.review,
        "created_at": datetime.utcnow()
    }
    await ratings_col.insert_one(rating)

    # Update shop avg rating
    cursor = ratings_col.find({"shop_id": data.shop_id})
    ratings_list = []
    async for r in cursor:
        ratings_list.append(r["rating"])

    avg = sum(ratings_list) / len(ratings_list) if ratings_list else 0
    await shops_col.update_one(
        {"_id": ObjectId(data.shop_id)},
        {"$set": {"avg_rating": round(avg, 1), "total_ratings": len(ratings_list)}}
    )

    return {"message": "Rating submitted", "avg_rating": round(avg, 1)}

@router.get("/shop/{shop_id}")
async def get_shop_ratings(shop_id: str):
    cursor = ratings_col.find({"shop_id": shop_id}).sort("created_at", -1)
    ratings = []
    async for r in cursor:
        r["id"] = str(r["_id"]); del r["_id"]
        ratings.append(r)
    return ratings
