from datetime import date

from database.database import get_connection
from modules.qr_code import qr_payload
from modules.suppliers import ensure_supplier_schema


def ensure_stock_schema():
    ensure_supplier_schema()
    with get_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS stock_receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_no TEXT NOT NULL UNIQUE,
            supplier_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'confirmed',
            received_date TEXT NOT NULL,
            supplier_document_no TEXT,
            tax_invoice_no TEXT,
            document_date TEXT,
            reference_gold_price REAL NOT NULL DEFAULT 0,
            payment_type TEXT NOT NULL DEFAULT 'เงินสด',
            payment_due_date TEXT,
            total_quantity INTEGER NOT NULL DEFAULT 0,
            total_weight_grams REAL NOT NULL DEFAULT 0,
            subtotal REAL NOT NULL DEFAULT 0,
            vat_amount REAL NOT NULL DEFAULT 0,
            grand_total REAL NOT NULL DEFAULT 0,
            notes TEXT,
            created_by INTEGER,
            confirmed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            cancelled_at TEXT,
            cancelled_by INTEGER,
            cancel_reason TEXT,
            FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
            FOREIGN KEY(created_by) REFERENCES users(id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS stock_receipt_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_receipt_id INTEGER NOT NULL,
            line_no INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            description TEXT NOT NULL,
            purity REAL NOT NULL,
            weight_grams REAL NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            gold_cost REAL NOT NULL DEFAULT 0,
            workmanship_cost REAL NOT NULL DEFAULT 0,
            discount REAL NOT NULL DEFAULT 0,
            vat_rate REAL NOT NULL DEFAULT 7,
            unit_subtotal REAL NOT NULL,
            unit_vat REAL NOT NULL,
            unit_total REAL NOT NULL,
            suggested_sale_price REAL NOT NULL DEFAULT 0,
            storage_location TEXT,
            notes TEXT,
            FOREIGN KEY(stock_receipt_id) REFERENCES stock_receipts(id) ON DELETE CASCADE
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS inventory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT NOT NULL UNIQUE,
            qr_payload TEXT NOT NULL UNIQUE,
            source_type TEXT NOT NULL DEFAULT 'new_purchase',
            stock_receipt_id INTEGER,
            stock_receipt_line_id INTEGER,
            supplier_id INTEGER,
            item_type TEXT NOT NULL,
            description TEXT NOT NULL,
            purity REAL NOT NULL,
            weight_grams REAL NOT NULL,
            gold_cost REAL NOT NULL DEFAULT 0,
            workmanship_cost REAL NOT NULL DEFAULT 0,
            discount REAL NOT NULL DEFAULT 0,
            vat_amount REAL NOT NULL DEFAULT 0,
            total_cost REAL NOT NULL DEFAULT 0,
            suggested_sale_price REAL NOT NULL DEFAULT 0,
            storage_location TEXT,
            status TEXT NOT NULL DEFAULT 'in_stock',
            acquired_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY(stock_receipt_id) REFERENCES stock_receipts(id),
            FOREIGN KEY(stock_receipt_line_id) REFERENCES stock_receipt_lines(id),
            FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
            FOREIGN KEY(created_by) REFERENCES users(id)
        )""")
        for table in ("stock_receipt_lines","inventory_items"):
            columns={row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if "gold_detail_id" not in columns:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN gold_detail_id INTEGER REFERENCES gold_details(id)")
        conn.execute("""UPDATE inventory_items SET gold_detail_id=(SELECT id FROM gold_details WHERE gold_details.name=inventory_items.description)
            WHERE gold_detail_id IS NULL""")
        conn.execute("""CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventory_item_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT NOT NULL,
            reference_type TEXT NOT NULL,
            reference_id INTEGER NOT NULL,
            movement_status TEXT NOT NULL DEFAULT 'completed',
            note TEXT,
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(inventory_item_id) REFERENCES inventory_items(id),
            FOREIGN KEY(created_by) REFERENCES users(id)
        )""")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_supplier_document_unique ON stock_receipts(supplier_id,supplier_document_no) WHERE supplier_document_no<>'' AND status<>'cancelled'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_inventory_status ON inventory_items(status,item_type)")
        conn.commit()


def calculate_stock_line(line):
    try: quantity = int(str(line.get("quantity") or "0").strip())
    except (TypeError,ValueError): raise ValueError("จำนวนชิ้นต้องเป็นเลขจำนวนเต็ม")
    def number(key,label,default="0"):
        try:return float(str(line.get(key) if line.get(key) not in (None,"") else default).strip())
        except (TypeError,ValueError):raise ValueError(f"{label}ต้องเป็นตัวเลข")
    weight = number("weight_grams","น้ำหนักทองสุทธิ")
    purity = number("purity","เปอร์เซ็นต์ทอง")
    gold_cost = number("gold_cost","ต้นทุนทอง")
    workmanship = number("workmanship_cost","ค่ากำเหน็จ")
    discount = number("discount","ส่วนลด")
    vat_rate = number("vat_rate","VAT",0)
    if quantity <= 0: raise ValueError("จำนวนชิ้นต้องมากกว่า 0")
    if weight <= 0: raise ValueError("น้ำหนักทองสุทธิต้องมากกว่า 0")
    if purity <= 0 or purity > 100: raise ValueError("เปอร์เซ็นต์ทองต้องอยู่ระหว่าง 0–100")
    if gold_cost <= 0: raise ValueError("ต้นทุนทองต้องมากกว่า 0")
    if min(gold_cost, workmanship, discount, vat_rate) < 0: raise ValueError("ต้นทุน ส่วนลด และภาษีต้องไม่ติดลบ")
    unit_subtotal = gold_cost + workmanship - discount
    if unit_subtotal < 0: raise ValueError("ส่วนลดมากกว่าต้นทุน")
    # ภาษีซื้อของทองใหม่ต้องยึดตามใบกำกับภาษีจากผู้จำหน่าย ภาษีจะถูก
    # กระจายให้แต่ละรายการตอนยืนยันใบรับ ไม่คำนวณ 7% จากต้นทุนสินค้าเอง
    unit_vat = number("unit_vat", "VAT ตามใบกำกับภาษี", 0)
    return {
        **line, "quantity": quantity, "weight_grams": weight, "purity": purity,
        "gold_cost": gold_cost, "workmanship_cost": workmanship, "discount": discount,
        "vat_rate": vat_rate, "unit_subtotal": round(unit_subtotal, 2),
        "unit_vat": unit_vat, "unit_total": round(unit_subtotal + unit_vat, 2),
    }


def calculate_gold_cost(weight_grams, purity, reference_gold_price, weight_per_baht=15.244):
    """คำนวณมูลค่าเนื้อทองต่อชิ้นจากราคาทองคำแท่ง 96.5% ต่อหนึ่งบาททอง"""
    weight = float(weight_grams or 0)
    percent = float(purity or 0)
    price = float(reference_gold_price or 0)
    baht_weight = float(weight_per_baht or 0)
    if weight <= 0 or percent <= 0 or percent > 100 or price <= 0 or baht_weight <= 0:
        return 0.0
    return round((weight / baht_weight) * price * (percent / 96.5), 2)


def apply_invoice_vat(lines, invoice_vat_amount):
    """กระจายยอด VAT รวมจากใบกำกับภาษีตามสัดส่วนมูลค่าก่อนภาษีของแต่ละบรรทัด"""
    calculated = [calculate_stock_line(line) for line in lines]
    try:
        total_vat = round(float(invoice_vat_amount or 0), 2)
    except (TypeError, ValueError):
        raise ValueError("VAT ตามใบกำกับภาษีต้องเป็นตัวเลข")
    if total_vat < 0:
        raise ValueError("VAT ตามใบกำกับภาษีต้องไม่ติดลบ")
    subtotal = sum(line["unit_subtotal"] * line["quantity"] for line in calculated)
    allocated = 0.0
    for index, line in enumerate(calculated):
        line_subtotal = line["unit_subtotal"] * line["quantity"]
        line_vat = (total_vat - allocated) if index == len(calculated) - 1 else round(total_vat * line_subtotal / subtotal, 2) if subtotal else 0.0
        allocated += line_vat
        line["unit_vat"] = line_vat / line["quantity"]
        line["unit_total"] = line["unit_subtotal"] + line["unit_vat"]
        line["vat_rate"] = (line_vat / line_subtotal * 100.0) if line_subtotal else 0.0
    return calculated


def _next_number(conn, table, prefix):
    next_id = conn.execute(f"SELECT COALESCE(MAX(id),0)+1 AS n FROM {table}").fetchone()["n"]
    return f"{prefix}{int(next_id):06d}"


def confirm_new_gold_receipt(header, lines, created_by=None):
    ensure_stock_schema()
    if not lines: raise ValueError("กรุณาเพิ่มรายการทองอย่างน้อย 1 รายการ")
    supplier_id = int(header.get("supplier_id") or 0)
    received_date = str(header.get("received_date") or date.today().isoformat())
    calculated = apply_invoice_vat(lines, header.get("invoice_vat_amount", 0))
    total_quantity = sum(line["quantity"] for line in calculated)
    total_weight = sum(line["weight_grams"] * line["quantity"] for line in calculated)
    subtotal = sum(line["unit_subtotal"] * line["quantity"] for line in calculated)
    vat = round(float(header.get("invoice_vat_amount") or 0), 2)
    grand_total = sum(line["unit_total"] * line["quantity"] for line in calculated)
    with get_connection() as conn:
        supplier = conn.execute("SELECT * FROM suppliers WHERE id=? AND active=1", (supplier_id,)).fetchone()
        if not supplier: raise ValueError("กรุณาเลือกผู้จำหน่ายที่เปิดใช้งาน")
        document_no = str(header.get("supplier_document_no") or "").strip()
        if document_no:
            duplicate = conn.execute("SELECT receipt_no FROM stock_receipts WHERE supplier_id=? AND supplier_document_no=? AND status<>'cancelled'", (supplier_id, document_no)).fetchone()
            if duplicate: raise ValueError(f"เลขที่เอกสารนี้ถูกใช้แล้วใน {duplicate['receipt_no']}")
        receipt_no = _next_number(conn, "stock_receipts", "GRN")
        cursor = conn.execute("""INSERT INTO stock_receipts
            (receipt_no,supplier_id,received_date,supplier_document_no,tax_invoice_no,document_date,
             reference_gold_price,payment_type,payment_due_date,total_quantity,total_weight_grams,
             subtotal,vat_amount,grand_total,notes,created_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            receipt_no, supplier_id, received_date, document_no,
            str(header.get("tax_invoice_no") or "").strip(), str(header.get("document_date") or received_date),
            float(header.get("reference_gold_price") or 0), str(header.get("payment_type") or "เงินสด"),
            str(header.get("payment_due_date") or "").strip(), total_quantity, total_weight,
            round(subtotal,2), round(vat,2), round(grand_total,2), str(header.get("notes") or "").strip(), created_by,
        ))
        receipt_id = cursor.lastrowid
        item_ids = []
        for line_no, line in enumerate(calculated, 1):
            line_cursor = conn.execute("""INSERT INTO stock_receipt_lines
                (stock_receipt_id,line_no,item_type,description,gold_detail_id,purity,weight_grams,quantity,gold_cost,
                 workmanship_cost,discount,vat_rate,unit_subtotal,unit_vat,unit_total,suggested_sale_price,
                 storage_location,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                receipt_id,line_no,str(line.get("item_type") or "ทองใหม่"),str(line.get("description") or "").strip(),
                int(line.get("gold_detail_id")) if line.get("gold_detail_id") else None,
                line["purity"],line["weight_grams"],line["quantity"],line["gold_cost"],line["workmanship_cost"],
                line["discount"],line["vat_rate"],line["unit_subtotal"],line["unit_vat"],line["unit_total"],
                float(line.get("suggested_sale_price") or 0),str(line.get("storage_location") or "").strip(),str(line.get("notes") or "").strip(),
            ))
            for _ in range(line["quantity"]):
                item_code = _next_number(conn, "inventory_items", "ITM")
                item_cursor = conn.execute("""INSERT INTO inventory_items
                    (item_code,qr_payload,source_type,stock_receipt_id,stock_receipt_line_id,supplier_id,item_type,
                     description,gold_detail_id,purity,weight_grams,gold_cost,workmanship_cost,discount,vat_amount,total_cost,
                     suggested_sale_price,storage_location,status,created_by)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'in_stock',?)""", (
                    item_code,qr_payload(item_code),"new_purchase",receipt_id,line_cursor.lastrowid,supplier_id,
                    str(line.get("item_type") or "ทองใหม่"),str(line.get("description") or "").strip(),
                    int(line.get("gold_detail_id")) if line.get("gold_detail_id") else None,line["purity"],
                    line["weight_grams"],line["gold_cost"],line["workmanship_cost"],line["discount"],line["unit_vat"],
                    line["unit_total"],float(line.get("suggested_sale_price") or 0),str(line.get("storage_location") or "").strip(),created_by,
                ))
                item_ids.append(item_cursor.lastrowid)
                conn.execute("""INSERT INTO stock_movements
                    (inventory_item_id,movement_type,from_status,to_status,reference_type,reference_id,note,created_by)
                    VALUES (?,'stock_in',NULL,'in_stock','stock_receipt',?,'รับทองใหม่เข้าสต็อก',?)""",
                    (item_cursor.lastrowid,receipt_id,created_by))
        conn.commit()
    return {"receipt_id":receipt_id,"receipt_no":receipt_no,"item_ids":item_ids,"total_quantity":total_quantity,
            "total_weight_grams":round(total_weight,3),"subtotal":round(subtotal,2),"vat_amount":round(vat,2),"grand_total":round(grand_total,2)}


def get_stock_receipt(receipt_id):
    ensure_stock_schema()
    with get_connection() as conn:
        header = conn.execute("""SELECT r.*,s.supplier_code,s.business_name,s.tax_id,s.address,s.phone
            FROM stock_receipts r JOIN suppliers s ON s.id=r.supplier_id WHERE r.id=?""", (int(receipt_id),)).fetchone()
        if not header: return None
        lines = conn.execute("SELECT * FROM stock_receipt_lines WHERE stock_receipt_id=? ORDER BY line_no", (int(receipt_id),)).fetchall()
        items = conn.execute("SELECT * FROM inventory_items WHERE stock_receipt_id=? ORDER BY id", (int(receipt_id),)).fetchall()
    result=dict(header);result["lines"]=[dict(x) for x in lines];result["items"]=[dict(x) for x in items];return result


def list_inventory(keyword="", status="in_stock"):
    ensure_stock_schema();params=[]
    sql="""SELECT i.*,s.business_name,d.image_path,d.name AS pattern_name FROM inventory_items i
        LEFT JOIN suppliers s ON s.id=i.supplier_id LEFT JOIN gold_details d ON d.id=i.gold_detail_id WHERE 1=1"""
    if status:sql+=" AND i.status=?";params.append(status)
    if str(keyword or "").strip():
        term=f"%{str(keyword).strip()}%";sql+=" AND (i.item_code LIKE ? OR i.item_type LIKE ? OR i.description LIKE ? OR s.business_name LIKE ?)";params.extend([term]*4)
    sql+=" ORDER BY i.id DESC"
    with get_connection() as conn:rows=conn.execute(sql,params).fetchall()
    return [dict(row) for row in rows]


ensure_stock_schema()
