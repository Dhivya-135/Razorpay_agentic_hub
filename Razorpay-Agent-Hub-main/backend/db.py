import sqlite3
import random
import argparse
import json
from typing import List, Optional, Dict, Any

def get_connection():
    conn = sqlite3.connect("catalog.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Products Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant TEXT NOT NULL,
            name TEXT NOT NULL,
            sku TEXT UNIQUE NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            language TEXT DEFAULT 'All',
            region TEXT DEFAULT 'All',
            image_url TEXT
        )
    ''')

    # Audit Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            intent TEXT,
            merchant TEXT,
            status TEXT,
            details TEXT
        )
    ''')

    # Orders Table (Required by Razorpay checkout tools)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_ids TEXT NOT NULL,
            total REAL NOT NULL,
            razorpay_order_id TEXT NOT NULL,
            merchant TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    
    # Populate seed data safely
    seed_data()

def seed_data():
    conn = get_connection()
    cursor = conn.cursor()

    initial_products = [
        # Tamil Movies running in PVR INOX Tamil Nadu
        ("PVR INOX", "Hi UA 13+(Tamil Feel-Good Drama)", "PVR-MOV-HI01", 250.0, "Entertainment", "Tamil", "Tamil Nadu", "https://originserver-static1-uat.pvrcinemas.com/pvrcms/movie_v/38399_z1FsFR5q.jpg"),
        ("PVR INOX", "Toxic A(Tamil Action Drama)", "PVR-MOV-AMR02", 300.0, "Entertainment", "Tamil,Kannada,Hindi", "Tamil Nadu", "https://originserver-static1-uat.pvrcinemas.com/pvrcms/movie_v/34785_oz7k4ZJn.jpg"),
        ("PVR INOX", "Spiderman Brand New Day UA 13+(Tamil Sci-Fi/Action)", "PVR-MOV-GOT03", 350.0, "Entertainment", "English,Tamil", "Tamil Nadu", "https://originserver-static1-uat.pvrcinemas.com/pvrcms/movie_v/35294_BTXAkWEz.jpg"),
        
        # General / Default PVR INOX fallback entries
        ("PVR INOX", "Recliner Ticket - Standard Blockbuster", "PVR-TIC-001", 450.0, "Entertainment", "All", "All", "https://images.unsplash.com/photo-1595769816263-9b910be24d5f?w=500"),
        ("PVR INOX", "Large Cheese Popcorn & Pepsi Combo", "PVR-COM-002", 670.0, "Entertainment", "All", "All", "https://images.unsplash.com/photo-1585647347483-22b66260dfff?w=500"),

        ("Zomato","Margherita Pizza","ZOM-PIZ-001",349.0,"Food","All","All","https://images.unsplash.com/photo-1574071318508-1cdbcd80ad59?w=500"),

    (
        "Zomato",
        "Ambur Star - Chicken Biryani",
        "ZOM-BIR-002",
        429.0,
        "Food",
        "All",
        "All",
        "https://images.unsplash.com/photo-1563379091339-03b21bc4a4f8?w=500"
    ),

    (
        "Zomato",
        "Chicken 65",
        "ZOM-CHK-003",
        299.0,
        "Food",
        "All",
        "All",
        "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=500"
    ),

    (
        "Zomato",
        "Dindigul Chicken Biryani",
        "ZOM-BIR-004",
        399.0,
        "Food",
        "All",
        "All",
        "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=500"
    ),

    (
        "Zomato",
        "Paneer Butter Masala",
        "ZOM-NOR-005",
        289.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=500"
    ),

    (
        "Zomato",
        "Butter Naan - 2 Pieces",
        "ZOM-NAN-006",
        129.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1601050690117-94f5f6fa8bd7?w=500"
    ),

    (
        "Zomato",
        "Chicken Shawarma",
        "ZOM-SHW-007",
        249.0,
        "Food",
        "Non-Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1529006557810-274b9b2fc783?w=500"
    ),

    (
        "Zomato",
        "Veg Fried Rice",
        "ZOM-CHI-008",
        219.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=500"
    ),

    (
        "Zomato",
        "Chicken Fried Rice",
        "ZOM-CHI-009",
        269.0,
        "Food",
        "Non-Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=500"
    ),

    (
        "Zomato",
        "Masala Dosa",
        "ZOM-SOU-010",
        149.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1668236543090-82eba5ee5976?w=500"
    ),

    (
        "Zomato",
        "Idli Vada Combo",
        "ZOM-SOU-011",
        119.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=500"
    ),

    (
        "Zomato",
        "South Indian Meals",
        "ZOM-SOU-012",
        199.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1626776876729-bab4369a5a5a?w=500"
    ),

    (
        "Zomato",
        "Chettinad Chicken",
        "ZOM-CHK-013",
        349.0,
        "Food",
        "Non-Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?w=500"
    ),

    (
        "Zomato",
        "Chicken Kothu Parotta",
        "ZOM-SOU-014",
        249.0,
        "Food",
        "Non-Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=500"
    ),

    (
        "Zomato",
        "Veg Burger",
        "ZOM-BRG-015",
        199.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1520072959219-c595dc870360?w=500"
    ),

    (
        "Zomato",
        "Chicken Burger",
        "ZOM-BRG-016",
        279.0,
        "Food",
        "Non-Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=500"
    ),

    (
        "Zomato",
        "Chocolate Brownie",
        "ZOM-DES-017",
        149.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1564355808539-22fda35bed7e?w=500"
    ),

    (
        "Zomato",
        "Chocolate Lava Cake",
        "ZOM-DES-018",
        199.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=500"
    ),

    (
        "Zomato",
        "Mango Lassi",
        "ZOM-DRK-019",
        129.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=500"
    ),

    (
        "Zomato",
        "Fresh Lime Soda",
        "ZOM-DRK-020",
        99.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=500"
    ),
    
    (
        "Swiggy",
        "Chicken Biryani",
        "SWI-BIR-001",
        379.0,
        "Food",
        "Non-Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1563379091339-03b21bc4a4f8?w=500"
    ),

    (
        "Swiggy",
        "Mutton Biryani",
        "SWI-BIR-002",
        499.0,
        "Food",
        "Non-Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1563379091339-03b21bc4a4f8?w=500"
    ),

    (
        "Swiggy",
        "Paneer Tikka",
        "SWI-VEG-003",
        299.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1567188040759-fb8a883dc6d8?w=500"
    ),

    (
        "Swiggy",
        "Veg Pizza",
        "SWI-PIZ-004",
        329.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1574071318508-1cdbcd80ad59?w=500"
    ),

    (
        "Swiggy",
        "Chicken Pizza",
        "SWI-PIZ-005",
        449.0,
        "Food",
        "Non-Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1574071318508-1cdbcd80ad59?w=500"
    ),

    (
        "Swiggy",
        "Chole Bhature",
        "SWI-NOR-006",
        229.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1626132647523-66f5bf380027?w=500"
    ),

    (
        "Swiggy",
        "Chicken Tikka",
        "SWI-CHK-007",
        349.0,
        "Food",
        "Non-Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?w=500"
    ),

    (
        "Swiggy",
        "Veg Noodles",
        "SWI-CHI-008",
        199.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1585032226651-759b368d7246?w=500"
    ),

    (
        "Swiggy",
        "Chicken Noodles",
        "SWI-CHI-009",
        249.0,
        "Food",
        "Non-Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1585032226651-759b368d7246?w=500"
    ),

    (
        "Swiggy",
        "Ghee Roast Dosa",
        "SWI-SOU-010",
        179.0,
        "Food",
        "Vegetarian",
        "All",
        "https://images.unsplash.com/photo-1668236543090-82eba5ee5976?w=500"
    ),


    # =========================
    # SWIGGY INSTAMART - GROCERIES
    # =========================

    (
        "Swiggy Instamart",
        "Organic Toned Milk 1L",
        "SWI-MLK-001",
        68.0,
        "Groceries",
        "All",
        "All",
        "https://images.unsplash.com/photo-1563636619-e910ef2a844b?w=500"
    ),

    (
        "Swiggy Instamart",
        "Farm Fresh Eggs - 12 Pack",
        "SWI-EGG-002",
        99.0,
        "Groceries",
        "All",
        "All",
        "https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=500"
    ),

    (
        "Swiggy Instamart",
        "Banana - 1 Dozen",
        "SWI-FRT-003",
        79.0,
        "Groceries",
        "All",
        "All",
        "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=500"
    ),

    (
        "Swiggy Instamart",
        "Fresh Apples 1kg",
        "SWI-FRT-004",
        149.0,
        "Groceries",
        "All",
        "All",
        "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=500"
    ),

    (
        "Swiggy Instamart",
        "Basmati Rice 5kg",
        "SWI-RIC-005",
        499.0,
        "Groceries",
        "All",
        "All",
        "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=500"
    ),

    (
        "Swiggy Instamart",
        "Potato 1kg",
        "SWI-VEG-006",
        49.0,
        "Groceries",
        "All",
        "All",
        "https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=500"
    ),

    (
        "Swiggy Instamart",
        "Tomato 1kg",
        "SWI-VEG-007",
        59.0,
        "Groceries",
        "All",
        "All",
        "https://images.unsplash.com/photo-1546094096-0df4bcaaa337?w=500"
    ),

    (
        "Swiggy Instamart",
        "Brown Bread",
        "SWI-BRD-008",
        55.0,
        "Groceries",
        "All",
        "All",
        "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=500"
    ),
]

    cursor.executemany(
        """INSERT OR IGNORE INTO products 
           (merchant, name, sku, price, category, language, region, image_url) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        initial_products
    )
    conn.commit()
    conn.close()

def search_products_db(query, merchant=None, max_price=None, region="Tamil Nadu", location=None):
    # Use location if passed from the agent, otherwise default to region
    target_region = location if location else region

    conn = get_connection()
    cursor = conn.cursor()

    search_term = f"%{query}%"

    sql = """
        SELECT * FROM products 
        WHERE (name LIKE ? OR category LIKE ? OR language LIKE ?)
    """
    params = [search_term, search_term, search_term]

    if merchant:
        sql += " AND merchant = ?"
        params.append(merchant)
    if max_price:
        sql += " AND price <= ?"
        params.append(float(max_price))

    cursor.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]

    if not results and merchant == "PVR INOX":
        cursor.execute("""
            SELECT * FROM products 
            WHERE merchant = 'PVR INOX' AND (region = ? OR region = 'All')
        """, (target_region,))
        results = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return results

def create_order_record(item_ids: List[int], total: float, razorpay_order_id: str, merchant: str, status: str = "PENDING"):
    """Inserts an order payload directly into the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO orders (item_ids, total, razorpay_order_id, merchant, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (json.dumps(item_ids), total, razorpay_order_id, merchant, status)
    )
    conn.commit()
    conn.close()

def update_order_status(razorpay_order_id: str, status: str):
    """Updates order fulfillment status after verification."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE orders 
        SET status = ? 
        WHERE razorpay_order_id = ?
        """,
        (status, razorpay_order_id)
    )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite Database Manager for Multi-Merchant Payment Hub")
    parser.add_argument("--seed-large", action="store_true", help="Seed a large synthetic dataset")
    parser.add_argument("--count", type=int, default=1000, help="Number of products to seed")
    args = parser.parse_args()

    init_db()
    print("✅ Database initialized with orders table and Tamil Nadu PVR INOX catalog!")