from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/dashboard-page")
def dashboard_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))

@app.get("/add-product-page")
def add_product_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "add-product.html"))

@app.get("/add-purchase-page")
def add_purchase_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "add-purchase.html"))

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
from typing import List
from typing import List
from datetime import date

class ExpenseItem(BaseModel):
    description: str
    amount: float

class DailyClosingCreate(BaseModel):
    date: date
    opening_cash: float
    closing_cash: float
    phonepe_amount: float
    paytm_amount: float
    expenses: List[ExpenseItem]

class PurchaseItem(BaseModel):
    product_id: int
    box_quantity: int
    purchase_rate_per_box: float
    total_amount: float

class PurchaseCreate(BaseModel):
    purchase_date: str
    supplier_id: int
    invoice_number: str
    total_bill_amount: float
    added_by: int
    items: List[PurchaseItem]

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


@app.get("/dashboard")
def dashboard(user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()

    # Total Purchase
    cursor.execute("SELECT COALESCE(SUM(total_bill_amount),0) FROM purchases")
    total_purchase = cursor.fetchone()[0]

    # Today's Purchase
    cursor.execute("""
        SELECT COALESCE(SUM(total_bill_amount),0)
        FROM purchases
        WHERE purchase_date = CURRENT_DATE
    """)
    today_purchase = cursor.fetchone()[0]

    # Monthly Purchase
    cursor.execute("""
        SELECT COALESCE(SUM(total_bill_amount),0)
        FROM purchases
        WHERE DATE_TRUNC('month', purchase_date) =
              DATE_TRUNC('month', CURRENT_DATE)
    """)
    monthly_purchase = cursor.fetchone()[0]

    # Top 5 Purchased Products
    cursor.execute("""
        SELECT p.product_name, SUM(pd.box_quantity) as total_boxes
        FROM purchase_details pd
        JOIN products p ON p.product_id = pd.product_id
        GROUP BY p.product_name
        ORDER BY total_boxes DESC
        LIMIT 5
    """)
    top_products = cursor.fetchall()

    conn.close()

    return {
        "total_purchase": total_purchase,
        "today_purchase": today_purchase,
        "monthly_purchase": monthly_purchase,
        "top_products": top_products
    }

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

@app.post("/add_purchase")
def add_purchase(purchase: PurchaseCreate, user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Insert into purchases table
        cursor.execute("""
            INSERT INTO purchases
            (purchase_date, supplier_id, invoice_number, total_bill_amount, added_by)
            VALUES (%s,%s,%s,%s,%s)
            RETURNING purchase_id
        """, (
            purchase.purchase_date,
            purchase.supplier_id,
            purchase.invoice_number,
            purchase.total_bill_amount,
            purchase.added_by
        ))

        purchase_id = cursor.fetchone()[0]

        # Insert purchase details
        for item in purchase.items:
            cursor.execute("""
                INSERT INTO purchase_details
                (purchase_id, product_id, box_quantity,
                 purchase_rate_per_box, total_amount)
                VALUES (%s,%s,%s,%s,%s)
            """, (
                purchase_id,
                item.product_id,
                item.box_quantity,
                item.purchase_rate_per_box,
                item.total_amount
            ))

        conn.commit()
        return {"message": "Purchase Added Successfully"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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
@app.post("/daily-closing")
def create_daily_closing(data: DailyClosingCreate, user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        total_expense = sum(item.amount for item in data.expenses)

        cash_sales = data.closing_cash - data.opening_cash + total_expense

        total_sales = cash_sales + data.phonepe_amount + data.paytm_amount

        cursor.execute("""
            INSERT INTO daily_closing
            (date, opening_cash, closing_cash, cash_sales,
             phonepe_amount, paytm_amount, total_sales)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            data.date,
            data.opening_cash,
            data.closing_cash,
            cash_sales,
            data.phonepe_amount,
            data.paytm_amount,
            total_sales
        ))

        for item in data.expenses:
            cursor.execute("""
                INSERT INTO daily_expenses
                (date, description, amount)
                VALUES (%s,%s,%s)
            """, (
                data.date,
                item.description,
                item.amount
            ))

        conn.commit()

        return {
            "message": "Daily Closing Saved",
            "cash_sales": cash_sales,
            "total_expense": total_expense,
            "total_sales": total_sales
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/daily-closing/month-phonepe")
def month_phonepe(user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT SUM(phonepe_amount)
        FROM daily_closing
        WHERE date_trunc('month', date) = date_trunc('month', CURRENT_DATE)
    """)

    result = cursor.fetchone()[0] or 0
    return {"phonepe_total": result}
@app.get("/daily-closing/month-paytm")
def month_paytm(user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT SUM(paytm_amount)
        FROM daily_closing
        WHERE date_trunc('month', date) = date_trunc('month', CURRENT_DATE)
    """)

    result = cursor.fetchone()[0] or 0
    return {"paytm_total": result}
@app.get("/daily-closing/chart-data")
def chart_data(user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT date, total_sales
        FROM daily_closing
        WHERE date >= CURRENT_DATE - INTERVAL '30 day'
        ORDER BY date ASC
    """)

    rows = cursor.fetchall()

    data = [
        {"date": str(row[0]), "total": float(row[1])}
        for row in rows
    ]

    return data
@app.get("/daily-closing/month-expense")
def month_expense(user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT SUM(amount)
        FROM daily_expenses
        WHERE date_trunc('month', date) = date_trunc('month', CURRENT_DATE)
    """)

    result = cursor.fetchone()[0] or 0
    return {"monthly_expense": result}