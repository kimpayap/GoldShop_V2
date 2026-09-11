from datetime import date,datetime,timedelta
from pathlib import Path
import hashlib,hmac,json,os,secrets,sqlite3

from database.database import get_connection,DB_PATH
from modules.document_numbers import next_document_no


PERMISSIONS={
    "transactions":"ทำรายการทั่วไป","view_cost":"ดูต้นทุนและกำไร","cancel_transaction":"ยกเลิกรายการ",
    "adjust_stock":"ปรับปรุงสต็อก","close_shift":"ปิดกะ/ปิดยอด","manage_users":"จัดการผู้ใช้และสิทธิ์",
    "backup":"สำรองข้อมูล","restore":"กู้คืนข้อมูล","view_audit":"ดูประวัติการใช้งาน","settings":"ตั้งค่าระบบ",
}
ROLE_DEFAULTS={
    "admin":set(PERMISSIONS),"owner":set(PERMISSIONS),"manager":set(PERMISSIONS)-{"restore","manage_users"},
    "accounting":{"view_cost","close_shift","view_audit","transactions"},"staff":{"transactions"},
}

def hash_password(password):
    salt=secrets.token_hex(16);digest=hashlib.pbkdf2_hmac('sha256',str(password).encode(),bytes.fromhex(salt),200000).hex();return f"pbkdf2_sha256${salt}${digest}"

def verify_password(password,stored):
    stored=str(stored or '')
    if not stored.startswith('pbkdf2_sha256$'):return hmac.compare_digest(str(password),stored)
    try:
        _,salt,expected=stored.split('$',2);actual=hashlib.pbkdf2_hmac('sha256',str(password).encode(),bytes.fromhex(salt),200000).hex();return hmac.compare_digest(actual,expected)
    except Exception:return False


def ensure_control_schema():
    with get_connection() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS role_permissions(role TEXT NOT NULL,permission_code TEXT NOT NULL,allowed INTEGER NOT NULL DEFAULT 1,PRIMARY KEY(role,permission_code))""")
        c.execute("""CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY AUTOINCREMENT,event_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,user_id INTEGER,username TEXT,action TEXT NOT NULL,module TEXT NOT NULL,record_type TEXT,record_id TEXT,description TEXT,old_value TEXT,new_value TEXT,reason TEXT,computer_name TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS approval_logs(id INTEGER PRIMARY KEY AUTOINCREMENT,requested_by INTEGER,approved_by INTEGER,permission_code TEXT NOT NULL,action TEXT NOT NULL,record_type TEXT,record_id TEXT,reason TEXT NOT NULL,approved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS login_attempts(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL,success INTEGER NOT NULL,attempted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,computer_name TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS database_backups(id INTEGER PRIMARY KEY AUTOINCREMENT,file_path TEXT NOT NULL,file_name TEXT NOT NULL,file_size INTEGER NOT NULL,checksum TEXT NOT NULL,backup_type TEXT NOT NULL,created_by INTEGER,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,status TEXT NOT NULL DEFAULT 'verified')""")
        c.execute("""CREATE TABLE IF NOT EXISTS cash_shifts(id INTEGER PRIMARY KEY AUTOINCREMENT,shift_no TEXT NOT NULL UNIQUE,shift_date TEXT NOT NULL,opened_by INTEGER NOT NULL,opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,opening_cash REAL NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'open',expected_json TEXT,actual_json TEXT,difference_json TEXT,note TEXT,closed_by INTEGER,approved_by INTEGER,closed_at TEXT)""")
        for role,permissions in ROLE_DEFAULTS.items():
            for code in PERMISSIONS:c.execute("INSERT OR IGNORE INTO role_permissions(role,permission_code,allowed) VALUES (?,?,?)",(role,code,1 if code in permissions else 0))
        c.commit()


def ensure_audit_triggers():
    """Record core business inserts and status changes even when a screen forgets to log them."""
    ensure_control_schema()
    definitions=(("pawn_tickets","ticket_no","created_by"),("pawn_transactions","id","created_by"),("gold_sales","sale_no","created_by"),("old_gold_receipts","receipt_no","created_by"),("inventory_items","item_code","created_by"),("old_gold_items","item_code",None))
    with get_connection() as c:
        tables={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table,record,user_col in definitions:
            if table not in tables:continue
            user_new=f"NEW.{user_col}" if user_col else "NULL";username=f"(SELECT username FROM users WHERE id={user_new})" if user_col else "NULL"
            c.execute(f"""CREATE TRIGGER IF NOT EXISTS audit_{table}_insert AFTER INSERT ON {table} BEGIN
                INSERT INTO audit_logs(user_id,username,action,module,record_type,record_id,description)
                VALUES ({user_new},{username},'create','{table}','{table}',NEW.{record},'สร้างรายการ'); END""")
            if table in {"pawn_tickets","gold_sales","old_gold_receipts","inventory_items","old_gold_items"}:
                c.execute(f"""CREATE TRIGGER IF NOT EXISTS audit_{table}_status AFTER UPDATE OF status ON {table} WHEN OLD.status<>NEW.status BEGIN
                    INSERT INTO audit_logs(user_id,username,action,module,record_type,record_id,description,old_value,new_value)
                    VALUES ({user_new},{username},'status_change','{table}','{table}',NEW.{record},'เปลี่ยนสถานะ',OLD.status,NEW.status); END""")
        c.commit()


def log_audit(action,module,user=None,record_type="",record_id="",description="",old_value=None,new_value=None,reason=""):
    ensure_control_schema();user=user or {}
    with get_connection() as c:c.execute("""INSERT INTO audit_logs(user_id,username,action,module,record_type,record_id,description,old_value,new_value,reason,computer_name) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",(user.get('id'),user.get('username'),str(action),str(module),str(record_type),str(record_id or ''),str(description),json.dumps(old_value,ensure_ascii=False,default=str) if old_value is not None else None,json.dumps(new_value,ensure_ascii=False,default=str) if new_value is not None else None,str(reason or ''),os.environ.get('COMPUTERNAME') or os.environ.get('HOSTNAME') or 'local'));c.commit()


def has_permission(user,permission):
    ensure_control_schema();role=str((user or {}).get('role','staff')).lower()
    with get_connection() as c:row=c.execute("SELECT allowed FROM role_permissions WHERE role=? AND permission_code=?",(role,permission)).fetchone()
    return bool(row and row[0])


def verify_approver(username,password,permission,requested_by=None,action="",record_type="",record_id="",reason=""):
    if not str(reason or '').strip():raise ValueError("กรุณาระบุเหตุผลที่ขออนุมัติ")
    ensure_control_schema()
    with get_connection() as c:
        user=c.execute("SELECT id,username,password,full_name,role FROM users WHERE username=? AND active=1",(str(username).strip(),)).fetchone()
        if not user or not verify_password(password,user['password']):raise ValueError("ชื่อผู้อนุมัติหรือรหัสผ่านไม่ถูกต้อง")
        if not str(user['password']).startswith('pbkdf2_sha256$'):c.execute("UPDATE users SET password=? WHERE id=?",(hash_password(password),user['id']));c.commit()
    approver={k:user[k] for k in ('id','username','full_name','role')}
    if not has_permission(approver,permission):raise ValueError("ผู้ใช้นี้ไม่มีสิทธิ์อนุมัติรายการ")
    if requested_by and int(requested_by)==approver['id']:raise ValueError("ผู้ทำรายการและผู้อนุมัติต้องเป็นคนละคน")
    with get_connection() as c:cur=c.execute("INSERT INTO approval_logs(requested_by,approved_by,permission_code,action,record_type,record_id,reason) VALUES (?,?,?,?,?,?,?)",(requested_by,approver['id'],permission,action,record_type,str(record_id or ''),str(reason)));c.commit()
    log_audit("approve","security",approver,record_type,record_id,action,reason=reason);return {**approver,"approval_id":cur.lastrowid}


def list_audit_logs(date_from,date_to,keyword=""):
    ensure_control_schema();params=[date_from,date_to];sql="SELECT * FROM audit_logs WHERE date(event_at) BETWEEN ? AND ?"
    if keyword:sql+=" AND (username LIKE ? OR action LIKE ? OR module LIKE ? OR description LIKE ? OR record_id LIKE ?)";params += [f"%{keyword}%"]*5
    with get_connection() as c:rows=c.execute(sql+" ORDER BY id DESC LIMIT 2000",params).fetchall()
    return [dict(x) for x in rows]


def list_users():
    ensure_control_schema()
    with get_connection() as c:rows=c.execute("SELECT id,username,full_name,role,active,created_at FROM users ORDER BY username").fetchall()
    return [dict(x) for x in rows]


def save_user(user_id,username,password,full_name,role,active,operator):
    if not has_permission(operator,"manage_users"):raise PermissionError("ไม่มีสิทธิ์จัดการผู้ใช้")
    username=str(username).strip();full_name=str(full_name).strip();role=str(role).lower()
    if not username or not full_name or (not user_id and not password):raise ValueError("กรุณากรอกชื่อผู้ใช้ ชื่อพนักงาน และรหัสผ่าน")
    with get_connection() as c:
        old=dict(c.execute("SELECT * FROM users WHERE id=?",(int(user_id),)).fetchone()) if user_id else None
        if user_id:
            if password:c.execute("UPDATE users SET username=?,password=?,full_name=?,role=?,active=? WHERE id=?",(username,hash_password(password),full_name,role,int(bool(active)),int(user_id)))
            else:c.execute("UPDATE users SET username=?,full_name=?,role=?,active=? WHERE id=?",(username,full_name,role,int(bool(active)),int(user_id)))
            saved=int(user_id)
        else:saved=c.execute("INSERT INTO users(username,password,full_name,role,active) VALUES (?,?,?,?,?)",(username,hash_password(password),full_name,role,int(bool(active)))).lastrowid
        c.commit()
    log_audit("update" if user_id else "create","users",operator,"user",saved,"บันทึกผู้ใช้",old,{"username":username,"full_name":full_name,"role":role,"active":bool(active)});return saved


def set_role_permission(role,permission,allowed,operator):
    if not has_permission(operator,"manage_users"):raise PermissionError("ไม่มีสิทธิ์จัดการสิทธิ์")
    with get_connection() as c:c.execute("INSERT INTO role_permissions(role,permission_code,allowed) VALUES (?,?,?) ON CONFLICT(role,permission_code) DO UPDATE SET allowed=excluded.allowed",(role,permission,int(bool(allowed))));c.commit()
    log_audit("permission","security",operator,"role",role,f"{permission}={bool(allowed)}")


def get_role_permissions(role):
    ensure_control_schema()
    with get_connection() as c:rows=c.execute("SELECT permission_code,allowed FROM role_permissions WHERE role=?",(role,)).fetchall()
    return {x['permission_code']:bool(x['allowed']) for x in rows}


def _backup_folder():
    if os.name=='nt':base=Path(os.environ.get('APPDATA',Path.home()))/'GoldShop'
    elif os.sys.platform=='darwin':base=Path.home()/'Library'/'Application Support'/'GoldShop'
    else:base=Path.home()/'.local'/'share'/'GoldShop'
    folder=base/'Backups'
    try:folder.mkdir(parents=True,exist_ok=True)
    except OSError:
        folder=Path(DB_PATH).parent/'Backups';folder.mkdir(parents=True,exist_ok=True)
    return folder


def _checksum(path):
    digest=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def create_backup(user=None,folder=None,backup_type="manual"):
    ensure_control_schema()
    if backup_type=='manual' and not has_permission(user,'backup'):raise PermissionError("ไม่มีสิทธิ์สำรองข้อมูล")
    if not folder:
        with get_connection() as c:setting=c.execute("SELECT setting_value FROM app_settings WHERE setting_key='backup_folder'").fetchone()
        folder=setting[0] if setting and setting[0] else None
    target_folder=Path(folder).expanduser() if folder else _backup_folder();target_folder.mkdir(parents=True,exist_ok=True);stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f');target=target_folder/f"GoldShop_{stamp}.db"
    with get_connection() as source,sqlite3.connect(target) as destination:source.backup(destination)
    with sqlite3.connect(target) as check:
        if check.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise RuntimeError("ไฟล์สำรองไม่ผ่านการตรวจสอบ")
    checksum=_checksum(target);size=target.stat().st_size
    with get_connection() as c:c.execute("INSERT INTO database_backups(file_path,file_name,file_size,checksum,backup_type,created_by) VALUES (?,?,?,?,?,?)",(str(target),target.name,size,checksum,backup_type,(user or {}).get('id')));c.commit()
    log_audit("backup","database",user,"database","",f"สำรองข้อมูล {target.name}",new_value={"path":str(target),"checksum":checksum});return {"path":str(target),"size":size,"checksum":checksum}


def save_backup_settings(folder,retention_days,user):
    if not has_permission(user,"backup"):raise PermissionError("ไม่มีสิทธิ์ตั้งค่าการสำรองข้อมูล")
    days=int(retention_days)
    if days<1:raise ValueError("จำนวนวันเก็บไฟล์ต้องมากกว่า 0")
    target=Path(folder).expanduser();target.mkdir(parents=True,exist_ok=True)
    with get_connection() as c:
        for key,value in (("backup_folder",str(target)),("backup_retention_days",str(days))):c.execute("INSERT INTO app_settings(setting_key,setting_value) VALUES (?,?) ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value",(key,value))
        c.commit()
    log_audit("settings","backup",user,description="ตั้งค่าการสำรองข้อมูล",new_value={"folder":str(target),"retention_days":days})


def get_backup_settings():
    ensure_control_schema()
    with get_connection() as c:rows={x[0]:x[1] for x in c.execute("SELECT setting_key,setting_value FROM app_settings WHERE setting_key IN ('backup_folder','backup_retention_days')")}
    return {"folder":rows.get("backup_folder",str(_backup_folder())),"retention_days":int(rows.get("backup_retention_days","30"))}


def list_backups():
    ensure_control_schema()
    with get_connection() as c:rows=c.execute("SELECT b.*,u.full_name created_name FROM database_backups b LEFT JOIN users u ON u.id=b.created_by ORDER BY b.id DESC LIMIT 500").fetchall()
    return [dict(x) for x in rows]


def automatic_daily_backup(user=None):
    ensure_control_schema()
    with get_connection() as c:exists=c.execute("SELECT 1 FROM database_backups WHERE backup_type='automatic' AND date(created_at)=CURRENT_DATE AND status='verified'").fetchone()
    result=None if exists else create_backup(user,backup_type="automatic")
    settings=get_backup_settings();cutoff=(datetime.now()-timedelta(days=settings['retention_days'])).isoformat(sep=' ')
    with get_connection() as c:
        expired=c.execute("SELECT id,file_path FROM database_backups WHERE backup_type='automatic' AND created_at<? AND status='verified'",(cutoff,)).fetchall()
        for row in expired:
            path=Path(row['file_path'])
            if path.is_file() and path.parent==Path(settings['folder']).expanduser():path.unlink();c.execute("UPDATE database_backups SET status='expired' WHERE id=?",(row['id'],))
        c.commit()
    return result


def verify_backup(path):
    source=Path(path)
    if not source.is_file():raise ValueError("ไม่พบไฟล์สำรอง")
    with sqlite3.connect(f"file:{source}?mode=ro",uri=True) as c:
        if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise ValueError("ฐานข้อมูลสำรองเสียหาย")
        required={"users","customers","gold_prices"};tables={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required<=tables:raise ValueError("ไฟล์นี้ไม่ใช่ฐานข้อมูล GoldShop ที่สมบูรณ์")
    return {"path":str(source),"size":source.stat().st_size,"checksum":_checksum(source)}


def restore_backup(path,user,approver,reason):
    if not has_permission(approver,"restore"):raise PermissionError("ผู้อนุมัติไม่มีสิทธิ์กู้คืนข้อมูล")
    verified=verify_backup(path);safety=create_backup(user,backup_type="pre_restore")
    source=sqlite3.connect(path);target=sqlite3.connect(DB_PATH)
    try:source.backup(target)
    finally:source.close();target.close()
    ensure_control_schema()
    with get_connection() as c:c.execute("INSERT INTO database_backups(file_path,file_name,file_size,checksum,backup_type,created_by) VALUES (?,?,?,?,?,?)",(safety['path'],Path(safety['path']).name,safety['size'],safety['checksum'],'pre_restore',user.get('id')));c.commit()
    log_audit("restore","database",user,"database","",f"กู้คืนจาก {Path(path).name}",old_value={"safety_backup":safety['path']},new_value=verified,reason=reason);return {"restored":verified,"safety":safety}


def open_shift(opening_cash,user,note=""):
    ensure_control_schema();amount=float(opening_cash)
    if amount<0:raise ValueError("เงินสดต้นกะต้องไม่ติดลบ")
    with get_connection() as c:
        existing=c.execute("SELECT * FROM cash_shifts WHERE shift_date=CURRENT_DATE AND status='open' ORDER BY id DESC LIMIT 1").fetchone()
        if existing:return dict(existing)
        no=next_document_no(c,"cash_shift","SHIFT");cur=c.execute("INSERT INTO cash_shifts(shift_no,shift_date,opened_by,opening_cash,note) VALUES (?,CURRENT_DATE,?,?,?)",(no,user.get('id'),amount,str(note)));c.commit()
    log_audit("open_shift","cash",user,"cash_shift",cur.lastrowid,f"เปิดกะ {no}",new_value={"opening_cash":amount});return get_shift(cur.lastrowid)


def get_shift(shift_id=None):
    ensure_control_schema()
    with get_connection() as c:
        row=c.execute("SELECT s.*,u.full_name opened_name,cu.full_name closed_name,au.full_name approved_name FROM cash_shifts s LEFT JOIN users u ON u.id=s.opened_by LEFT JOIN users cu ON cu.id=s.closed_by LEFT JOIN users au ON au.id=s.approved_by WHERE s.id=?",(int(shift_id),)).fetchone() if shift_id else c.execute("SELECT * FROM cash_shifts WHERE shift_date=CURRENT_DATE ORDER BY id DESC LIMIT 1").fetchone()
    result=dict(row) if row else None
    if result:
        for key in ('expected_json','actual_json','difference_json'):result[key[:-5]]=json.loads(result[key] or '{}')
    return result


def calculate_shift(shift_id):
    from modules.operations_control import ensure_operations_schema
    ensure_operations_schema()
    shift=get_shift(shift_id)
    if not shift:raise ValueError("ไม่พบกะ")
    with get_connection() as c:
        rows=[]
        queries=[("SELECT payment_method,amount_paid amount FROM gold_sales WHERE sale_date=? AND status='completed'",(shift['shift_date'],),1),
          ("SELECT payment_method,-paid_amount amount FROM old_gold_receipts r WHERE receipt_date=? AND status='completed' AND NOT EXISTS(SELECT 1 FROM gold_exchanges e WHERE e.old_gold_receipt_id=r.id AND e.status='completed')",(shift['shift_date'],),1),
          ("SELECT settlement_method payment_method,difference_amount amount FROM gold_exchanges WHERE date(created_at)=? AND status='completed' AND difference_amount<0",(shift['shift_date'],),1),
          ("SELECT 'เงินสด' payment_method,-loan_amount amount FROM pawn_tickets WHERE date(opened_at)=? AND status<>'cancelled'",(shift['shift_date'],),1),
          ("SELECT 'เงินสด' payment_method,amount FROM pawn_transactions WHERE date(transaction_at)=? AND transaction_status='completed' AND transaction_type IN ('renew','redeem')",(shift['shift_date'],),1)]
        for sql,args,_ in queries:rows.extend(dict(x) for x in c.execute(sql,args))
    totals={"เงินสด":float(shift['opening_cash']),"โอนเงิน":0.0,"บัตรเครดิต":0.0,"อื่น ๆ":0.0}
    for x in rows:
        method=x['payment_method'] if x['payment_method'] in totals else "อื่น ๆ";totals[method]+=float(x['amount'] or 0)
    return {k:round(v,2) for k,v in totals.items()}


def close_shift(shift_id,actual,user,approver,note=""):
    shift=get_shift(shift_id)
    if not shift or shift['status']!='open':raise ValueError("กะนี้ปิดแล้วหรือไม่พบข้อมูล")
    if not has_permission(approver,"close_shift"):raise PermissionError("ผู้อนุมัติไม่มีสิทธิ์ปิดกะ")
    expected=calculate_shift(shift_id);actual={k:round(float(actual.get(k,0)),2) for k in expected};difference={k:round(actual[k]-expected[k],2) for k in expected}
    with get_connection() as c:c.execute("UPDATE cash_shifts SET status='closed',expected_json=?,actual_json=?,difference_json=?,note=?,closed_by=?,approved_by=?,closed_at=CURRENT_TIMESTAMP WHERE id=?",(json.dumps(expected,ensure_ascii=False),json.dumps(actual,ensure_ascii=False),json.dumps(difference,ensure_ascii=False),str(note),user.get('id'),approver.get('id'),int(shift_id)));c.commit()
    log_audit("close_shift","cash",user,"cash_shift",shift_id,f"ปิดกะ {shift['shift_no']}",new_value={"expected":expected,"actual":actual,"difference":difference},reason=note);return get_shift(shift_id)


def list_shifts(date_from,date_to):
    ensure_control_schema()
    with get_connection() as c:rows=c.execute("""SELECT s.*,u.full_name opened_name,cu.full_name closed_name,au.full_name approved_name FROM cash_shifts s
        LEFT JOIN users u ON u.id=s.opened_by LEFT JOIN users cu ON cu.id=s.closed_by LEFT JOIN users au ON au.id=s.approved_by
        WHERE shift_date BETWEEN ? AND ? ORDER BY id DESC""",(date_from,date_to)).fetchall()
    return [dict(x) for x in rows]


ensure_control_schema()
