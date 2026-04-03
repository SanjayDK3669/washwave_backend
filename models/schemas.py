from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class UserRole(str, Enum):
    customer = "customer"
    laundry_owner = "laundry_owner"

class ServiceType(str, Enum):
    washing = "washing"
    dry_cleaning = "dry_cleaning"
    laundry = "laundry"
    ironing = "ironing"

class OrderStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    picked_up = "picked_up"
    in_progress = "in_progress"
    delivered = "delivered"
    cancelled = "cancelled"

# ── Geo ──────────────────────────────────────────────
class GeoLocation(BaseModel):
    type: str = "Point"
    coordinates: List[float]   # [lng, lat]

# ── Auth ─────────────────────────────────────────────
class CustomerRegister(BaseModel):
    name: str
    phone: str
    password: str
    address: Optional[str] = ""
    pincode: Optional[str] = ""
    location: Optional[GeoLocation] = None

class ShopRegister(BaseModel):
    shop_name: str
    owner_name: str
    phone: str
    password: str
    address: str
    pincode: str
    location: Optional[GeoLocation] = None
    services: List[ServiceType]
    description: Optional[str] = ""

class LoginRequest(BaseModel):
    phone: str
    password: str
    role: UserRole

# ── Shop update ───────────────────────────────────────
class ShopUpdate(BaseModel):
    shop_name: Optional[str] = None
    owner_name: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    description: Optional[str] = None
    services: Optional[List[ServiceType]] = None
    phone: Optional[str] = None
    location: Optional[GeoLocation] = None

# ── Order ─────────────────────────────────────────────
class OrderCreate(BaseModel):
    clothes_count: int
    services: List[ServiceType]
    notes: Optional[str] = ""
    customer_location: GeoLocation
    customer_address: str
    target_shop_id: Optional[str] = None

# ── Rating ────────────────────────────────────────────
class RatingCreate(BaseModel):
    shop_id: str
    order_id: str
    rating: int = Field(ge=1, le=5)
    review: Optional[str] = ""
