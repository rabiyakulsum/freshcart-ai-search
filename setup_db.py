import csv, os
import psycopg2
from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables

# ==========================================
# setup_db.py
# 1. Enable the pgvector extension.
# 2. Create the `products` table used by app.py.
# 3. Load the 100 products (with precomputed 384-dim embeddings)
#    from products_precalculated.csv.
# Safe to re-run: existing rows (including ones added via the app) are kept.
# ==========================================

CSV_FILE = "products_precalculated.csv"

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    database=os.getenv("POSTGRES_DB", "postgres"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", "password"),
    port=int(os.getenv("POSTGRES_PORT", 5432))
)
cur = conn.cursor()

# 1. pgvector adds the `vector` column type and the <=> distance operator
cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

# 2. Columns match the INSERT in app.py (POST /products/add).
#    all-MiniLM-L6-v2 produces 384-dimensional embeddings.
cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id         INTEGER PRIMARY KEY,
        name               TEXT NOT NULL,
        category           TEXT,
        price              NUMERIC(10, 2),
        stock_quantity     INTEGER,
        rating             NUMERIC(2, 1),
        description        TEXT,
        description_vector VECTOR(384)
    )
""")

# 3. Load the CSV. description_vector is stored as "[0.1, 0.2, ...]",
#    which pgvector accepts directly as text.
with open(CSV_FILE, newline="", encoding="utf-8") as f:
    rows = [
        (int(r["product_id"]), r["name"], r["category"], float(r["price"]),
         int(r["stock_quantity"]), float(r["rating"]), r["description"],
         r["description_vector"])
        for r in csv.DictReader(f)
    ]

cur.executemany(
    "INSERT INTO products "
    "(product_id, name, category, price, stock_quantity, rating, description, description_vector) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector) "
    "ON CONFLICT (product_id) DO NOTHING",
    rows
)
conn.commit()

cur.execute("SELECT COUNT(*) FROM products")
print(f"✅ Loaded {len(rows)} rows from {CSV_FILE}. products table now has {cur.fetchone()[0]} rows.")

cur.close(); conn.close()
