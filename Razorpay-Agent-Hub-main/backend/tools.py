import os
import uuid
import asyncio
from typing import List,Optional,Dict,Any
from dotenv import load_dotenv
from backend import db

load_dotenv()

RAZORPAY_KEY_ID=os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET=os.getenv("RAZORPAY_KEY_SECRET")

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    raise RuntimeError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be set in .env")

if not RAZORPAY_KEY_ID.startswith("rzp_"):
    raise RuntimeError("Invalid RAZORPAY_KEY_ID. Use a real Razorpay Test or Live Key ID.")

import razorpay

razorpay_client=razorpay.Client(auth=(RAZORPAY_KEY_ID,RAZORPAY_KEY_SECRET))

def create_food_razorpay_checkout(food_name:str,amount:float=None,location:str=None):
    """
    Creates a REAL Razorpay order for food.
    Food is not checked against the database.
    """
    try:
        if amount is None:
            amount=299
        amount=float(amount)
        if amount<=0:
            amount=299
        amount_paise=int(round(amount*100))
        receipt=f"food_{uuid.uuid4().hex[:16]}"
        order=razorpay_client.order.create({
            "amount":amount_paise,
            "currency":"INR",
            "receipt":receipt,
            "notes":{
                "food_name":food_name,
                "location":location or ""
            }
        })
        return {
            "success":True,
            "type":"food_checkout",
            "food_name":food_name,
            "amount":amount,
            "amount_paise":amount_paise,
            "currency":"INR",
            "razorpay_order_id":order["id"],
            "razorpay_key_id":RAZORPAY_KEY_ID,
            "merchant":"Razorpay",
            "message":f"Checkout created for {food_name}"
        }
    except Exception as e:
        print(f"Food Razorpay Error: {e}")
        return {
            "success":False,
            "type":"checkout_error",
            "message":"Unable to create Razorpay order.",
            "error":str(e)
        }

def search_merchant_products(query:str,merchant:Optional[str]=None,max_price:Optional[float]=None,location:Optional[str]=None)->List[Dict[str,Any]]:
    return db.search_products_db(
        query=query,
        merchant=merchant,
        max_price=max_price,
        location=location
    )

async def create_razorpay_checkout(item_ids:List[int],merchant:str)->Dict[str,Any]:
    """
    Creates a REAL Razorpay checkout order using database products.
    """
    try:
        items=[]
        conn=db.get_connection()
        cursor=conn.cursor()
        for iid in item_ids:
            cursor.execute("SELECT * FROM products WHERE id = ?",(iid,))
            row=cursor.fetchone()
            if row:
                items.append(dict(row))
        conn.close()
        if not items:
            return {
                "status":"failure",
                "error":"No valid items found for checkout."
            }
        total_inr=sum(float(item["price"]) for item in items)
        total_paise=int(round(total_inr*100))
        if total_inr>5000:
            db.create_order_record(
                item_ids=item_ids,
                total=total_inr,
                razorpay_order_id="BLOCKED",
                merchant=merchant,
                status="SAFETY_LIMIT_EXCEEDED"
            )
            return {
                "status":"rejected",
                "reason":"Order exceeds max safety limit of ₹5000",
                "total_inr":total_inr
            }
        order_payload={
            "amount":total_paise,
            "currency":"INR",
            "receipt":f"order_{uuid.uuid4().hex[:16]}",
            "notes":{
                "merchant":merchant
            }
        }
        razorpay_order=await asyncio.to_thread(
            razorpay_client.order.create,
            data=order_payload
        )
        razorpay_order_id=razorpay_order["id"]
        db.create_order_record(
            item_ids=item_ids,
            total=total_inr,
            razorpay_order_id=razorpay_order_id,
            merchant=merchant,
            status="PENDING"
        )
        return {
            "status":"created",
            "total_inr":total_inr,
            "total_paise":total_paise,
            "razorpay_order_id":razorpay_order_id,
            "key_id":RAZORPAY_KEY_ID,
            "razorpay_key_id":RAZORPAY_KEY_ID,
            "currency":"INR",
            "merchant":merchant,
            "item_summaries":[
                f"{item['name']} (₹{item['price']})"
                for item in items
            ],
            "image_urls":[
                item.get("image_url")
                for item in items
                if item.get("image_url")
            ]
        }
    except Exception as e:
        print(f"Checkout Tool Error: {e}")
        return {
            "status":"error",
            "message":"Unable to create Razorpay checkout.",
            "error":str(e)
        }

async def verify_and_fulfill_payment(
    razorpay_order_id:str,
    razorpay_payment_id:str,
    razorpay_signature:str
):
    """
    Verifies a REAL Razorpay payment signature.
    This function is intentionally synchronous because main.py
    calls it without await.
    """
    try:
        if not razorpay_order_id:
            return {
                "success":False,
                "verified":False,
                "status":"FAILED",
                "message":"Razorpay Order ID is missing."
            }
        if not razorpay_payment_id:
            return {
                "success":False,
                "verified":False,
                "status":"FAILED",
                "message":"Razorpay Payment ID is missing."
            }
        if not razorpay_signature:
            return {
                "success":False,
                "verified":False,
                "status":"FAILED",
                "message":"Razorpay signature is missing."
            }
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id":razorpay_order_id,
            "razorpay_payment_id":razorpay_payment_id,
            "razorpay_signature":razorpay_signature
        })
        return {
            "success":True,
            "verified":True,
            "status":"PAID",
            "message":"Payment verified successfully.",
            "razorpay_order_id":razorpay_order_id,
            "razorpay_payment_id":razorpay_payment_id
        }
    except Exception as e:
        print(f"Payment Verification Error: {e}")
        return {
            "success":False,
            "verified":False,
            "status":"FAILED",
            "message":"Payment verification failed.",
            "error":str(e)
        }