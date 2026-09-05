import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Any
import uvicorn

load_dotenv()

from backend import db, agent, tools

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    history: List[Any]

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class CheckoutRequest(BaseModel):
    item_id: int
    merchant: str = "PVR INOX"

@app.on_event("startup")
async def startup_event():
    db.init_db()

@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    result = await agent.run_agent(payload.message, payload.history)
    return result

@app.post("/api/verify-payment")
async def verify_payment(request: VerifyPaymentRequest):
    result = await tools.verify_and_fulfill_payment(
        razorpay_order_id=request.razorpay_order_id,
        razorpay_payment_id=request.razorpay_payment_id,
        razorpay_signature=request.razorpay_signature
    )
    return result

@app.post("/api/checkout")
async def checkout(request: CheckoutRequest):
    try:
        result = await tools.create_razorpay_checkout(
            item_ids=[request.item_id],
            merchant=request.merchant
        )
        return result
    except Exception as e:
        print("Checkout error:", repr(e))
        return {
            "status": "error",
            "message": "Unable to create Razorpay checkout."
        }

@app.get("/api/products")
async def get_products():
    products = db.search_products_db(query="")
    return products

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "frontend"))

app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000))
    )
