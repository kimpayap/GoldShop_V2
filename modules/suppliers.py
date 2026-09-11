from database.database import get_connection


def ensure_supplier_schema():
    with get_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_code TEXT NOT NULL UNIQUE,
            supplier_type TEXT NOT NULL DEFAULT 'ผู้จำหน่าย',
            business_name TEXT NOT NULL,
            tax_id TEXT,
            contact_name TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            bank_account TEXT,
            notes TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(business_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_tax ON suppliers(tax_id)")
        conn.commit()


def _next_code(conn):
    row = conn.execute("SELECT COALESCE(MAX(id),0)+1 AS next_id FROM suppliers").fetchone()
    return f"SUP{int(row['next_id']):05d}"


def save_supplier(data, supplier_id=None):
    ensure_supplier_schema()
    business_name = str(data.get("business_name") or "").strip()
    if not business_name: raise ValueError("กรุณาระบุชื่อกิจการ/คู่ค้า")
    supplier_type = str(data.get("supplier_type") or "ผู้จำหน่าย").strip()
    if supplier_type not in {"ผู้จำหน่าย", "คู่ค้า", "ผู้จำหน่ายและคู่ค้า"}:
        raise ValueError("ประเภทคู่ค้าไม่ถูกต้อง")
    values = (
        supplier_type, business_name, str(data.get("tax_id") or "").strip(),
        str(data.get("contact_name") or "").strip(), str(data.get("phone") or "").strip(),
        str(data.get("email") or "").strip(), str(data.get("address") or "").strip(),
        str(data.get("bank_account") or "").strip(), str(data.get("notes") or "").strip(),
        int(bool(data.get("active", True))),
    )
    with get_connection() as conn:
        if supplier_id:
            cursor = conn.execute("""UPDATE suppliers SET supplier_type=?,business_name=?,tax_id=?,contact_name=?,
                phone=?,email=?,address=?,bank_account=?,notes=?,active=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                values + (int(supplier_id),))
            if cursor.rowcount != 1: raise ValueError("ไม่พบข้อมูลคู่ค้าที่ต้องการแก้ไข")
            saved_id = int(supplier_id)
        else:
            code = _next_code(conn)
            cursor = conn.execute("""INSERT INTO suppliers
                (supplier_code,supplier_type,business_name,tax_id,contact_name,phone,email,address,bank_account,notes,active)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (code,) + values)
            saved_id = cursor.lastrowid
        conn.commit()
    return get_supplier(saved_id)


def get_supplier(supplier_id):
    ensure_supplier_schema()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM suppliers WHERE id=?", (int(supplier_id),)).fetchone()
    return dict(row) if row else None


def list_suppliers(keyword="", active_only=False):
    ensure_supplier_schema()
    keyword = str(keyword or "").strip()
    sql = "SELECT * FROM suppliers WHERE 1=1"
    params = []
    if active_only: sql += " AND active=1"
    if keyword:
        term = f"%{keyword}%"
        sql += " AND (supplier_code LIKE ? OR business_name LIKE ? OR tax_id LIKE ? OR contact_name LIKE ? OR phone LIKE ?)"
        params.extend([term] * 5)
    sql += " ORDER BY active DESC,business_name,supplier_code"
    with get_connection() as conn: rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def toggle_supplier(supplier_id):
    ensure_supplier_schema()
    with get_connection() as conn:
        cursor = conn.execute("UPDATE suppliers SET active=CASE active WHEN 1 THEN 0 ELSE 1 END,updated_at=CURRENT_TIMESTAMP WHERE id=?", (int(supplier_id),))
        if cursor.rowcount != 1: raise ValueError("ไม่พบข้อมูลคู่ค้า")
        conn.commit()
    return get_supplier(supplier_id)


ensure_supplier_schema()
