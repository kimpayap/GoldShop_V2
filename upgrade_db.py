from database.database import get_connection

with get_connection() as conn:
    cols = {r['name'] for r in conn.execute('PRAGMA table_info(customers)').fetchall()}
    if 'identity_type' not in cols:
        conn.execute("ALTER TABLE customers ADD COLUMN identity_type TEXT DEFAULT 'ไม่มีเอกสาร'")
        print('เพิ่ม column: customers.identity_type')
    conn.commit()
print('Customer database upgrade OK')
