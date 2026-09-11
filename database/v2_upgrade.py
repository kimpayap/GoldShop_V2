
from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "gold_shop.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_v2_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pawn_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                monthly_interest_rate REAL NOT NULL DEFAULT 2.00,
                loan_term_days INTEGER NOT NULL DEFAULT 120,
                weight_per_baht_gram REAL NOT NULL DEFAULT 15.244,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            INSERT OR IGNORE INTO pawn_settings
            (id, monthly_interest_rate, loan_term_days, weight_per_baht_gram)
            VALUES (1, 2.00, 120, 15.244)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS pawn_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_no TEXT NOT NULL UNIQUE,
                customer_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                gold_price_id INTEGER,
                loan_amount REAL NOT NULL,
                monthly_interest_rate REAL NOT NULL,
                opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                due_date TEXT NOT NULL,
                redeemed_at TEXT,
                redeemed_amount REAL,
                notes TEXT,
                created_by INTEGER,
                FOREIGN KEY(customer_id) REFERENCES customers(id),
                FOREIGN KEY(gold_price_id) REFERENCES gold_prices(id),
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS pawn_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pawn_ticket_id INTEGER NOT NULL,
                item_no INTEGER NOT NULL,
                item_type TEXT NOT NULL DEFAULT 'ทองรูปพรรณ',
                description TEXT NOT NULL,
                purity REAL NOT NULL DEFAULT 96.5,
                weight_grams REAL NOT NULL,
                gold_price_per_baht REAL,
                estimated_value REAL,
                loan_value REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(pawn_ticket_id) REFERENCES pawn_tickets(id) ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS pawn_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pawn_ticket_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL DEFAULT 0,
                transaction_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                note TEXT,
                created_by INTEGER,
                FOREIGN KEY(pawn_ticket_id) REFERENCES pawn_tickets(id) ON DELETE CASCADE,
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pawn_ticket_customer
            ON pawn_tickets(customer_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pawn_ticket_status
            ON pawn_tickets(status)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pawn_item_ticket
            ON pawn_items(pawn_ticket_id)
        """)

        conn.commit()

    print("=" * 60)
    print("GoldShop V2 database upgrade สำเร็จ")
    print(f"Database: {DB_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    init_v2_db()
