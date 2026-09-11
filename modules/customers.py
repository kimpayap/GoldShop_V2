from database.database import get_connection


def _s(v):
    return (v or '').strip()


def next_customer_code():
    with get_connection() as conn:
        row = conn.execute('SELECT customer_code FROM customers ORDER BY id DESC LIMIT 1').fetchone()
    if not row:
        return 'C000001'
    try:
        return f"C{int((row['customer_code'] or 'C0')[1:]) + 1:06d}"
    except (ValueError, TypeError):
        return 'C000001'


def _check_cid(conn, citizen_id, exclude_id=None):
    citizen_id = _s(citizen_id)
    if not citizen_id:
        return
    if exclude_id is None:
        row = conn.execute('SELECT id FROM customers WHERE citizen_id=? LIMIT 1', (citizen_id,)).fetchone()
    else:
        row = conn.execute('SELECT id FROM customers WHERE citizen_id=? AND id!=? LIMIT 1', (citizen_id, exclude_id)).fetchone()
    if row:
        raise ValueError('เลขบัตรประชาชนนี้มีอยู่ในระบบแล้ว')


def add_customer(first_name, last_name, citizen_id='', phone='', address='', note='',
                 thai_name='', english_name='', birth_date='', gender='', card_issuer='',
                 card_issue_date='', card_expire_date='', photo_path='', identity_type='ไม่มีเอกสาร'):
    first_name, last_name = _s(first_name), _s(last_name)
    if not first_name or not last_name:
        raise ValueError('กรุณากรอกชื่อและนามสกุล')
    with get_connection() as conn:
        _check_cid(conn, citizen_id)
        code = next_customer_code()
        cur = conn.execute('''INSERT INTO customers
            (customer_code,first_name,last_name,citizen_id,phone,address,note,
             thai_name,english_name,birth_date,gender,card_issuer,card_issue_date,
             card_expire_date,photo_path,identity_type)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (code, first_name, last_name, _s(citizen_id), _s(phone), _s(address), _s(note),
             _s(thai_name), _s(english_name), _s(birth_date), _s(gender), _s(card_issuer),
             _s(card_issue_date), _s(card_expire_date), _s(photo_path), _s(identity_type) or 'ไม่มีเอกสาร'))
        conn.commit()
        return cur.lastrowid, code


def update_customer(customer_id, first_name, last_name, citizen_id='', phone='', address='', note='',
                    thai_name='', english_name='', birth_date='', gender='', card_issuer='',
                    card_issue_date='', card_expire_date='', photo_path='', identity_type='ไม่มีเอกสาร'):
    first_name, last_name = _s(first_name), _s(last_name)
    if not first_name or not last_name:
        raise ValueError('กรุณากรอกชื่อและนามสกุล')
    with get_connection() as conn:
        _check_cid(conn, citizen_id, customer_id)
        conn.execute('''UPDATE customers SET first_name=?,last_name=?,citizen_id=?,phone=?,address=?,note=?,
            thai_name=?,english_name=?,birth_date=?,gender=?,card_issuer=?,card_issue_date=?,card_expire_date=?,
            photo_path=?,identity_type=?,updated_at=CURRENT_TIMESTAMP WHERE id=?''',
            (first_name,last_name,_s(citizen_id),_s(phone),_s(address),_s(note),_s(thai_name),_s(english_name),
             _s(birth_date),_s(gender),_s(card_issuer),_s(card_issue_date),_s(card_expire_date),_s(photo_path),
             _s(identity_type) or 'ไม่มีเอกสาร',customer_id))
        conn.commit()


def get_customer(customer_id):
    with get_connection() as conn:
        row = conn.execute('SELECT * FROM customers WHERE id=?', (customer_id,)).fetchone()
    return dict(row) if row else None


def find_customer_by_citizen_id(citizen_id):
    citizen_id = _s(citizen_id)
    if not citizen_id:
        return None
    with get_connection() as conn:
        row = conn.execute('SELECT * FROM customers WHERE citizen_id=? LIMIT 1', (citizen_id,)).fetchone()
    return dict(row) if row else None


def search_customers(keyword=''):
    keyword = _s(keyword)
    with get_connection() as conn:
        if keyword:
            q = f'%{keyword}%'
            rows = conn.execute('''SELECT * FROM customers WHERE customer_code LIKE ? OR first_name LIKE ?
                OR last_name LIKE ? OR citizen_id LIKE ? OR phone LIKE ? OR thai_name LIKE ? OR english_name LIKE ?
                ORDER BY id DESC''', (q,q,q,q,q,q,q)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM customers ORDER BY id DESC').fetchall()
    return [dict(r) for r in rows]
