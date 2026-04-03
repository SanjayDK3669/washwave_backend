from fastapi import APIRouter, HTTPException, Depends
from database import orders_col, shops_col, users_col
from models.schemas import OrderCreate, OrderStatus
from utils.jwt_handler import get_current_user, require_customer, require_owner
from bson import ObjectId
from datetime import datetime

router = APIRouter()

def serialize(doc):
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc

@router.post("/")
async def create_order(data: OrderCreate, user=Depends(require_customer)):
    # Find nearby shops (within 5km)
    nearby_shops = []

    if data.target_shop_id:
        shop = await shops_col.find_one({"_id": ObjectId(data.target_shop_id)})
        if shop:
            nearby_shops = [str(shop["_id"])]
    else:
        cursor = shops_col.find({
            "location": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": data.customer_location.coordinates
                    },
                    "$maxDistance": 5000
                }
            },
            "is_active": True
        }).limit(5)
        async for shop in cursor:
            nearby_shops.append(str(shop["_id"]))

    if not nearby_shops:
        raise HTTPException(status_code=404, detail="No laundry shops found nearby")

    order = {
        "customer_id": user["user_id"],
        "clothes_count": data.clothes_count,
        "services": [s.value for s in data.services],
        "notes": data.notes,
        "customer_location": data.customer_location.dict(),
        "customer_address": data.customer_address,
        "status": OrderStatus.pending.value,
        "notified_shops": nearby_shops,
        "accepted_by_shop": None,
        "target_shop_id": data.target_shop_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    result = await orders_col.insert_one(order)
    created = await orders_col.find_one({"_id": result.inserted_id})
    return serialize(created)

@router.get("/my-orders")
async def customer_orders(user=Depends(require_customer)):
    cursor = orders_col.find({"customer_id": user["user_id"]}).sort("created_at", -1)
    orders = []
    async for o in cursor:
        o = serialize(o)
        # Attach shop info if accepted
        if o.get("accepted_by_shop"):
            shop = await shops_col.find_one({"_id": ObjectId(o["accepted_by_shop"])})
            if shop:
                o["shop"] = {"name": shop["name"], "phone": shop["phone"], "id": str(shop["_id"])}
        orders.append(o)
    return orders

@router.get("/shop-requests")
async def shop_incoming_orders(user=Depends(require_owner)):
    shop = await shops_col.find_one({"owner_id": user["user_id"]})
    if not shop:
        raise HTTPException(status_code=404, detail="No shop found")
    shop_id = str(shop["_id"])

    cursor = orders_col.find({
        "notified_shops": shop_id,
        "status": OrderStatus.pending.value
    }).sort("created_at", -1)

    orders = []
    async for o in cursor:
        o = serialize(o)
        # Get customer basic info
        cust = await users_col.find_one({"_id": ObjectId(o["customer_id"])})
        if cust:
            o["customer"] = {"name": cust.get("name", ""), "phone": cust.get("phone", "")}
        orders.append(o)
    return orders

@router.get("/shop-accepted")
async def shop_accepted_orders(user=Depends(require_owner)):
    shop = await shops_col.find_one({"owner_id": user["user_id"]})
    if not shop:
        raise HTTPException(status_code=404, detail="No shop found")
    shop_id = str(shop["_id"])

    cursor = orders_col.find({
        "accepted_by_shop": shop_id
    }).sort("created_at", -1)

    orders = []
    async for o in cursor:
        o = serialize(o)
        cust = await users_col.find_one({"_id": ObjectId(o["customer_id"])})
        if cust:
            o["customer"] = {"name": cust.get("name", ""), "phone": cust.get("phone", "")}
        orders.append(o)
    return orders

@router.post("/{order_id}/accept")
async def accept_order(order_id: str, user=Depends(require_owner)):
    shop = await shops_col.find_one({"owner_id": user["user_id"]})
    if not shop:
        raise HTTPException(status_code=404, detail="No shop found")

    order = await orders_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order["status"] != OrderStatus.pending.value:
        raise HTTPException(status_code=400, detail="Order already accepted by another shop")

    shop_id = str(shop["_id"])
    if shop_id not in order.get("notified_shops", []):
        raise HTTPException(status_code=403, detail="This order was not sent to your shop")

    await orders_col.update_one(
        {"_id": ObjectId(order_id), "status": OrderStatus.pending.value},
        {"$set": {
            "status": OrderStatus.accepted.value,
            "accepted_by_shop": shop_id,
            "updated_at": datetime.utcnow()
        }}
    )
    updated = await orders_col.find_one({"_id": ObjectId(order_id)})
    return serialize(updated)

@router.put("/{order_id}/status")
async def update_order_status(order_id: str, status: str, user=Depends(require_owner)):
    valid = [s.value for s in OrderStatus]
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from: {valid}")

    shop = await shops_col.find_one({"owner_id": user["user_id"]})
    shop_id = str(shop["_id"])

    await orders_col.update_one(
        {"_id": ObjectId(order_id), "accepted_by_shop": shop_id},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}}
    )
    updated = await orders_col.find_one({"_id": ObjectId(order_id)})
    return serialize(updated)

@router.get("/{order_id}")
async def get_order(order_id: str, user=Depends(get_current_user)):
    order = await orders_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return serialize(order)
