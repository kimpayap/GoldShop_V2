from datetime import date,datetime

from database.database import get_connection
from modules.stock import ensure_stock_schema
from modules.qr_code import item_code_from_qr
from modules.document_numbers import next_document_no


DEFAULT_CARD_FEE_RATE = 3.0
VAT_RATE = 7.0


def ensure_sales_schema():
    ensure_stock_schema()
    with get_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS gold_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_no TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'completed',
            sale_date TEXT NOT NULL,
            customer_name TEXT,
            customer_tax_id TEXT,
            customer_address TEXT,
            payment_method TEXT NOT NULL,
            card_fee_rate REAL NOT NULL DEFAULT 0,
            amount_before_fee REAL NOT NULL,
            card_fee_amount REAL NOT NULL DEFAULT 0,
            amount_paid REAL NOT NULL,
            subtotal_ex_vat REAL NOT NULL,
            vat_base REAL NOT NULL,
            vat_amount REAL NOT NULL,
            grand_total REAL NOT NULL,
            notes TEXT,
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            cancelled_at TEXT,
            cancelled_by INTEGER,
            cancel_reason TEXT,
            FOREIGN KEY(created_by) REFERENCES users(id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS gold_sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            line_no INTEGER NOT NULL,
            inventory_item_id INTEGER NOT NULL,
            item_code TEXT NOT NULL,
            item_type TEXT NOT NULL,
            description TEXT NOT NULL,
            purity REAL NOT NULL,
            weight_grams REAL NOT NULL,
            sale_price_ex_vat REAL NOT NULL,
            gta_buy_reference REAL NOT NULL,
            vat_base REAL NOT NULL,
            vat_rate REAL NOT NULL DEFAULT 7,
            vat_amount REAL NOT NULL,
            total_incl_vat REAL NOT NULL,
            FOREIGN KEY(sale_id) REFERENCES gold_sales(id) ON DELETE CASCADE,
            FOREIGN KEY(inventory_item_id) REFERENCES inventory_items(id)
        )""")
        sale_columns={row[1] for row in conn.execute("PRAGMA table_info(gold_sales)").fetchall()}
        for column in ("gold_bar_price", "gold_jewelry_price", "gold_jewelry_buy_per_gram", "exchange_credit"):
            if column not in sale_columns:
                conn.execute(f"ALTER TABLE gold_sales ADD COLUMN {column} REAL NOT NULL DEFAULT 0")
        conn.execute("""CREATE TABLE IF NOT EXISTS app_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("INSERT OR IGNORE INTO app_settings(setting_key,setting_value) VALUES ('credit_card_fee_rate','3')")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_gold_sales_date ON gold_sales(sale_date,status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_gold_sale_items_inventory ON gold_sale_items(inventory_item_id)")
        conn.commit()


def get_card_fee_rate():
    ensure_sales_schema()
    with get_connection() as conn:
        row = conn.execute("SELECT setting_value FROM app_settings WHERE setting_key='credit_card_fee_rate'").fetchone()
    try: return float(row["setting_value"] if row else DEFAULT_CARD_FEE_RATE)
    except (TypeError, ValueError): return DEFAULT_CARD_FEE_RATE


def save_card_fee_rate(rate):
    value = float(rate)
    if value < 0 or value > 100: raise ValueError("ค่าธรรมเนียมบัตรต้องอยู่ระหว่าง 0–100%")
    ensure_sales_schema()
    with get_connection() as conn:
        conn.execute("""INSERT INTO app_settings(setting_key,setting_value,updated_at)
            VALUES ('credit_card_fee_rate',?,CURRENT_TIMESTAMP)
            ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value,updated_at=CURRENT_TIMESTAMP""", (f"{value:g}",))
        conn.commit()
    return value


def calculate_card_payment(amount=None, rate=DEFAULT_CARD_FEE_RATE, total_with_fee=None):
    fee_rate = float(rate or 0)
    if fee_rate < 0 or fee_rate > 100: raise ValueError("ค่าธรรมเนียมบัตรต้องอยู่ระหว่าง 0–100%")
    if total_with_fee is not None:
        paid = round(float(total_with_fee or 0), 2)
        before = round(paid / (1 + fee_rate / 100.0), 2) if fee_rate else paid
        fee = round(paid - before, 2)
    else:
        before = round(float(amount or 0), 2)
        fee = round(before * fee_rate / 100.0, 2)
        paid = round(before + fee, 2)
    if min(before, fee, paid) < 0: raise ValueError("ยอดรับชำระต้องไม่ติดลบ")
    return {"amount_before_fee": before, "card_fee_rate": fee_rate, "card_fee_amount": fee, "amount_paid": paid}


def get_inventory_by_scan(value):
    ensure_sales_schema()
    text = str(value or "").strip()
    if not text: return None
    try: code = item_code_from_qr(text)
    except ValueError: code = text.upper()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM inventory_items WHERE UPPER(item_code)=?", (code,)).fetchone()
    return dict(row) if row else None


def calculate_sale_item(item, total_incl_vat, jewelry_buy_per_baht, weight_per_baht=15.244, vat_rate=VAT_RATE):
    total = round(float(total_incl_vat or 0), 2)
    weight = float(item.get("weight_grams") or 0)
    purity = float(item.get("purity") or 0)
    reference_price = float(jewelry_buy_per_baht or 0)
    grams = float(weight_per_baht or 0)
    rate = float(vat_rate or 0)
    if total <= 0: raise ValueError("ราคาขายต้องมากกว่า 0")
    if min(weight, purity, reference_price, grams) <= 0: raise ValueError("ข้อมูลสินค้าและราคารับซื้อทองอ้างอิงไม่ถูกต้อง")
    # ราคาซื้อคืนอ้างอิงปรับตามน้ำหนักและความบริสุทธิ์ของชิ้นงาน
    gta_reference = round((weight / grams) * reference_price * (purity / 96.5), 2)
    # เมื่อราคาที่หน้าร้านรวม VAT แล้ว: VAT = ส่วนต่างรวม VAT × 7/107
    margin_incl_vat = max(0.0, total - gta_reference)
    vat = round(margin_incl_vat * rate / (100.0 + rate), 2) if rate else 0.0
    sale_ex_vat = round(total - vat, 2)
    vat_base = round(max(0.0, sale_ex_vat - gta_reference), 2)
    return {
        **item, "sale_price_ex_vat": sale_ex_vat, "gta_buy_reference": gta_reference,
        "vat_base": vat_base, "vat_rate": rate, "vat_amount": vat, "total_incl_vat": total,
    }


def calculate_sale_totals(items):
    return {
        "subtotal_ex_vat": round(sum(float(x["sale_price_ex_vat"]) for x in items), 2),
        "vat_base": round(sum(float(x["vat_base"]) for x in items), 2),
        "vat_amount": round(sum(float(x["vat_amount"]) for x in items), 2),
        "grand_total": round(sum(float(x["total_incl_vat"]) for x in items), 2),
    }


def _next_sale_no(conn):
    while True:
        number=next_document_no(conn,"gold_sale","SALE")
        if not conn.execute("SELECT 1 FROM gold_sales WHERE sale_no=?",(number,)).fetchone():return number


def confirm_gold_sale(header, items, created_by=None):
    ensure_sales_schema()
    if not items: raise ValueError("กรุณาเลือกสินค้าอย่างน้อย 1 รายการ")
    totals = calculate_sale_totals(items)
    method = str(header.get("payment_method") or "เงินสด")
    if method not in {"เงินสด", "โอนเงิน", "บัตรเครดิต"}: raise ValueError("วิธีชำระเงินไม่ถูกต้อง")
    exchange_credit=round(float(header.get("exchange_credit") or 0),2)
    settlement_base=max(0.0,round(totals["grand_total"]-exchange_credit,2))
    payment = calculate_card_payment(settlement_base, header.get("card_fee_rate", 0)) if method == "บัตรเครดิต" else calculate_card_payment(settlement_base, 0)
    entered_paid = round(float(header.get("amount_paid", payment["amount_paid"])), 2)
    if abs(entered_paid - payment["amount_paid"]) > 0.01: raise ValueError("ยอดรับชำระไม่ตรงกับยอดที่ระบบคำนวณ")
    with get_connection() as conn:
        inventory_ids = [int(x["id"]) for x in items]
        placeholders = ",".join("?" * len(inventory_ids))
        rows = conn.execute(f"SELECT id,status FROM inventory_items WHERE id IN ({placeholders})", inventory_ids).fetchall()
        status = {row["id"]: row["status"] for row in rows}
        unavailable = [x["item_code"] for x in items if status.get(int(x["id"])) != "in_stock"]
        if unavailable: raise ValueError("สินค้าถูกขายหรือไม่อยู่ในสต็อกแล้ว: " + ", ".join(unavailable))
        sale_no = _next_sale_no(conn)
        cursor = conn.execute("""INSERT INTO gold_sales
            (sale_no,sale_date,customer_name,customer_tax_id,customer_address,payment_method,
             card_fee_rate,amount_before_fee,card_fee_amount,amount_paid,subtotal_ex_vat,vat_base,
             vat_amount,grand_total,notes,created_by,gold_bar_price,gold_jewelry_price,
             gold_jewelry_buy_per_gram,exchange_credit) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            sale_no,str(header.get("sale_date") or date.today().isoformat()),str(header.get("customer_name") or "").strip(),
            str(header.get("customer_tax_id") or "").strip(),str(header.get("customer_address") or "").strip(),method,
            payment["card_fee_rate"],payment["amount_before_fee"],payment["card_fee_amount"],payment["amount_paid"],
            totals["subtotal_ex_vat"],totals["vat_base"],totals["vat_amount"],totals["grand_total"],
            str(header.get("notes") or "").strip(),created_by,
            float(header.get("gold_bar_price") or 0),float(header.get("gold_jewelry_price") or 0),
            float(header.get("gold_jewelry_buy_per_gram") or 0),exchange_credit))
        sale_id = cursor.lastrowid
        for line_no,item in enumerate(items,1):
            conn.execute("""INSERT INTO gold_sale_items
                (sale_id,line_no,inventory_item_id,item_code,item_type,description,purity,weight_grams,
                 sale_price_ex_vat,gta_buy_reference,vat_base,vat_rate,vat_amount,total_incl_vat)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (sale_id,line_no,int(item["id"]),item["item_code"],item["item_type"],
                item["description"],item["purity"],item["weight_grams"],item["sale_price_ex_vat"],item["gta_buy_reference"],
                item["vat_base"],item["vat_rate"],item["vat_amount"],item["total_incl_vat"]))
            updated = conn.execute("UPDATE inventory_items SET status='sold' WHERE id=? AND status='in_stock'", (int(item["id"]),))
            if updated.rowcount != 1: raise ValueError(f"ไม่สามารถตัดสต็อก {item['item_code']} ได้")
            conn.execute("""INSERT INTO stock_movements
                (inventory_item_id,movement_type,from_status,to_status,reference_type,reference_id,note,created_by)
                VALUES (?,'sale','in_stock','sold','gold_sale',?,'ขายทองใหม่',?)""", (int(item["id"]),sale_id,created_by))
        conn.commit()
    return {"sale_id":sale_id,"sale_no":sale_no,**totals,**payment}


def get_gold_sale(sale_id):
    ensure_sales_schema()
    with get_connection() as conn:
        row=conn.execute("""SELECT s.*,u.full_name AS created_by_name,cu.full_name AS cancelled_by_name
            FROM gold_sales s LEFT JOIN users u ON u.id=s.created_by LEFT JOIN users cu ON cu.id=s.cancelled_by
            WHERE s.id=?""",(int(sale_id),)).fetchone()
        if not row:return None
        items=conn.execute("SELECT * FROM gold_sale_items WHERE sale_id=? ORDER BY line_no",(int(sale_id),)).fetchall()
    result=dict(row);result["items"]=[dict(x) for x in items];return result


def list_gold_sales(keyword="",date_from="",date_to="",status="",payment_method=""):
    ensure_sales_schema();params=[]
    sql="""SELECT DISTINCT s.*,u.full_name AS created_by_name,cu.full_name AS cancelled_by_name,
        (SELECT GROUP_CONCAT(si.item_code, ', ') FROM gold_sale_items si WHERE si.sale_id=s.id) AS item_codes
        FROM gold_sales s LEFT JOIN users u ON u.id=s.created_by LEFT JOIN users cu ON cu.id=s.cancelled_by
        LEFT JOIN gold_sale_items i ON i.sale_id=s.id WHERE 1=1"""
    if str(keyword or "").strip():
        term=f"%{str(keyword).strip()}%";sql+=" AND (s.sale_no LIKE ? OR s.customer_name LIKE ? OR s.customer_tax_id LIKE ? OR i.item_code LIKE ? OR i.description LIKE ?)";params.extend([term]*5)
    if date_from:sql+=" AND s.sale_date>=?";params.append(str(date_from))
    if date_to:sql+=" AND s.sale_date<=?";params.append(str(date_to))
    if status:sql+=" AND s.status=?";params.append(str(status))
    if payment_method:sql+=" AND s.payment_method=?";params.append(str(payment_method))
    sql+=" ORDER BY s.sale_date DESC,s.id DESC"
    with get_connection() as conn:rows=conn.execute(sql,params).fetchall()
    return [dict(x) for x in rows]


def cancel_gold_sale(sale_id,reason,cancelled_by):
    ensure_sales_schema();reason=str(reason or "").strip()
    if not reason:raise ValueError("กรุณาระบุเหตุผลในการยกเลิกการขาย")
    if not cancelled_by:raise ValueError("ไม่พบผู้ดำเนินการยกเลิก")
    with get_connection() as conn:
        operator=conn.execute("SELECT id FROM users WHERE id=? AND active=1",(int(cancelled_by),)).fetchone()
        if not operator:raise ValueError("ไม่พบผู้ใช้งานที่มีสิทธิ์ดำเนินการ")
        sale=conn.execute("SELECT * FROM gold_sales WHERE id=?",(int(sale_id),)).fetchone()
        if not sale:raise ValueError("ไม่พบรายการขาย")
        if sale["status"]=="cancelled":raise ValueError("รายการขายนี้ถูกยกเลิกแล้ว")
        if sale["status"]!="completed":raise ValueError("ยกเลิกได้เฉพาะรายการขายที่เสร็จสมบูรณ์")
        items=conn.execute("SELECT inventory_item_id,item_code FROM gold_sale_items WHERE sale_id=? ORDER BY line_no",(int(sale_id),)).fetchall()
        if not items:raise ValueError("รายการขายไม่มีข้อมูลสินค้า")
        unavailable=[]
        for item in items:
            state=conn.execute("SELECT status FROM inventory_items WHERE id=?",(item["inventory_item_id"],)).fetchone()
            if not state or state["status"]!="sold":unavailable.append(item["item_code"])
        if unavailable:raise ValueError("ไม่สามารถคืนสต็อกได้ เนื่องจากสถานะสินค้าเปลี่ยนไป: "+", ".join(unavailable))
        cancelled_at=datetime.now().isoformat(timespec="seconds")
        conn.execute("UPDATE gold_sales SET status='cancelled',cancelled_at=?,cancelled_by=?,cancel_reason=? WHERE id=?",(cancelled_at,int(cancelled_by),reason,int(sale_id)))
        conn.execute("UPDATE stock_movements SET movement_status='reversed' WHERE reference_type='gold_sale' AND reference_id=? AND movement_type='sale'",(int(sale_id),))
        for item in items:
            updated=conn.execute("UPDATE inventory_items SET status='in_stock' WHERE id=? AND status='sold'",(item["inventory_item_id"],))
            if updated.rowcount!=1:raise ValueError(f"คืนสินค้า {item['item_code']} เข้าสต็อกไม่สำเร็จ")
            conn.execute("""INSERT INTO stock_movements
                (inventory_item_id,movement_type,from_status,to_status,reference_type,reference_id,note,created_by)
                VALUES (?,'sale_cancel','sold','in_stock','gold_sale_cancel',?,?,?)""",(item["inventory_item_id"],int(sale_id),f"ยกเลิกการขาย {sale['sale_no']}: {reason}",int(cancelled_by)))
        conn.commit()
    return {"sale_id":int(sale_id),"sale_no":sale["sale_no"],"cancelled_at":cancelled_at,"returned_items":len(items),"reason":reason}


ensure_sales_schema()
