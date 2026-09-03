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

# Enable CORS for local testing
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

@app.on_event("startup")
async def startup_event():
    db.init_db()

# --- API ENDPOINTS ---
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

@app.get("/api/products")
async def get_products():
    products = db.search_products_db(query="")
    return products

# --- STATIC & FRONTEND FILE SERVING ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "frontend"))

# Mount frontend directory for static assets (style.css, images, etc.)
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)