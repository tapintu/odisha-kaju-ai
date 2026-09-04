import sqlite3, os
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "data.db")

@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()

def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS products(
            grade TEXT PRIMARY KEY,
            price REAL NOT NULL,
            stock REAL NOT NULL,
            moq REAL NOT NULL DEFAULT 200,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS customers(
            phone TEXT PRIMARY KEY,
            name TEXT,
            city TEXT,
            last_grade TEXT,
            qty REAL,
            lead_status TEXT DEFAULT 'Warm',
            score INTEGER DEFAULT 50,
            last_message TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS approvals(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            category TEXT NOT NULL,
            question TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            owner_answer TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        count = c.execute("SELECT COUNT(*) n FROM products").fetchone()["n"]
        if count == 0:
            seed = [
                ("LWP",680,950,200),("SJH",710,600,200),("K",730,720,200),
                ("KK",750,550,200),("SW",760,480,200),("W400",790,800,200),
                ("JH",800,1300,200),("W320",820,1200,200),("JJH",820,700,200),
                ("DOUBLE",850,420,200),("W240",850,900,200),("W210",890,500,200),
                ("W180",940,340,200),("W160",970,180,200)
            ]
            c.executemany("INSERT INTO products(grade,price,stock,moq) VALUES(?,?,?,?)", seed)

def get_product(grade):
    grade = (grade or "").upper().strip()
    with conn() as c:
        r = c.execute("SELECT * FROM products WHERE grade=? AND active=1", (grade,)).fetchone()
        return dict(r) if r else None

def list_products():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM products ORDER BY grade")]

def update_product(grade, price=None, stock=None, moq=None):
    fields, vals = [], []
    for k,v in [("price",price),("stock",stock),("moq",moq)]:
        if v is not None:
            fields.append(f"{k}=?"); vals.append(v)
    if not fields: return False
    vals.append(grade.upper())
    with conn() as c:
        c.execute(f"UPDATE products SET {', '.join(fields)} WHERE grade=?", vals)
    return True

def add_message(phone, role, content):
    with conn() as c:
        c.execute("INSERT INTO messages(phone,role,content) VALUES(?,?,?)",(phone,role,content))
        c.execute("""INSERT INTO customers(phone,last_message) VALUES(?,?)
                     ON CONFLICT(phone) DO UPDATE SET last_message=excluded.last_message,updated_at=CURRENT_TIMESTAMP""",
                  (phone, content))

def history(phone, limit=12):
    with conn() as c:
        rows = c.execute("""SELECT role,content FROM messages WHERE phone=?
                            ORDER BY id DESC LIMIT ?""",(phone,limit)).fetchall()
    return [dict(r) for r in reversed(rows)]

def create_approval(phone, category, question):
    with conn() as c:
        cur = c.execute("INSERT INTO approvals(phone,category,question) VALUES(?,?,?)",(phone,category,question))
        return cur.lastrowid

def approvals(status="pending"):
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM approvals WHERE status=? ORDER BY id DESC",(status,))]

def resolve_approval(i, answer):
    with conn() as c:
        c.execute("UPDATE approvals SET status='resolved', owner_answer=? WHERE id=?",(answer,i))

def set_customer_fields(phone, name=None, city=None, grade=None, qty=None, status=None, score=None):
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO customers(phone) VALUES(?)",(phone,))
        data = {"name":name,"city":city,"last_grade":grade,"qty":qty,"lead_status":status,"score":score}
        for k,v in data.items():
            if v is not None:
                c.execute(f"UPDATE customers SET {k}=?,updated_at=CURRENT_TIMESTAMP WHERE phone=?",(v,phone))

def customers():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM customers ORDER BY score DESC, updated_at DESC")]
