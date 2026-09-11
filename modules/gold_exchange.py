from database.database import get_connection
from modules.old_gold import ensure_old_gold_schema, get_old_gold_receipt
from modules.sales import ensure_sales_schema, get_gold_sale
from modules.document_numbers import next_document_no


def ensure_exchange_schema():
    ensure_old_gold_schema(); ensure_sales_schema()
    with get_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS gold_exchanges(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exchange_no TEXT NOT NULL UNIQUE,
            old_gold_receipt_id INTEGER NOT NULL UNIQUE,
            gold_sale_id INTEGER NOT NULL UNIQUE,
            trade_in_amount REAL NOT NULL,
            new_gold_amount REAL NOT NULL,
            difference_amount REAL NOT NULL,
            settlement_direction TEXT NOT NULL,
            settlement_method TEXT NOT NULL DEFAULT 'เงินสด',
            notes TEXT,
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(old_gold_receipt_id) REFERENCES old_gold_receipts(id),
            FOREIGN KEY(gold_sale_id) REFERENCES gold_sales(id),
            FOREIGN KEY(created_by) REFERENCES users(id))""")
        conn.commit()


def create_gold_exchange(old_gold_receipt_id, gold_sale_id, settlement_method="เงินสด", notes="", created_by=None):
    ensure_exchange_schema()
    old_receipt=get_old_gold_receipt(old_gold_receipt_id); sale=get_gold_sale(gold_sale_id)
    if not old_receipt or old_receipt["status"]!="completed":raise ValueError("ใบรับซื้อทองเก่าไม่พร้อมใช้งาน")
    if not sale or sale["status"]!="completed":raise ValueError("รายการขายทองใหม่ไม่พร้อมใช้งาน")
    old_amount=round(float(old_receipt["paid_amount"]),2);new_amount=round(float(sale["grand_total"]),2)
    difference=round(new_amount-old_amount,2)
    direction="customer_pays" if difference>0 else ("shop_refunds" if difference<0 else "even")
    with get_connection() as conn:
        if conn.execute("SELECT 1 FROM gold_exchanges WHERE old_gold_receipt_id=? OR gold_sale_id=?",(int(old_gold_receipt_id),int(gold_sale_id))).fetchone():
            raise ValueError("เอกสารนี้ถูกเชื่อมกับรายการแลกทองแล้ว")
        exchange_no=next_document_no(conn,"gold_exchange","EX")
        while conn.execute("SELECT 1 FROM gold_exchanges WHERE exchange_no=?",(exchange_no,)).fetchone():exchange_no=next_document_no(conn,"gold_exchange","EX")
        cur=conn.execute("""INSERT INTO gold_exchanges
            (exchange_no,old_gold_receipt_id,gold_sale_id,trade_in_amount,new_gold_amount,
             difference_amount,settlement_direction,settlement_method,notes,created_by)
             VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (exchange_no,int(old_gold_receipt_id),int(gold_sale_id),old_amount,new_amount,difference,
             direction,str(settlement_method or "เงินสด"),str(notes or ""),created_by))
        conn.commit()
    return {"exchange_id":cur.lastrowid,"exchange_no":exchange_no,"trade_in_amount":old_amount,
            "new_gold_amount":new_amount,"difference_amount":difference,"settlement_direction":direction}


def get_or_create_gold_exchange(old_gold_receipt_id, gold_sale_id, settlement_method="เงินสด", notes="", created_by=None):
    """Finish an exchange safely when the UI is resumed or a completion callback runs twice."""
    ensure_exchange_schema()
    with get_connection() as conn:
        row=conn.execute("""SELECT id,exchange_no,old_gold_receipt_id,gold_sale_id,trade_in_amount,new_gold_amount,difference_amount,
            settlement_direction FROM gold_exchanges
            WHERE old_gold_receipt_id=? OR gold_sale_id=? LIMIT 1""",
            (int(old_gold_receipt_id),int(gold_sale_id))).fetchone()
    if row:
        result=dict(row);result["exchange_id"]=result.pop("id")
        if result["old_gold_receipt_id"]!=int(old_gold_receipt_id) or result["gold_sale_id"]!=int(gold_sale_id):
            raise ValueError("เอกสารรายการหนึ่งถูกเชื่อมกับรายการแลกทองอื่นแล้ว")
        return result
    return create_gold_exchange(old_gold_receipt_id,gold_sale_id,settlement_method,notes,created_by)


def get_gold_exchange(exchange_id):
    ensure_exchange_schema()
    with get_connection() as conn:
        row=conn.execute("""SELECT e.*,o.receipt_no,s.sale_no,u.full_name created_by_name
            FROM gold_exchanges e JOIN old_gold_receipts o ON o.id=e.old_gold_receipt_id
            JOIN gold_sales s ON s.id=e.gold_sale_id LEFT JOIN users u ON u.id=e.created_by
            WHERE e.id=?""",(int(exchange_id),)).fetchone()
    return dict(row) if row else None


ensure_exchange_schema()
