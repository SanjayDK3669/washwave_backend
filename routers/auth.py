from fastapi import APIRouter, HTTPException, Depends
from database import users_col, shops_col
from models.schemas import CustomerRegister, ShopRegister, LoginRequest
from utils.jwt_handler import create_token, get_current_user
from bson import ObjectId
from datetime import datetime
import bcrypt

router = APIRouter()

# ── helpers ──────────────────────────────────────────
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    doc.pop("password", None)          # never send password to frontend
    return doc

# ── Customer register ─────────────────────────────────
@router.post("/register/customer")
async def register_customer(data: CustomerRegister):
    if await users_col.find_one({"phone": data.phone, "role": "customer"}):
        raise HTTPException(status_code=400, detail="Phone number already registered")

    doc = {
        "role": "customer",
        "name": data.name.strip(),
        "phone": data.phone.strip(),
        "password": hash_password(data.password),
        "address": data.address or "",
        "pincode": data.pincode or "",
        "location": data.location.dict() if data.location else None,
        "created_at": datetime.utcnow(),
    }
    result = await users_col.insert_one(doc)
    user = await users_col.find_one({"_id": result.inserted_id})
    token = create_token(str(result.inserted_id), "customer")
    return {"token": token, "user": serialize(user)}

# ── Shop owner register ───────────────────────────────
@router.post("/register/shop")
async def register_shop(data: ShopRegister):
    if await users_col.find_one({"phone": data.phone, "role": "laundry_owner"}):
        raise HTTPException(status_code=400, detail="Phone number already registered")

    # Create user account
    user_doc = {
        "role": "laundry_owner",
        "name": data.owner_name.strip(),
        "phone": data.phone.strip(),
        "password": hash_password(data.password),
        "created_at": datetime.utcnow(),
    }
    user_result = await users_col.insert_one(user_doc)
    owner_id = str(user_result.inserted_id)

    # Create shop profile
    shop_doc = {
        "name": data.shop_name.strip(),
        "owner_name": data.owner_name.strip(),
        "owner_id": owner_id,
        "phone": data.phone.strip(),
        "address": data.address.strip(),
        "pincode": data.pincode.strip(),
        "description": data.description or "",
        "services": [s.value for s in data.services],
        "location": data.location.dict() if data.location else {
            "type": "Point", "coordinates": [0.0, 0.0]
        },
        "is_active": True,
        "avg_rating": 0.0,
        "total_ratings": 0,
        "created_at": datetime.utcnow(),
    }
    shop_result = await shops_col.insert_one(shop_doc)

    user = await users_col.find_one({"_id": user_result.inserted_id})
    shop = await shops_col.find_one({"_id": shop_result.inserted_id})
    token = create_token(owner_id, "laundry_owner")
    return {"token": token, "user": serialize(user), "shop": serialize(shop)}

# ── Login (both roles) ────────────────────────────────
@router.post("/login")
async def login(data: LoginRequest):
    user = await users_col.find_one({"phone": data.phone.strip(), "role": data.role.value})
    if not user:
        raise HTTPException(status_code=401, detail="Phone number not found")
    if not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect password")

    token = create_token(str(user["_id"]), user["role"])
    response = {"token": token, "user": serialize(user)}

    # Attach shop info for owners
    if user["role"] == "laundry_owner":
        shop = await shops_col.find_one({"owner_id": str(user["_id"])})
        if shop:
            response["shop"] = serialize(shop)

    return response

# ── Me ────────────────────────────────────────────────
@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    user = await users_col.find_one({"_id": ObjectId(current_user["user_id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize(user)
