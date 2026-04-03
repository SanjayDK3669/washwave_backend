from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, orders, shops, ratings
from database import create_indexes   # ✅ IMPORT THIS
import uvicorn

app = FastAPI(title="WashWave Laundry API", version="1.0.0")

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ ROUTERS
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(shops.router, prefix="/api/shops", tags=["Shops"])
app.include_router(ratings.router, prefix="/api/ratings", tags=["Ratings"])


# ✅ STARTUP EVENT (VERY IMPORTANT 🔥)
@app.on_event("startup")
async def startup_event():
    print("🚀 Creating indexes...")
    await create_indexes()
    print("✅ Indexes created successfully")


# ✅ ROOT
@app.get("/")
def root():
    return {"message": "WashWave API is running"}


# ✅ RUN SERVER
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)