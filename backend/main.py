from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List
from jose import JWTError, jwt
from datetime import datetime, timedelta
import psycopg2
from fastapi.middleware.cors import CORSMiddleware

# ================= CONFIG =================

SECRET_KEY = "ENJOYPOINTSECRET123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # development ke liye sab allow
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ================= DB CONNECTION =================

def get_connection():
    return psycopg2.connect(
        host="aws-1-ap-southeast-2.pooler.supabase.com",
        database="postgres",
        user="postgres.qlvuzviwincrzhlvxuid",
        password="enjoypoint@123",
        port="5432",
        sslmode="require"
    )

# ================= JWT FUNCTIONS =================

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid Token")

def owner_required(user: dict = Depends(get_current_user)):
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access required")
    return user

# ================= LOGIN =================

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    print("LOGIN API CALLED")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT user_id, password, role FROM users WHERE username=%s",
        (form_data.username,)
    )

    user = cursor.fetchone()
    print("DB RESULT:", user)

    if not user:
        raise HTTPException(status_code=400, detail="Invalid username")

    user_id, db_password, role = user
    print("PASSWORD FROM DB:", db_password)

    if form_data.password != db_password:
        raise HTTPException(status_code=400, detail="Invalid password")

    token = create_access_token(
        {"sub": form_data.username, "role": role, "user_id": user_id}
    )

    return {"access_token": token, "token_type": "bearer"}

# ================= PRODUCT MODELS =================

class Product(BaseModel):
    brand: str
    product_name: str
    category: str
    pack_size: str
    pieces_per_box: int
    dealer_rate_with_gst: float
    mrp_per_piece: float

# ================= PRODUCT APIs =================

@app.get("/products")
def get_products(user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    return cursor.fetchall()

@app.post("/products")
def add_product(product: Product, user: dict = Depends(owner_required)):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO products
            (brand, product_name, category, pack_size, pieces_per_box,
             dealer_rate_with_gst, mrp_per_piece)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            product.brand, product.product_name, product.category,
            product.pack_size, product.pieces_per_box,
            product.dealer_rate_with_gst, product.mrp_per_piece
        ))

        conn.commit()
        return {"message": "Product added"}

    except Exception as e:
        print("PRODUCT ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/products/{id}")
def update_product(id: int, product: Product, user: dict = Depends(owner_required)):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE products SET
        brand=%s, product_name=%s, category=%s,
        pack_size=%s, pieces_per_box=%s,
        dealer_rate_with_gst=%s, mrp_per_piece=%s
        WHERE product_id=%s
    """, (
        product.brand, product.product_name, product.category,
        product.pack_size, product.pieces_per_box,
        product.dealer_rate_with_gst, product.mrp_per_piece, id
    ))

    conn.commit()
    return {"message": "Product updated"}

@app.delete("/products/{id}")
def delete_product(id: int, user: dict = Depends(owner_required)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE product_id=%s", (id,))
    conn.commit()
    return {"message": "Product deleted"}

# ================= SUPPLIER APIs =================

@app.get("/suppliers")
def get_suppliers(user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM suppliers")
    return cursor.fetchall()

@app.post("/suppliers")
def add_supplier(name: str, user: dict = Depends(owner_required)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO suppliers (supplier_name) VALUES (%s)", (name,))
    conn.commit()
    return {"message": "Supplier added"}

# ================= PURCHASE APIs =================

@app.get("/purchases")
def get_purchases(user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM purchases")
    return cursor.fetchall()

@app.get("/purchases/{invoice}")
def get_purchase_by_invoice(invoice: str, user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM purchases WHERE invoice_number=%s", (invoice,))
    return cursor.fetchall()

@app.delete("/purchases/{id}")
def delete_purchase(id: int, user: dict = Depends(owner_required)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM purchases WHERE purchase_id=%s", (id,))
    conn.commit()
    return {"message": "Purchase deleted"}

# ================= USER APIs =================

class NewUser(BaseModel):
    name: str
    username: str
    password: str
    role: str

@app.post("/users")
def add_user(new_user: NewUser, user: dict = Depends(owner_required)):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (name, username, password, role)
        VALUES (%s,%s,%s,%s)
    """, (
        new_user.name,
        new_user.username,
        new_user.password,
        new_user.role
    ))

    conn.commit()
    return {"message": "User added"}

@app.get("/users")
def get_users(user: dict = Depends(owner_required)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, name, username, role FROM users")
    return cursor.fetchall()