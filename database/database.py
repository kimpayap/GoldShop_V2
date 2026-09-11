from pathlib import Path
import sqlite3
import os
import shutil
import sys


# =========================================================
# ตำแหน่งฐานข้อมูล
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent


def _application_data_dir():
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "GoldShop"
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", Path.home())) / "GoldShop"
    return Path.home() / ".local" / "share" / "GoldShop"


def _database_path():
    override = os.environ.get("GOLDSHOP_DB_PATH", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    # ตอนพัฒนาให้ใช้ฐานข้อมูลในโครงการเหมือนเดิม ส่วนโปรแกรมที่ติดตั้งแล้ว
    # ใช้พื้นที่ข้อมูลผู้ใช้ซึ่งเขียนได้และไม่ถูกลบเมื่ออัปเดตตัวโปรแกรม
    if not getattr(sys, "frozen", False):
        return BASE_DIR / "database" / "gold_shop.db"
    data_dir = _application_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / "gold_shop.db"
    if not target.exists():
        bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        seed = bundle_root / "database" / "gold_shop.db"
        if seed.exists(): shutil.copy2(seed, target)
    return target


DB_PATH = _database_path()


# =========================================================
# เชื่อมต่อ SQLite
# =========================================================

def get_connection():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


# =========================================================
# Migration: เพิ่ม column ที่ยังไม่มี
# =========================================================

def add_column_if_missing(
    conn,
    table_name,
    column_name,
    column_definition
):

    columns = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    existing_columns = {
        row["name"]
        for row in columns
    }

    if column_name not in existing_columns:

        conn.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name}
            {column_definition}
            """
        )

        print(
            f"เพิ่ม column: "
            f"{table_name}.{column_name}"
        )


# =========================================================
# Database
# =========================================================

def init_db():

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with get_connection() as conn:

        # =================================================
        # USERS
        # =================================================

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                username TEXT NOT NULL UNIQUE,

                password TEXT NOT NULL,

                full_name TEXT NOT NULL,

                role TEXT NOT NULL
                    DEFAULT 'staff',

                active INTEGER NOT NULL
                    DEFAULT 1,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # =================================================
        # CUSTOMERS
        # =================================================

        conn.execute("""
            CREATE TABLE IF NOT EXISTS customers (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                customer_code TEXT NOT NULL UNIQUE,

                first_name TEXT NOT NULL,

                last_name TEXT NOT NULL,

                citizen_id TEXT,

                phone TEXT,

                address TEXT,

                note TEXT,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # =================================================
        # CUSTOMER CARD DATA
        # =================================================
        # เพิ่มข้อมูลที่อ่านจาก Smart Card
        # =================================================

        add_column_if_missing(
            conn,
            "customers",
            "thai_name",
            "TEXT"
        )

        add_column_if_missing(
            conn,
            "customers",
            "english_name",
            "TEXT"
        )

        add_column_if_missing(
            conn,
            "customers",
            "birth_date",
            "TEXT"
        )

        add_column_if_missing(
            conn,
            "customers",
            "gender",
            "TEXT"
        )

        add_column_if_missing(
            conn,
            "customers",
            "card_issuer",
            "TEXT"
        )

        add_column_if_missing(
            conn,
            "customers",
            "card_issue_date",
            "TEXT"
        )

        add_column_if_missing(
            conn,
            "customers",
            "card_expire_date",
            "TEXT"
        )

        add_column_if_missing(
            conn,
            "customers",
            "photo_path",
            "TEXT"
        )

        # =================================================
        # CUSTOMER INDEX
        # =================================================

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_customers_name
            ON customers(first_name, last_name)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_customers_phone
            ON customers(phone)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_customers_citizen_id
            ON customers(citizen_id)
        """)

        # =================================================
        # GOLD PRICES
        # =================================================

        conn.execute("""
            CREATE TABLE IF NOT EXISTS gold_prices (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                price_date TEXT NOT NULL,

                price_time TEXT NOT NULL,

                announcement_no INTEGER,

                gold_bar_buy REAL,

                gold_bar_sell REAL,

                gold_jewelry_tax REAL,

                gold_jewelry_sell REAL,

                gold_spot REAL,

                thai_baht REAL,

                price_change REAL,

                source TEXT NOT NULL
                    DEFAULT 'goldtraders.or.th',

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_gold_prices_datetime
            ON gold_prices(price_date, price_time)
        """)

        # =================================================
        # DEFAULT ADMIN
        # =================================================

        conn.execute("""
            INSERT OR IGNORE INTO users
            (
                username,
                password,
                full_name,
                role
            )
            VALUES (?, ?, ?, ?)
        """, (
            "admin",
            "admin123",
            "ผู้ดูแลระบบ",
            "admin"
        ))

        conn.commit()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    init_db()

    print()
    print("=" * 60)
    print("สร้าง / อัปเดตฐานข้อมูลสำเร็จ")
    print("=" * 60)
    print(
        f"Database: {DB_PATH}"
    )
    print("=" * 60)
