from datetime import date, datetime, timedelta
from math import ceil
from database.database import get_connection
from modules.document_numbers import next_document_no


def ensure_pawn_schema():
    """สร้าง/อัปเดตตาราง V2 ที่เกี่ยวกับระบบขายฝาก โดยไม่ลบข้อมูลเดิม"""
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
        legacy=conn.execute("SELECT * FROM pawn_settings WHERE id=1").fetchone()
        conn.execute("""CREATE TABLE IF NOT EXISTS contract_series(
            series_code TEXT PRIMARY KEY CHECK(series_code IN ('P','Q')),
            series_name TEXT NOT NULL,monthly_interest_rate REAL NOT NULL,
            default_term_days INTEGER NOT NULL DEFAULT 120,next_number INTEGER NOT NULL DEFAULT 1,
            active INTEGER NOT NULL DEFAULT 1,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        for code,name in (("P","ระบบขายฝาก P"),("Q","ระบบขายฝาก Q")):
            conn.execute("""INSERT OR IGNORE INTO contract_series
                (series_code,series_name,monthly_interest_rate,default_term_days)
                VALUES (?,?,?,?)""",(code,name,float(legacy["monthly_interest_rate"]),int(legacy["loan_term_days"])))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pawn_item_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                purity REAL NOT NULL DEFAULT 96.5,
                default_weight_baht REAL NOT NULL DEFAULT 1.00,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gold_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gold_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        detail_columns = {row[1] for row in conn.execute("PRAGMA table_info(gold_details)").fetchall()}
        if "image_path" not in detail_columns:
            conn.execute("ALTER TABLE gold_details ADD COLUMN image_path TEXT")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gold_purities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                percent REAL NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pawn_weight_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit TEXT NOT NULL CHECK(unit IN ('baht','gram')),
                label TEXT NOT NULL,
                value REAL NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(unit, label)
            )
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
        # ค่าเริ่มต้นของการตั้งค่าแบบอิสระ
        type_defaults = ["ทองรูปพรรณ", "ทองคำแท่ง", "ทองเก่า", "ทองอื่น ๆ"]
        detail_defaults = ["แหวน", "สร้อยคอ", "สร้อยข้อมือ", "กำไล", "ต่างหู", "จี้", "ทองแท่ง", "อื่น ๆ"]
        purity_defaults = [("99.99%",99.99),("96.5%",96.5),("90%",90.0),("80%",80.0),("50%",50.0),("40%",40.0)]
        for i, name in enumerate(type_defaults, 1):
            conn.execute("INSERT OR IGNORE INTO gold_types(name,sort_order) VALUES (?,?)", (name,i))
        for i, name in enumerate(detail_defaults, 1):
            conn.execute("INSERT OR IGNORE INTO gold_details(name,sort_order) VALUES (?,?)", (name,i))
        for i, (name, percent) in enumerate(purity_defaults, 1):
            conn.execute("INSERT OR IGNORE INTO gold_purities(name,percent,sort_order) VALUES (?,?,?)", (name,percent,i))
        weight_defaults = [
            ('baht','1/4 บาท',0.25,1), ('baht','1/2 บาท',0.50,2),
            ('baht','1 บาท',1.00,3), ('baht','2 บาท',2.00,4),
            ('baht','3 บาท',3.00,5), ('baht','5 บาท',5.00,6),
            ('gram','1 กรัม',1.00,1), ('gram','2 กรัม',2.00,2),
            ('gram','5 กรัม',5.00,3), ('gram','10 กรัม',10.00,4),
            ('gram','15 กรัม',15.00,5), ('gram','20 กรัม',20.00,6),
        ]
        for unit, label, value, order in weight_defaults:
            conn.execute(
                "INSERT OR IGNORE INTO pawn_weight_options(unit,label,value,sort_order) VALUES (?,?,?,?)",
                (unit,label,value,order)
            )

        # คงข้อมูล preset เดิมไว้เพื่อ backward compatibility
        count = conn.execute("SELECT COUNT(*) FROM pawn_item_presets").fetchone()[0]
        if count == 0:
            defaults = [
                ("ทองรูปพรรณ", "แหวน", 96.5, 1.00),
                ("ทองรูปพรรณ", "สร้อยคอ", 96.5, 1.00),
                ("ทองรูปพรรณ", "สร้อยข้อมือ", 96.5, 1.00),
                ("ทองรูปพรรณ", "กำไล", 96.5, 1.00),
                ("ทองรูปพรรณ", "จี้", 96.5, 1.00),
                ("ทองคำแท่ง", "ทองคำแท่ง", 96.5, 1.00),
            ]
            conn.executemany("""
                INSERT INTO pawn_item_presets
                (item_type, description, purity, default_weight_baht)
                VALUES (?, ?, ?, ?)
            """, defaults)
        # V2.8: การต่อดอกและตั๋วหลุดขายฝาก
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pawn_renewal_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                months INTEGER NOT NULL UNIQUE,
                active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for i, months in enumerate((1, 2, 3, 6, 8, 12), 1):
            conn.execute(
                "INSERT OR IGNORE INTO pawn_renewal_options(label, months, sort_order) VALUES (?, ?, ?)",
                (f"{months} เดือน", months, i)
            )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS pawn_renewals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pawn_ticket_id INTEGER NOT NULL,
                renew_months INTEGER NOT NULL,
                interest_amount REAL NOT NULL,
                paid_amount REAL NOT NULL,
                previous_due_date TEXT NOT NULL,
                new_due_date TEXT NOT NULL,
                renewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                note TEXT,
                created_by INTEGER,
                FOREIGN KEY(pawn_ticket_id) REFERENCES pawn_tickets(id) ON DELETE CASCADE,
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
        """)

        # V2.9: ย้อน/ยกเลิกรายการแบบเก็บ Audit Trail (ไม่ลบข้อมูลเดิม)
        transaction_columns = {row[1] for row in conn.execute("PRAGMA table_info(pawn_transactions)").fetchall()}
        for col, definition in (
            ("transaction_status", "TEXT NOT NULL DEFAULT 'completed'"),
            ("voided_at", "TEXT"),
            ("voided_by", "INTEGER"),
            ("void_reason", "TEXT"),
            ("vat_rate", "REAL NOT NULL DEFAULT 0"),
            ("vat_base", "REAL NOT NULL DEFAULT 0"),
            ("vat_amount", "REAL NOT NULL DEFAULT 0"),
            ("total_with_vat", "REAL NOT NULL DEFAULT 0"),
            ("tax_document_no", "TEXT"),
        ):
            if col not in transaction_columns:
                conn.execute(f"ALTER TABLE pawn_transactions ADD COLUMN {col} {definition}")

        renewal_columns = {row[1] for row in conn.execute("PRAGMA table_info(pawn_renewals)").fetchall()}
        for col, definition in (
            ("renewal_status", "TEXT NOT NULL DEFAULT 'completed'"),
            ("voided_at", "TEXT"),
            ("voided_by", "INTEGER"),
            ("void_reason", "TEXT"),
            ("vat_rate", "REAL NOT NULL DEFAULT 0"),
            ("vat_base", "REAL NOT NULL DEFAULT 0"),
            ("vat_amount", "REAL NOT NULL DEFAULT 0"),
            ("total_with_vat", "REAL NOT NULL DEFAULT 0"),
            ("tax_document_no", "TEXT"),
        ):
            if col not in renewal_columns:
                conn.execute(f"ALTER TABLE pawn_renewals ADD COLUMN {col} {definition}")

        # เพิ่มข้อมูลการหลุดขายฝาก โดย ALTER เฉพาะคอลัมน์ที่ยังไม่มี
        ticket_columns = {row[1] for row in conn.execute("PRAGMA table_info(pawn_tickets)").fetchall()}
        for col, definition in (
            ("forfeited_at", "TEXT"),
            ("forfeited_by", "INTEGER"),
            ("forfeit_note", "TEXT"),
            ("cancelled_at", "TEXT"),
            ("cancelled_by", "INTEGER"),
            ("cancel_reason", "TEXT"),
            ("series_code", "TEXT NOT NULL DEFAULT 'P'"),
            ("contract_term_days", "INTEGER NOT NULL DEFAULT 120"),
        ):
            if col not in ticket_columns:
                conn.execute(f"ALTER TABLE pawn_tickets ADD COLUMN {col} {definition}")
        conn.execute("UPDATE pawn_tickets SET series_code=CASE WHEN UPPER(ticket_no) LIKE 'Q%' THEN 'Q' ELSE 'P' END WHERE series_code IS NULL OR series_code NOT IN ('P','Q') OR UPPER(ticket_no) LIKE 'Q%'")
        conn.execute("UPDATE pawn_tickets SET contract_term_days=CAST(julianday(due_date)-julianday(date(opened_at)) AS INTEGER) WHERE contract_term_days IS NULL OR contract_term_days<=0")
        for code in ("P","Q"):
            maximum=conn.execute("SELECT COALESCE(MAX(CAST(SUBSTR(ticket_no,2) AS INTEGER)),0) FROM pawn_tickets WHERE UPPER(ticket_no) LIKE ?",(code+"%",)).fetchone()[0]
            conn.execute("UPDATE contract_series SET next_number=MAX(next_number,?) WHERE series_code=?",(int(maximum)+1,code))

        conn.commit()


ensure_pawn_schema()


def _next_ticket_no(conn,series_code="P"):
    code=str(series_code or "P").upper()
    if code not in {"P","Q"}:raise ValueError("ชุดสัญญาต้องเป็น P หรือ Q")
    row=conn.execute("SELECT next_number FROM contract_series WHERE series_code=? AND active=1",(code,)).fetchone()
    if not row:raise ValueError(f"ระบบขายฝาก {code} ปิดใช้งานหรือไม่มีการตั้งค่า")
    number=max(1,int(row["next_number"]));ticket=f"{code}{number:06d}"
    while conn.execute("SELECT 1 FROM pawn_tickets WHERE ticket_no=?",(ticket,)).fetchone():
        number+=1;ticket=f"{code}{number:06d}"
    conn.execute("UPDATE contract_series SET next_number=?,updated_at=CURRENT_TIMESTAMP WHERE series_code=?",(number+1,code))
    return ticket


def list_contract_series(active_only=False):
    ensure_pawn_schema()
    with get_connection() as conn:
        sql="SELECT * FROM contract_series"+(" WHERE active=1" if active_only else "")+" ORDER BY series_code"
        return [dict(x) for x in conn.execute(sql).fetchall()]


def get_series_settings(series_code="P"):
    ensure_pawn_schema();code=str(series_code or "P").upper()
    with get_connection() as conn:row=conn.execute("SELECT * FROM contract_series WHERE series_code=?",(code,)).fetchone()
    if not row:raise ValueError(f"ไม่พบการตั้งค่าระบบ {code}")
    return dict(row)


def get_settings(series_code="P"):
    ensure_pawn_schema()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM pawn_settings WHERE id = 1").fetchone()
        series=conn.execute("SELECT * FROM contract_series WHERE series_code=?",(str(series_code or "P").upper(),)).fetchone()
    result=dict(row) if row else {
        "monthly_interest_rate": 2.0,
        "loan_term_days": 120,
        "weight_per_baht_gram": 15.244,
    }
    if series:result.update({"series_code":series["series_code"],"series_name":series["series_name"],"monthly_interest_rate":series["monthly_interest_rate"],"loan_term_days":series["default_term_days"],"active":series["active"],"next_number":series["next_number"]})
    return result


def save_settings(monthly_interest_rate, loan_term_days, weight_per_baht_gram,series_code="P"):
    rate = float(monthly_interest_rate)
    days = int(loan_term_days)
    grams = float(weight_per_baht_gram)
    if rate < 0 or rate > 100:
        raise ValueError("อัตราผลตอบแทนต้องอยู่ระหว่าง 0-100% ต่อเดือน")
    if days <= 0 or days > 3650:
        raise ValueError("ระยะเวลาขายฝากต้องมากกว่า 0 วัน และไม่เกิน 3650 วัน")
    if grams <= 0:
        raise ValueError("น้ำหนัก 1 บาทต้องมากกว่า 0 กรัม")
    with get_connection() as conn:
        code=str(series_code or "P").upper()
        if code not in {"P","Q"}:raise ValueError("ระบบต้องเป็น P หรือ Q")
        conn.execute("UPDATE contract_series SET monthly_interest_rate=?,default_term_days=?,updated_at=CURRENT_TIMESTAMP WHERE series_code=?",(rate,days,code))
        conn.execute("UPDATE pawn_settings SET weight_per_baht_gram=?,updated_at=CURRENT_TIMESTAMP WHERE id=1",(grams,))
        if code=="P":conn.execute("UPDATE pawn_settings SET monthly_interest_rate=?,loan_term_days=? WHERE id=1",(rate,days))
        conn.commit()


def list_item_presets(active_only=True):
    ensure_pawn_schema()
    with get_connection() as conn:
        sql = "SELECT * FROM pawn_item_presets"
        if active_only:
            sql += " WHERE active = 1"
        sql += " ORDER BY item_type, description, id"
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


def save_item_preset(preset_id, item_type, description, purity, default_weight_baht, active=1):
    item_type = str(item_type).strip()
    description = str(description).strip()
    purity = float(purity)
    weight = float(default_weight_baht)
    if not item_type:
        raise ValueError("กรุณาระบุประเภท")
    if not description:
        raise ValueError("กรุณาระบุรายละเอียด")
    if purity <= 0 or purity > 100:
        raise ValueError("เปอร์เซ็นต์ทองต้องมากกว่า 0 และไม่เกิน 100")
    if weight <= 0:
        raise ValueError("น้ำหนักตั้งต้นต้องมากกว่า 0 บาท")
    with get_connection() as conn:
        if preset_id:
            conn.execute("""
                UPDATE pawn_item_presets
                SET item_type=?, description=?, purity=?, default_weight_baht=?,
                    active=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (item_type, description, purity, weight, int(active), int(preset_id)))
        else:
            conn.execute("""
                INSERT INTO pawn_item_presets
                (item_type, description, purity, default_weight_baht, active)
                VALUES (?, ?, ?, ?, ?)
            """, (item_type, description, purity, weight, int(active)))
        conn.commit()


def delete_item_preset(preset_id):
    with get_connection() as conn:
        conn.execute("UPDATE pawn_item_presets SET active=0, updated_at=CURRENT_TIMESTAMP WHERE id=?", (int(preset_id),))
        conn.commit()



def list_gold_types(active_only=True):
    ensure_pawn_schema()
    with get_connection() as conn:
        sql="SELECT * FROM gold_types" + (" WHERE active=1" if active_only else "") + " ORDER BY sort_order,id"
        return [dict(r) for r in conn.execute(sql).fetchall()]


def list_gold_details(active_only=True):
    ensure_pawn_schema()
    with get_connection() as conn:
        sql="SELECT * FROM gold_details" + (" WHERE active=1" if active_only else "") + " ORDER BY sort_order,id"
        return [dict(r) for r in conn.execute(sql).fetchall()]


def list_gold_purities(active_only=True):
    ensure_pawn_schema()
    with get_connection() as conn:
        sql="SELECT * FROM gold_purities" + (" WHERE active=1" if active_only else "") + " ORDER BY sort_order,id"
        return [dict(r) for r in conn.execute(sql).fetchall()]


def save_gold_setting(table, item_id, name, percent=None, active=1):
    if table not in {"gold_types","gold_details","gold_purities"}:
        raise ValueError("ตารางตั้งค่าไม่ถูกต้อง")
    name=str(name).strip()
    if not name: raise ValueError("กรุณาระบุชื่อรายการ")
    with get_connection() as conn:
        if table == "gold_purities":
            if percent is None: raise ValueError("กรุณาระบุเปอร์เซ็นต์ทอง")
            percent=float(percent)
            if percent<=0 or percent>100: raise ValueError("เปอร์เซ็นต์ทองต้องมากกว่า 0 และไม่เกิน 100")
            if item_id:
                conn.execute("UPDATE gold_purities SET name=?,percent=?,active=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(name,percent,int(active),int(item_id)))
                saved_id=int(item_id)
            else:
                saved_id=conn.execute("INSERT INTO gold_purities(name,percent,active) VALUES (?,?,?)",(name,percent,int(active))).lastrowid
        else:
            if item_id:
                conn.execute(f"UPDATE {table} SET name=?,active=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(name,int(active),int(item_id)))
                saved_id=int(item_id)
            else:
                saved_id=conn.execute(f"INSERT INTO {table}(name,active) VALUES (?,?)",(name,int(active))).lastrowid
        conn.commit()
    return saved_id


def toggle_gold_setting(table, item_id):
    if table not in {"gold_types","gold_details","gold_purities"}: raise ValueError("ตารางตั้งค่าไม่ถูกต้อง")
    with get_connection() as conn:
        conn.execute(f"UPDATE {table} SET active=CASE active WHEN 1 THEN 0 ELSE 1 END, updated_at=CURRENT_TIMESTAMP WHERE id=?",(int(item_id),))
        conn.commit()



def move_gold_setting(table, item_id, direction):
    if table not in {"gold_types", "gold_details", "gold_purities"}:
        raise ValueError("ตารางตั้งค่าไม่ถูกต้อง")
    direction = -1 if direction < 0 else 1
    with get_connection() as conn:
        current = conn.execute(
            f"SELECT id, sort_order FROM {table} WHERE id=?", (int(item_id),)
        ).fetchone()
        if not current:
            return
        if direction < 0:
            other = conn.execute(
                f"SELECT id, sort_order FROM {table} WHERE (sort_order < ? OR (sort_order=? AND id<?)) "
                f"ORDER BY sort_order DESC, id DESC LIMIT 1",
                (current['sort_order'], current['sort_order'], current['id'])
            ).fetchone()
        else:
            other = conn.execute(
                f"SELECT id, sort_order FROM {table} WHERE (sort_order > ? OR (sort_order=? AND id>?)) "
                f"ORDER BY sort_order ASC, id ASC LIMIT 1",
                (current['sort_order'], current['sort_order'], current['id'])
            ).fetchone()
        if not other:
            return
        # Swap display order; use temporary value to avoid equal-order ambiguity.
        conn.execute(f"UPDATE {table} SET sort_order=-999999 WHERE id=?", (current['id'],))
        conn.execute(f"UPDATE {table} SET sort_order=? WHERE id=?", (current['sort_order'], other['id']))
        conn.execute(f"UPDATE {table} SET sort_order=? WHERE id=?", (other['sort_order'], current['id']))
        conn.commit()


def list_weight_options(unit=None, active_only=True):
    ensure_pawn_schema()
    with get_connection() as conn:
        sql = "SELECT * FROM pawn_weight_options WHERE 1=1"
        params = []
        if unit:
            sql += " AND unit=?"; params.append(unit)
        if active_only:
            sql += " AND active=1"
        sql += " ORDER BY unit, sort_order, id"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def save_weight_option(item_id, unit, label, value, active=1):
    unit = str(unit).strip().lower()
    if unit not in {'baht','gram'}:
        raise ValueError("หน่วยน้ำหนักไม่ถูกต้อง")
    label = str(label).strip()
    value = float(value)
    if not label:
        raise ValueError("กรุณาระบุชื่อปุ่มน้ำหนัก")
    if value <= 0:
        raise ValueError("น้ำหนักต้องมากกว่า 0")
    with get_connection() as conn:
        if item_id:
            conn.execute(
                "UPDATE pawn_weight_options SET unit=?,label=?,value=?,active=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (unit,label,value,int(active),int(item_id))
            )
        else:
            max_order = conn.execute(
                "SELECT COALESCE(MAX(sort_order),0) FROM pawn_weight_options WHERE unit=?", (unit,)
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO pawn_weight_options(unit,label,value,active,sort_order) VALUES (?,?,?,?,?)",
                (unit,label,value,int(active),max_order+1)
            )
        conn.commit()


def toggle_weight_option(item_id):
    with get_connection() as conn:
        conn.execute(
            "UPDATE pawn_weight_options SET active=CASE active WHEN 1 THEN 0 ELSE 1 END, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (int(item_id),)
        )
        conn.commit()


def move_weight_option(item_id, direction):
    direction = -1 if direction < 0 else 1
    with get_connection() as conn:
        current = conn.execute("SELECT id,unit,sort_order FROM pawn_weight_options WHERE id=?", (int(item_id),)).fetchone()
        if not current: return
        op = '<' if direction < 0 else '>'
        order = 'DESC' if direction < 0 else 'ASC'
        other = conn.execute(
            f"SELECT id,sort_order FROM pawn_weight_options WHERE unit=? AND sort_order {op} ? ORDER BY sort_order {order},id {order} LIMIT 1",
            (current['unit'], current['sort_order'])
        ).fetchone()
        if not other: return
        conn.execute("UPDATE pawn_weight_options SET sort_order=-999999 WHERE id=?", (current['id'],))
        conn.execute("UPDATE pawn_weight_options SET sort_order=? WHERE id=?", (current['sort_order'], other['id']))
        conn.execute("UPDATE pawn_weight_options SET sort_order=? WHERE id=?", (other['sort_order'], current['id']))
        conn.commit()


def _allowed_gold_table(table):
    if table not in {"gold_types", "gold_details", "gold_purities"}:
        raise ValueError("ตารางตั้งค่าไม่ถูกต้อง")
    return table


def _renumber_gold_settings(conn, table):
    table = _allowed_gold_table(table)
    rows = conn.execute(
        f"SELECT id FROM {table} ORDER BY sort_order ASC, id ASC"
    ).fetchall()
    for order, row in enumerate(rows, 1):
        conn.execute(
            f"UPDATE {table} SET sort_order=? WHERE id=?",
            (order, int(row["id"]))
        )


def set_gold_setting_active(table, item_id, active):
    table = _allowed_gold_table(table)
    item_id = int(item_id)
    with get_connection() as conn:
        exists = conn.execute(
            f"SELECT id FROM {table} WHERE id=?", (item_id,)
        ).fetchone()
        if not exists:
            raise ValueError("ไม่พบรายการที่เลือก")
        conn.execute(
            f"UPDATE {table} SET active=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (1 if bool(active) else 0, item_id)
        )
        conn.commit()
    return True


def toggle_gold_setting(table, item_id):
    table = _allowed_gold_table(table)
    item_id = int(item_id)
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT active FROM {table} WHERE id=?", (item_id,)
        ).fetchone()
        if not row:
            raise ValueError("ไม่พบรายการที่เลือก")
        new_active = 0 if int(row["active"] or 0) else 1
        conn.execute(
            f"UPDATE {table} SET active=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (new_active, item_id)
        )
        conn.commit()
    return new_active


def move_gold_setting_v2(table, item_id, direction):
    table = _allowed_gold_table(table)
    item_id = int(item_id)
    step = -1 if int(direction) < 0 else 1
    with get_connection() as conn:
        _renumber_gold_settings(conn, table)
        rows = [int(r["id"]) for r in conn.execute(
            f"SELECT id FROM {table} ORDER BY sort_order ASC, id ASC"
        ).fetchall()]
        if item_id not in rows:
            raise ValueError("ไม่พบรายการที่เลือก")
        old = rows.index(item_id)
        new = old + step
        if new < 0 or new >= len(rows):
            conn.commit()
            return False
        rows[old], rows[new] = rows[new], rows[old]
        for order, rid in enumerate(rows, 1):
            conn.execute(
                f"UPDATE {table} SET sort_order=? WHERE id=?",
                (order, rid)
            )
        conn.commit()
    return True


def set_gold_setting_order(table, item_id, new_order):
    table = _allowed_gold_table(table)
    item_id = int(item_id)
    new_order = int(new_order)
    if new_order < 1:
        raise ValueError("ลำดับต้องเริ่มจาก 1")
    with get_connection() as conn:
        _renumber_gold_settings(conn, table)
        rows = [int(r["id"]) for r in conn.execute(
            f"SELECT id FROM {table} ORDER BY sort_order ASC, id ASC"
        ).fetchall()]
        if item_id not in rows:
            raise ValueError("ไม่พบรายการที่เลือก")
        rows.remove(item_id)
        pos = min(new_order - 1, len(rows))
        rows.insert(pos, item_id)
        for order, rid in enumerate(rows, 1):
            conn.execute(
                f"UPDATE {table} SET sort_order=? WHERE id=?",
                (order, rid)
            )
        conn.commit()
    return True


def _renumber_weight_options(conn, unit):
    rows = conn.execute(
        "SELECT id FROM pawn_weight_options WHERE unit=? ORDER BY sort_order ASC, id ASC",
        (unit,)
    ).fetchall()
    for order, row in enumerate(rows, 1):
        conn.execute(
            "UPDATE pawn_weight_options SET sort_order=? WHERE id=?",
            (order, int(row["id"]))
        )


def set_weight_option_active(item_id, active):
    item_id = int(item_id)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM pawn_weight_options WHERE id=?", (item_id,)
        ).fetchone()
        if not row:
            raise ValueError("ไม่พบปุ่มน้ำหนักที่เลือก")
        conn.execute(
            "UPDATE pawn_weight_options SET active=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (1 if bool(active) else 0, item_id)
        )
        conn.commit()
    return True


def toggle_weight_option(item_id):
    item_id = int(item_id)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT active FROM pawn_weight_options WHERE id=?", (item_id,)
        ).fetchone()
        if not row:
            raise ValueError("ไม่พบปุ่มน้ำหนักที่เลือก")
        new_active = 0 if int(row["active"] or 0) else 1
        conn.execute(
            "UPDATE pawn_weight_options SET active=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (new_active, item_id)
        )
        conn.commit()
    return new_active


def move_weight_option_v2(item_id, direction):
    item_id = int(item_id)
    step = -1 if int(direction) < 0 else 1
    with get_connection() as conn:
        current = conn.execute(
            "SELECT unit FROM pawn_weight_options WHERE id=?", (item_id,)
        ).fetchone()
        if not current:
            raise ValueError("ไม่พบปุ่มน้ำหนักที่เลือก")
        unit = current["unit"]
        _renumber_weight_options(conn, unit)
        rows = [int(r["id"]) for r in conn.execute(
            "SELECT id FROM pawn_weight_options WHERE unit=? ORDER BY sort_order ASC, id ASC",
            (unit,)
        ).fetchall()]
        old = rows.index(item_id)
        new = old + step
        if new < 0 or new >= len(rows):
            conn.commit()
            return False
        rows[old], rows[new] = rows[new], rows[old]
        for order, rid in enumerate(rows, 1):
            conn.execute(
                "UPDATE pawn_weight_options SET sort_order=? WHERE id=?",
                (order, rid)
            )
        conn.commit()
    return True


def set_weight_option_order(item_id, new_order):
    item_id = int(item_id)
    new_order = int(new_order)
    if new_order < 1:
        raise ValueError("ลำดับต้องเริ่มจาก 1")
    with get_connection() as conn:
        current = conn.execute(
            "SELECT unit FROM pawn_weight_options WHERE id=?", (item_id,)
        ).fetchone()
        if not current:
            raise ValueError("ไม่พบปุ่มน้ำหนักที่เลือก")
        unit = current["unit"]
        _renumber_weight_options(conn, unit)
        rows = [int(r["id"]) for r in conn.execute(
            "SELECT id FROM pawn_weight_options WHERE unit=? ORDER BY sort_order ASC, id ASC",
            (unit,)
        ).fetchall()]
        rows.remove(item_id)
        pos = min(new_order - 1, len(rows))
        rows.insert(pos, item_id)
        for order, rid in enumerate(rows, 1):
            conn.execute(
                "UPDATE pawn_weight_options SET sort_order=? WHERE id=?",
                (order, rid)
            )
        conn.commit()
    return True


def get_latest_gold_price():
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM gold_prices ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def search_pawn_customers(keyword=""):
    keyword = keyword.strip()
    with get_connection() as conn:
        if keyword:
            s = f"%{keyword}%"
            rows = conn.execute("""
                SELECT id, customer_code, first_name, last_name, citizen_id, phone, photo_path
                FROM customers
                WHERE customer_code LIKE ? OR first_name LIKE ? OR last_name LIKE ?
                   OR citizen_id LIKE ? OR phone LIKE ?
                ORDER BY id DESC
            """, (s, s, s, s, s)).fetchall()
        else:
            rows = conn.execute("""
                SELECT id, customer_code, first_name, last_name, citizen_id, phone, photo_path
                FROM customers ORDER BY id DESC
            """).fetchall()
    return [dict(r) for r in rows]


def get_customer_by_citizen_id(citizen_id):
    citizen_id = (citizen_id or "").strip()
    if not citizen_id:
        return None
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM customers WHERE citizen_id=? LIMIT 1", (citizen_id,)).fetchone()
    return dict(row) if row else None


def _next_customer_code():
    with get_connection() as conn:
        row = conn.execute("SELECT customer_code FROM customers ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return "C000001"
    try:
        return f"C{int(row['customer_code'][1:]) + 1:06d}"
    except (ValueError, TypeError, IndexError):
        return "C000001"


def _split_thai_name(thai_name):
    text = " ".join((thai_name or "").split())
    for title in ("นาย", "นางสาว", "นาง", "เด็กชาย", "เด็กหญิง"):
        if text.startswith(title):
            text = text[len(title):].strip()
            break
    parts = text.split()
    return (parts[0] if parts else "ลูกค้าจากบัตร", " ".join(parts[1:]) if len(parts) > 1 else "")


def create_customer_from_id_card(card):
    citizen_id = (card.get("citizen_id") or "").strip()
    if not citizen_id:
        raise ValueError("ไม่พบเลขบัตรประชาชนจากบัตร")
    existing = get_customer_by_citizen_id(citizen_id)
    if existing:
        return existing, False
    first_name, last_name = _split_thai_name(card.get("thai_name", ""))
    code = _next_customer_code()
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO customers (
                customer_code, first_name, last_name, citizen_id, phone, address, note,
                thai_name, english_name, birth_date, gender, card_issuer,
                card_issue_date, card_expire_date, photo_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (code, first_name, last_name, citizen_id, "", card.get("address", ""),
              "สร้างจากบัตรประชาชน", card.get("thai_name", ""), card.get("english_name", ""),
              card.get("birth_date", ""), card.get("gender", ""), card.get("issuer", ""),
              card.get("issue_date", ""), card.get("expire_date", ""), card.get("photo_path", "")))
        conn.commit()
        cid = cur.lastrowid
    return get_customer(cid), True


def get_customer(customer_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
    return dict(row) if row else None


def calculate_gold_value(weight_grams, purity, gold_bar_buy, weight_per_baht=15.244):
    weight_grams = float(weight_grams)
    purity = float(purity)
    if weight_grams <= 0 or purity <= 0 or purity > 100 or float(gold_bar_buy or 0) <= 0:
        raise ValueError("ข้อมูลน้ำหนัก/เปอร์เซ็นต์ทอง/ราคาทองไม่ถูกต้อง")
    return (weight_grams / float(weight_per_baht)) * float(gold_bar_buy) * (purity / 96.5)


def calculate_gold_value_baht(weight_baht, purity, gold_bar_buy):
    weight_baht = float(weight_baht)
    purity = float(purity)
    gold_bar_buy = float(gold_bar_buy or 0)
    if weight_baht <= 0:
        raise ValueError("น้ำหนักต้องมากกว่า 0 บาท")
    if purity <= 0 or purity > 100:
        raise ValueError("เปอร์เซ็นต์ทองไม่ถูกต้อง")
    if gold_bar_buy <= 0:
        raise ValueError("ยังไม่มีราคาทองแท่งรับซื้อ")
    return weight_baht * gold_bar_buy * (purity / 96.5)


def calculate_interest(principal, opened_at, as_of=None, monthly_rate=None):
    if as_of is None:
        as_of = date.today()
    if isinstance(opened_at, str):
        opened_date = datetime.fromisoformat(opened_at.replace("Z", "")).date()
    elif isinstance(opened_at, datetime):
        opened_date = opened_at.date()
    else:
        opened_date = opened_at
    days = max(0, (as_of - opened_date).days)
    months = max(1, ceil(days / 30))
    if monthly_rate is None:
        monthly_rate = get_settings()["monthly_interest_rate"]
    interest = float(principal) * (float(monthly_rate) / 100) * months
    return {"days": days, "months": months, "interest": round(interest, 2), "total": round(float(principal) + interest, 2)}


def create_pawn(customer_id, loan_amount, items, notes="", created_by=None,series_code="P",contract_term_days=None):
    customer_id, loan_amount = int(customer_id), float(loan_amount)
    if loan_amount <= 0: raise ValueError("วงเงินขายฝากต้องมากกว่า 0")
    if not items: raise ValueError("กรุณาเพิ่มรายการทรัพย์ขายฝากอย่างน้อย 1 รายการ")
    code=str(series_code or "P").upper();settings, gold = get_settings(code), get_latest_gold_price()
    if not gold: raise ValueError("ยังไม่มีราคาทองในฐานข้อมูล กรุณาดึงราคาทองก่อน")
    term=int(contract_term_days or settings["loan_term_days"])
    if term not in {30,60,90,120}:raise ValueError("ระยะเวลาสัญญาต้องเป็น 30, 60, 90 หรือ 120 วัน")
    due_date = date.today() + timedelta(days=term)
    with get_connection() as conn:
        ticket_no = _next_ticket_no(conn,code)
        cur = conn.execute("""
            INSERT INTO pawn_tickets
            (ticket_no, customer_id, status, gold_price_id, loan_amount, monthly_interest_rate, due_date, notes, created_by,series_code,contract_term_days)
            VALUES (?, ?, 'active', ?, ?, ?, ?, ?, ?,?,?)
        """, (ticket_no, customer_id, gold["id"], loan_amount, settings["monthly_interest_rate"], due_date.isoformat(), notes.strip(), created_by,code,term))
        ticket_id = cur.lastrowid
        for index, item in enumerate(items, 1):
            conn.execute("""
                INSERT INTO pawn_items
                (pawn_ticket_id, item_no, item_type, description, purity, weight_grams,
                 gold_price_per_baht, estimated_value, loan_value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ticket_id, index, item.get("item_type", "ทองรูปพรรณ"), item["description"],
                  float(item.get("purity", 96.5)), float(item["weight_grams"]),
                  float(item.get("gold_price_per_baht", gold["gold_bar_buy"] or 0)),
                  float(item.get("estimated_value", 0)), float(item.get("loan_value", 0))))
        conn.execute("""INSERT INTO pawn_transactions
            (pawn_ticket_id, transaction_type, amount, note, created_by)
            VALUES (?, 'pawn', ?, 'รับขายฝาก', ?)""", (ticket_id, loan_amount, created_by))
        conn.commit()
    return ticket_id, ticket_no


def get_pawn(ticket_id):
    with get_connection() as conn:
        ticket = conn.execute("""
            SELECT p.*, c.customer_code, c.first_name, c.last_name, c.citizen_id, c.phone,
                   c.thai_name, c.english_name, c.birth_date, c.gender, c.card_issuer,
                   c.card_issue_date, c.card_expire_date, c.address, c.photo_path
            FROM pawn_tickets p JOIN customers c ON c.id=p.customer_id WHERE p.id=?
        """, (ticket_id,)).fetchone()
        if not ticket: return None
        items = conn.execute("SELECT * FROM pawn_items WHERE pawn_ticket_id=? ORDER BY item_no", (ticket_id,)).fetchall()
    result = dict(ticket); result["items"] = [dict(x) for x in items]; return result


def list_pawns(keyword="", status="active", date_from="", date_to="", display_status=""):
    keyword = keyword.strip()
    if keyword.startswith("GOLDSHOP:PAWN:"):
        from modules.qr_code import ticket_no_from_qr
        keyword = ticket_no_from_qr(keyword)
    with get_connection() as conn:
        params=[]; sql="""SELECT p.id,p.ticket_no,p.status,p.loan_amount,p.monthly_interest_rate,p.opened_at,p.due_date,
        p.series_code,p.contract_term_days,c.customer_code,c.first_name||' '||c.last_name AS customer_name,c.citizen_id
        FROM pawn_tickets p JOIN customers c ON c.id=p.customer_id WHERE 1=1"""
        requested_display=str(display_status or "").strip()
        if requested_display in {"active","due","overdue"}:status="active"
        elif requested_display:status=requested_display
        if status: sql += " AND p.status=?"; params.append(status)
        if date_from:sql += " AND date(p.opened_at)>=date(?)";params.append(str(date_from))
        if date_to:sql += " AND date(p.opened_at)<=date(?)";params.append(str(date_to))
        if keyword:
            s=f"%{keyword}%"; sql += " AND (p.ticket_no LIKE ? OR c.customer_code LIKE ? OR c.first_name LIKE ? OR c.last_name LIKE ? OR c.citizen_id LIKE ?)"; params.extend([s]*5)
        sql += " ORDER BY p.id DESC"
        rows=conn.execute(sql,params).fetchall()
    result=[dict(r) for r in rows]
    for row in result:row["display_status"]=get_pawn_display_status(row)
    if requested_display in {"active","due","overdue"}:result=[x for x in result if x["display_status"]==requested_display]
    return result


def _parse_date(value):
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    return datetime.fromisoformat(str(value).replace("Z", "")).date()


def _add_months(source_date, months):
    """เพิ่มเดือนแบบปฏิทิน เช่น 31 ม.ค. + 1 เดือน = วันสุดท้ายของ ก.พ."""
    import calendar
    source_date = _parse_date(source_date)
    months = int(months)
    month_index = source_date.month - 1 + months
    year = source_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def get_pawn_display_status(pawn_or_due, stored_status=None, as_of=None):
    """สถานะที่แสดงผล: active / due / overdue / redeemed / forfeited"""
    if isinstance(pawn_or_due, dict):
        stored_status = pawn_or_due.get("status")
        due_value = pawn_or_due.get("due_date")
    else:
        due_value = pawn_or_due
    stored_status = stored_status or "active"
    if stored_status != "active":
        return stored_status
    today = as_of or date.today()
    due = _parse_date(due_value)
    if due < today:
        return "overdue"
    if due == today:
        return "due"
    return "active"


def list_renewal_options(active_only=True):
    ensure_pawn_schema()
    with get_connection() as conn:
        sql = "SELECT * FROM pawn_renewal_options"
        if active_only:
            sql += " WHERE active=1"
        sql += " ORDER BY sort_order,id"
        return [dict(r) for r in conn.execute(sql).fetchall()]


def save_renewal_option(item_id, label, months, active=1):
    label = str(label).strip()
    months = int(months)
    if not label:
        raise ValueError("กรุณาระบุชื่อปุ่ม")
    if months <= 0 or months > 120:
        raise ValueError("จำนวนเดือนต้องอยู่ระหว่าง 1-120 เดือน")
    with get_connection() as conn:
        if item_id:
            conn.execute(
                "UPDATE pawn_renewal_options SET label=?,months=?,active=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (label, months, int(active), int(item_id))
            )
        else:
            max_order = conn.execute("SELECT COALESCE(MAX(sort_order),0) FROM pawn_renewal_options").fetchone()[0]
            conn.execute(
                "INSERT INTO pawn_renewal_options(label,months,active,sort_order) VALUES (?,?,?,?)",
                (label, months, int(active), int(max_order)+1)
            )
        conn.commit()


def set_renewal_option_active(item_id, active):
    with get_connection() as conn:
        conn.execute(
            "UPDATE pawn_renewal_options SET active=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (1 if active else 0, int(item_id))
        )
        conn.commit()


def move_renewal_option(item_id, direction):
    direction = -1 if int(direction) < 0 else 1
    with get_connection() as conn:
        rows = conn.execute("SELECT id FROM pawn_renewal_options ORDER BY sort_order,id").fetchall()
        ids = [r["id"] for r in rows]
        item_id = int(item_id)
        if item_id not in ids:
            return
        i = ids.index(item_id)
        j = i + direction
        if j < 0 or j >= len(ids):
            return
        ids[i], ids[j] = ids[j], ids[i]
        for order, rid in enumerate(ids, 1):
            conn.execute("UPDATE pawn_renewal_options SET sort_order=? WHERE id=?", (order, rid))
        conn.commit()


def list_pawns_for_renew(keyword=""):
    """ตั๋วที่ยังไม่ปิด ทั้ง active / due / overdue"""
    rows = list_pawns(keyword, "active")
    for row in rows:
        row["display_status"] = get_pawn_display_status(row)
    return rows


def list_overdue_pawns(keyword=""):
    return [p for p in list_pawns_for_renew(keyword) if p["display_status"] == "overdue"]


def calculate_renewal_interest(principal, months, monthly_rate):
    principal = float(principal)
    months = int(months)
    monthly_rate = float(monthly_rate)
    if principal <= 0:
        raise ValueError("เงินต้นไม่ถูกต้อง")
    if months <= 0:
        raise ValueError("จำนวนเดือนต้องมากกว่า 0")
    interest = principal * (monthly_rate / 100.0) * months
    return round(interest, 2)


Q_CONTRACT_VAT_RATE = 7.0


def calculate_q_contract_vat(series_code, return_amount):
    """ผลตอบแทนของสัญญา Q เป็นราคารวม VAT จึงถอด VAT ออกจากยอดดังกล่าว"""
    gross_return = round(float(return_amount), 2)
    vat_rate = Q_CONTRACT_VAT_RATE if str(series_code or "P").upper() == "Q" else 0.0
    if vat_rate:
        vat_base = round(gross_return / (1.0 + vat_rate / 100.0), 2)
        vat_amount = round(gross_return - vat_base, 2)
    else:
        vat_base, vat_amount = gross_return, 0.0
    return {"vat_base": vat_base, "vat_rate": vat_rate, "vat_amount": vat_amount,
            "return_with_vat": gross_return}


def calculate_renewal_payment(ticket_id, months):
    pawn = get_pawn(int(ticket_id))
    if not pawn or pawn["status"] != "active":
        raise ValueError("ไม่พบตั๋วขายฝากที่ยังใช้งานอยู่")
    return_amount = calculate_renewal_interest(pawn["loan_amount"], months, pawn["monthly_interest_rate"])
    result = calculate_q_contract_vat(pawn.get("series_code"), return_amount)
    result.update({"interest_amount": return_amount, "total": result["return_with_vat"],
                   "series_code": str(pawn.get("series_code") or "P").upper()})
    return result


def calculate_redemption_amount(ticket_id, as_of=None):
    """คำนวณยอดไถ่ถอนตามกติกาหน้าร้าน

    - หากมีการชำระต่อดอกครอบคลุมวันไถ่แล้ว: ไม่คิดดอกเพิ่ม
    - ช่วงที่ต้องคิดดอกไม่เกิน 15 วัน: คิดครึ่งเดือน
    - เกิน 15 วัน: คิดเต็มเดือนและปัดเศษขึ้นทุก 30 วัน
    """
    as_of = _parse_date(as_of or date.today())
    pawn = get_pawn(int(ticket_id))
    if not pawn or pawn["status"] != "active":
        raise ValueError("ไม่พบตั๋วขายฝากที่ยังใช้งานอยู่")
    with get_connection() as conn:
        renewal = conn.execute(
            """SELECT * FROM pawn_renewals WHERE pawn_ticket_id=?
               AND renewal_status='completed' ORDER BY id DESC LIMIT 1""",
            (int(ticket_id),)
        ).fetchone()
    principal = float(pawn["loan_amount"])
    monthly_rate = float(pawn["monthly_interest_rate"])
    monthly_interest = principal * monthly_rate / 100.0

    if renewal and as_of <= _parse_date(renewal["new_due_date"]):
        result = {
            "principal": round(principal, 2), "interest": 0.0,
            "total": round(principal, 2), "days": 0, "charged_months": 0.0,
            "interest_start": renewal["previous_due_date"],
            "paid_through": renewal["new_due_date"],
            "reason": "ชำระผลตอบแทนครอบคลุมถึงวันไถ่แล้ว จึงชำระเฉพาะเงินต้น",
        }
        result.update(calculate_q_contract_vat(pawn.get("series_code"), 0.0))
        result["series_code"] = str(pawn.get("series_code") or "P").upper()
        return result

    interest_start = _parse_date(renewal["new_due_date"]) if renewal else _parse_date(pawn["opened_at"])
    days = max(1, (as_of - interest_start).days)
    charged_months = 0.5 if days <= 15 else float(ceil(days / 30.0))
    interest = round(monthly_interest * charged_months, 2)
    reason = "ไม่เกิน 15 วัน คิดผลตอบแทนครึ่งเดือน" if days <= 15 else f"เกิน 15 วัน คิดผลตอบแทน {charged_months:g} เดือน"
    vat = calculate_q_contract_vat(pawn.get("series_code"), interest)
    return {
        "principal": round(principal, 2), "interest": interest,
        "total": round(principal + vat["return_with_vat"], 2), "days": days,
        "charged_months": charged_months, "interest_start": interest_start.isoformat(),
        "paid_through": renewal["new_due_date"] if renewal else None, "reason": reason,
        "series_code": str(pawn.get("series_code") or "P").upper(), **vat,
    }


def renew_pawn(ticket_id, paid_amount, new_due_date=None, note="", created_by=None,
               renew_months=None, renewal_date=None):
    """ต่อดอกโดยคงตั๋วเดิมและบันทึกประวัติทุกครั้ง

    รองรับ callback รุ่นเก่าที่ส่ง new_due_date มาโดยตรง และรุ่นใหม่ที่ส่ง renew_months
    """
    paid_amount = float(paid_amount)
    if paid_amount < 0:
        raise ValueError("จำนวนเงินไม่ถูกต้อง")
    renewal_date = _parse_date(renewal_date or date.today())

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM pawn_tickets WHERE id=? AND status='active'",
            (int(ticket_id),)
        ).fetchone()
        if not row:
            raise ValueError("ไม่พบตั๋วขายฝากที่ยังใช้งานอยู่")

        previous_due = row["due_date"]
        if renew_months is not None:
            renew_months = int(renew_months)
            if renew_months <= 0:
                raise ValueError("กรุณาเลือกระยะเวลาต่อดอก")
            calculated_interest = calculate_renewal_interest(
                row["loan_amount"], renew_months, row["monthly_interest_rate"]
            )
            # การต่อดอกต้องต่อจากวันครบกำหนดเดิม ไม่ใช่วันที่มาชำระ
            # และใช้เดือนปฏิทินจริง (เช่น 31 ม.ค. + 1 เดือน = วันสุดท้าย ก.พ.)
            new_due = _add_months(_parse_date(previous_due), renew_months).isoformat()
        else:
            # backward compatibility
            if not new_due_date:
                raise ValueError("กรุณาระบุวันครบกำหนดใหม่")
            new_due = str(new_due_date)
            months_diff = max(1, round((_parse_date(new_due) - renewal_date).days / 30))
            renew_months = months_diff
            calculated_interest = calculate_renewal_interest(
                row["loan_amount"], renew_months, row["monthly_interest_rate"]
            )

        vat = calculate_q_contract_vat(row["series_code"], calculated_interest)
        expected_paid = vat["return_with_vat"]

        updated = conn.execute(
            "UPDATE pawn_tickets SET due_date=? WHERE id=? AND status='active'",
            (new_due, int(ticket_id))
        )
        if updated.rowcount != 1:
            raise RuntimeError("ไม่สามารถอัปเดตวันครบกำหนดของตั๋วขายฝากได้")
        tax_document_no=next_document_no(conn,"q_renew_tax","Q-RN-") if str(row["series_code"] or "P").upper()=="Q" else None
        renewal_cursor = conn.execute(
            """INSERT INTO pawn_renewals
               (pawn_ticket_id,renew_months,interest_amount,paid_amount,
                previous_due_date,new_due_date,note,created_by,
                vat_rate,vat_base,vat_amount,total_with_vat,tax_document_no)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (int(ticket_id), renew_months, calculated_interest, paid_amount,
             previous_due, new_due, note or "ต่อดอก", created_by,
             vat["vat_rate"], vat["vat_base"], vat["vat_amount"], expected_paid,tax_document_no)
        )
        conn.execute(
            """INSERT INTO pawn_transactions
               (pawn_ticket_id,transaction_type,amount,note,created_by,
                vat_rate,vat_base,vat_amount,total_with_vat,tax_document_no)
               VALUES (?,'renew',?,?,?,?,?,?,?,?)""",
            (int(ticket_id), paid_amount,
             f"ต่อดอก {renew_months} เดือน | {previous_due} -> {new_due}" + (f" | {note}" if note else ""),
             created_by, vat["vat_rate"], vat["vat_base"], vat["vat_amount"], expected_paid,tax_document_no)
        )
        conn.commit()

        # อ่านกลับจากฐานข้อมูลเพื่อยืนยันว่า due_date ถูกบันทึกจริง
        saved_due = conn.execute(
            "SELECT due_date FROM pawn_tickets WHERE id=?", (int(ticket_id),)
        ).fetchone()["due_date"]
        if saved_due != new_due:
            raise RuntimeError("บันทึกวันครบกำหนดใหม่ไม่สำเร็จ")

    return {
        "ticket_id": int(ticket_id),
        "renewal_id": renewal_cursor.lastrowid,
        "renew_months": renew_months,
        "interest_amount": calculated_interest,
        "paid_amount": paid_amount,
        **vat,
        "total_with_vat": expected_paid,
        "previous_due_date": previous_due,
        "new_due_date": saved_due,
    }


def get_pawn_renewals(ticket_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM pawn_renewals WHERE pawn_ticket_id=? ORDER BY id DESC",
            (int(ticket_id),)
        ).fetchall()
    return [dict(r) for r in rows]


def _required_reason(reason):
    reason = str(reason or "").strip()
    if not reason:
        raise ValueError("กรุณาระบุเหตุผลในการยกเลิกรายการ")
    return reason


def cancel_pawn(ticket_id, reason, voided_by):
    """ยกเลิกตั๋วที่ยัง active โดยเก็บตั๋วและธุรกรรมเดิมไว้ทั้งหมด"""
    reason = _required_reason(reason)
    with get_connection() as conn:
        row = conn.execute("SELECT status FROM pawn_tickets WHERE id=?", (int(ticket_id),)).fetchone()
        if not row or row["status"] != "active":
            raise ValueError("ยกเลิกได้เฉพาะตั๋วที่ยังใช้งานอยู่")
        active_renewals = conn.execute(
            "SELECT COUNT(*) FROM pawn_renewals WHERE pawn_ticket_id=? AND renewal_status='completed'",
            (int(ticket_id),)
        ).fetchone()[0]
        if active_renewals:
            raise ValueError("ตั๋วนี้มีประวัติต่อดอก กรุณาย้อนรายการต่อดอกทั้งหมดก่อน")
        conn.execute(
            """UPDATE pawn_tickets SET status='cancelled',cancelled_at=CURRENT_TIMESTAMP,
               cancelled_by=?,cancel_reason=? WHERE id=?""",
            (voided_by, reason, int(ticket_id))
        )
        conn.execute(
            """UPDATE pawn_transactions SET transaction_status='voided',voided_at=CURRENT_TIMESTAMP,
               voided_by=?,void_reason=? WHERE pawn_ticket_id=? AND transaction_type='pawn'
               AND transaction_status='completed'""",
            (voided_by, reason, int(ticket_id))
        )
        cursor = conn.execute(
            "INSERT INTO pawn_transactions (pawn_ticket_id,transaction_type,amount,note,created_by) VALUES (?,'cancel_pawn',0,?,?)",
            (int(ticket_id), reason, voided_by)
        )
        conn.commit()
        return {"ticket_id": int(ticket_id), "transaction_id": cursor.lastrowid, "action": "cancel_pawn"}


def void_latest_renewal(ticket_id, reason, voided_by):
    """ย้อนเฉพาะการต่อดอกล่าสุด แล้วคืน due_date เป็นค่าก่อนต่อ"""
    reason = _required_reason(reason)
    with get_connection() as conn:
        ticket = conn.execute("SELECT status,due_date FROM pawn_tickets WHERE id=?", (int(ticket_id),)).fetchone()
        if not ticket or ticket["status"] != "active":
            raise ValueError("ย้อนต่อดอกได้เฉพาะตั๋วที่ยังใช้งานอยู่")
        renewal = conn.execute(
            """SELECT * FROM pawn_renewals WHERE pawn_ticket_id=?
               AND renewal_status='completed' ORDER BY id DESC LIMIT 1""",
            (int(ticket_id),)
        ).fetchone()
        if not renewal:
            raise ValueError("ไม่พบรายการต่อดอกที่สามารถย้อนได้")
        if ticket["due_date"] != renewal["new_due_date"]:
            raise ValueError("วันครบกำหนดปัจจุบันไม่ตรงกับรายการต่อดอกล่าสุด กรุณาตรวจสอบประวัติ")
        conn.execute("UPDATE pawn_tickets SET due_date=? WHERE id=?", (renewal["previous_due_date"], int(ticket_id)))
        conn.execute(
            """UPDATE pawn_renewals SET renewal_status='voided',voided_at=CURRENT_TIMESTAMP,
               voided_by=?,void_reason=? WHERE id=?""", (voided_by, reason, renewal["id"])
        )
        tx = conn.execute(
            """SELECT id FROM pawn_transactions WHERE pawn_ticket_id=? AND transaction_type='renew'
               AND transaction_status='completed' ORDER BY id DESC LIMIT 1""", (int(ticket_id),)
        ).fetchone()
        if tx:
            conn.execute(
                """UPDATE pawn_transactions SET transaction_status='voided',voided_at=CURRENT_TIMESTAMP,
                   voided_by=?,void_reason=? WHERE id=?""", (voided_by, reason, tx["id"])
            )
        cursor = conn.execute(
            "INSERT INTO pawn_transactions (pawn_ticket_id,transaction_type,amount,note,created_by) VALUES (?,'void_renew',0,?,?)",
            (int(ticket_id), reason, voided_by)
        )
        conn.commit()
        return {"ticket_id": int(ticket_id), "transaction_id": cursor.lastrowid,
                "action": "void_renew", "restored_due_date": renewal["previous_due_date"]}


def void_redemption(ticket_id, reason, voided_by):
    """ย้อนการไถ่ถอนและเปิดตั๋วกลับเป็น active โดยไม่ลบธุรกรรมเดิม"""
    reason = _required_reason(reason)
    with get_connection() as conn:
        ticket = conn.execute("SELECT status FROM pawn_tickets WHERE id=?", (int(ticket_id),)).fetchone()
        if not ticket or ticket["status"] != "redeemed":
            raise ValueError("ย้อนการไถ่ถอนได้เฉพาะตั๋วสถานะไถ่ถอนแล้ว")
        tx = conn.execute(
            """SELECT id FROM pawn_transactions WHERE pawn_ticket_id=? AND transaction_type='redeem'
               AND transaction_status='completed' ORDER BY id DESC LIMIT 1""", (int(ticket_id),)
        ).fetchone()
        if not tx:
            raise ValueError("ไม่พบรายการไถ่ถอนที่สามารถย้อนได้")
        conn.execute(
            "UPDATE pawn_tickets SET status='active',redeemed_at=NULL,redeemed_amount=NULL WHERE id=?",
            (int(ticket_id),)
        )
        conn.execute(
            """UPDATE pawn_transactions SET transaction_status='voided',voided_at=CURRENT_TIMESTAMP,
               voided_by=?,void_reason=? WHERE id=?""", (voided_by, reason, tx["id"])
        )
        cursor = conn.execute(
            "INSERT INTO pawn_transactions (pawn_ticket_id,transaction_type,amount,note,created_by) VALUES (?,'void_redeem',0,?,?)",
            (int(ticket_id), reason, voided_by)
        )
        conn.commit()
        return {"ticket_id": int(ticket_id), "transaction_id": cursor.lastrowid, "action": "void_redeem"}


def forfeit_pawn(ticket_id, note="", created_by=None):
    """เปลี่ยน overdue -> forfeited โดยผู้ใช้ยืนยันเองเท่านั้น"""
    forfeit_pawns([ticket_id], note, created_by)


def forfeit_pawns(ticket_ids, note="", created_by=None):
    """ยืนยันตั๋วหลุดขายฝากหลายใบพร้อมกันแบบ atomic"""
    return forfeit_pawns_with_batch(ticket_ids, note, created_by)["ticket_count"]


def ensure_forfeit_batch_schema():
    with get_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS pawn_forfeit_batches(
            id INTEGER PRIMARY KEY AUTOINCREMENT,batch_no TEXT NOT NULL UNIQUE,
            ticket_count INTEGER NOT NULL DEFAULT 0,total_loan REAL NOT NULL DEFAULT 0,
            note TEXT,created_by INTEGER,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(created_by) REFERENCES users(id))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS pawn_forfeit_batch_tickets(
            batch_id INTEGER NOT NULL,pawn_ticket_id INTEGER NOT NULL UNIQUE,
            PRIMARY KEY(batch_id,pawn_ticket_id),
            FOREIGN KEY(batch_id) REFERENCES pawn_forfeit_batches(id),
            FOREIGN KEY(pawn_ticket_id) REFERENCES pawn_tickets(id))""")
        conn.commit()


def forfeit_pawns_with_batch(ticket_ids, note="", created_by=None):
    """ยืนยันหลายตั๋วเป็นชุดเดียว และคืนเลขชุดสำหรับจัดทำเอกสาร"""
    ensure_forfeit_batch_schema()
    ids = []
    for value in ticket_ids:
        ticket_id = int(value)
        if ticket_id not in ids:
            ids.append(ticket_id)
    if not ids:
        raise ValueError("กรุณาเลือกตั๋วขายฝากอย่างน้อย 1 รายการ")
    with get_connection() as conn:
        rows = []
        for ticket_id in ids:
            row = conn.execute(
                "SELECT * FROM pawn_tickets WHERE id=? AND status='active'", (ticket_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"ตั๋วรหัส {ticket_id} ไม่ได้อยู่ในสถานะใช้งาน")
            if get_pawn_display_status(dict(row)) != "overdue":
                raise ValueError(f"ตั๋ว {row['ticket_no']} ยังไม่เกินกำหนด")
            rows.append(row)
        clean_note = str(note or "ยืนยันหลุดขายฝาก").strip()
        next_id = conn.execute("SELECT COALESCE(MAX(id),0)+1 n FROM pawn_forfeit_batches").fetchone()["n"]
        batch_no = f"FF{int(next_id):06d}"
        total_loan = sum(float(row["loan_amount"] or 0) for row in rows)
        cursor = conn.execute(
            """INSERT INTO pawn_forfeit_batches(batch_no,ticket_count,total_loan,note,created_by)
               VALUES (?,?,?,?,?)""", (batch_no, len(rows), total_loan, clean_note, created_by)
        )
        batch_id = cursor.lastrowid
        for row in rows:
            conn.execute(
                """UPDATE pawn_tickets SET status='forfeited', forfeited_at=CURRENT_TIMESTAMP,
                   forfeited_by=?, forfeit_note=? WHERE id=?""",
                (created_by, clean_note, row["id"])
            )
            conn.execute(
                """INSERT INTO pawn_transactions
                   (pawn_ticket_id,transaction_type,amount,note,created_by)
                   VALUES (?,'forfeit',0,?,?)""",
                (row["id"], clean_note, created_by)
            )
            conn.execute(
                "INSERT INTO pawn_forfeit_batch_tickets(batch_id,pawn_ticket_id) VALUES (?,?)",
                (batch_id, row["id"])
            )
        conn.commit()
    return {"batch_id": batch_id, "batch_no": batch_no, "ticket_count": len(ids),
            "total_loan": round(total_loan, 2)}


def get_forfeit_batch(batch_id):
    ensure_forfeit_batch_schema()
    with get_connection() as conn:
        batch = conn.execute("""SELECT b.*,u.full_name created_by_name FROM pawn_forfeit_batches b
            LEFT JOIN users u ON u.id=b.created_by WHERE b.id=?""", (int(batch_id),)).fetchone()
        if not batch: return None
        tickets = conn.execute("""SELECT p.*,c.customer_code,c.first_name,c.last_name,c.citizen_id,c.phone
            FROM pawn_forfeit_batch_tickets bt JOIN pawn_tickets p ON p.id=bt.pawn_ticket_id
            JOIN customers c ON c.id=p.customer_id WHERE bt.batch_id=? ORDER BY p.ticket_no""",
            (int(batch_id),)).fetchall()
        result = dict(batch); result["tickets"] = []
        for ticket in tickets:
            entry = dict(ticket)
            entry["items"] = [dict(x) for x in conn.execute(
                "SELECT * FROM pawn_items WHERE pawn_ticket_id=? ORDER BY item_no", (ticket["id"],)
            ).fetchall()]
            result["tickets"].append(entry)
    return result


def list_forfeit_batches():
    ensure_forfeit_batch_schema()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM pawn_forfeit_batches ORDER BY id DESC").fetchall()
    return [dict(x) for x in rows]


def list_pawn_history(ticket_id):
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id,transaction_type,amount,transaction_at,note,created_by,
                      transaction_status,voided_at,voided_by,void_reason
               FROM pawn_transactions WHERE pawn_ticket_id=? ORDER BY id""",
            (int(ticket_id),)
        ).fetchall()
    return [dict(r) for r in rows]

def redeem_pawn(ticket_id, paid_amount, created_by=None, note=""):
    paid_amount=float(paid_amount)
    if paid_amount<0: raise ValueError("จำนวนเงินไม่ถูกต้อง")
    calculation = calculate_redemption_amount(ticket_id)
    with get_connection() as conn:
        row=conn.execute("SELECT * FROM pawn_tickets WHERE id=? AND status='active'",(ticket_id,)).fetchone()
        if not row: raise ValueError("ไม่พบตั๋วขายฝากที่ยังใช้งานอยู่")
        conn.execute("UPDATE pawn_tickets SET status='redeemed',redeemed_at=CURRENT_TIMESTAMP,redeemed_amount=? WHERE id=?",(paid_amount,ticket_id))
        tx_note = "ไถ่ถอน" + (f" | {str(note).strip()}" if str(note or "").strip() else "")
        tax_document_no=next_document_no(conn,"q_redeem_tax","Q-RD-") if calculation["series_code"]=="Q" else None
        cursor=conn.execute(
            """INSERT INTO pawn_transactions
               (pawn_ticket_id,transaction_type,amount,note,created_by,
                vat_rate,vat_base,vat_amount,total_with_vat,tax_document_no)
               VALUES (?,'redeem',?,?,?,?,?,?,?,?)""",
            (ticket_id,paid_amount,tx_note,created_by,calculation["vat_rate"],
             calculation["vat_base"],calculation["vat_amount"],calculation["total"],tax_document_no)
        ); conn.commit()
        return {"ticket_id": int(ticket_id), "transaction_id": cursor.lastrowid,
                "paid_amount": paid_amount, **calculation}


def get_active_counts():
    with get_connection() as conn:
        active=conn.execute("SELECT COUNT(*) FROM pawn_tickets WHERE status='active'").fetchone()[0]
        total=conn.execute("SELECT COALESCE(SUM(loan_amount),0) FROM pawn_tickets WHERE status='active'").fetchone()[0]
    return active,float(total)
