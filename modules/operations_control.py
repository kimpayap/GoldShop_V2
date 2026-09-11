from datetime import date,datetime
from database.database import get_connection
from modules.document_numbers import next_document_no
from modules.gold_exchange import ensure_exchange_schema
from modules.old_gold import ensure_old_gold_schema,cancel_old_gold_receipt
from modules.sales import ensure_sales_schema,cancel_gold_sale
from modules.stock import ensure_stock_schema

def ensure_operations_schema():
    ensure_exchange_schema();ensure_old_gold_schema();ensure_sales_schema();ensure_stock_schema()
    with get_connection() as c:
        exchange_cols={r[1] for r in c.execute("PRAGMA table_info(gold_exchanges)").fetchall()}
        for col,definition in (("status","TEXT NOT NULL DEFAULT 'completed'"),("cancelled_at","TEXT"),("cancelled_by","INTEGER"),("cancel_reason","TEXT")):
            if col not in exchange_cols:c.execute(f"ALTER TABLE gold_exchanges ADD COLUMN {col} {definition}")
        c.execute("""CREATE TABLE IF NOT EXISTS exchange_workflows(
            id INTEGER PRIMARY KEY AUTOINCREMENT,workflow_no TEXT NOT NULL UNIQUE,status TEXT NOT NULL DEFAULT 'draft',
            old_gold_receipt_id INTEGER,gold_sale_id INTEGER,gold_exchange_id INTEGER,current_step TEXT NOT NULL DEFAULT 'old_gold',
            note TEXT,created_by INTEGER,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            cancelled_at TEXT,cancelled_by INTEGER,cancel_reason TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS tax_adjustments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,document_no TEXT NOT NULL UNIQUE,adjustment_type TEXT NOT NULL,
            original_document_type TEXT NOT NULL,original_document_id INTEGER NOT NULL,original_document_no TEXT NOT NULL,
            document_date TEXT NOT NULL,reason TEXT NOT NULL,amount_ex_vat REAL NOT NULL,vat_amount REAL NOT NULL,
            total_amount REAL NOT NULL,status TEXT NOT NULL DEFAULT 'completed',created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS old_gold_bulk_sales(
            id INTEGER PRIMARY KEY AUTOINCREMENT,sale_no TEXT NOT NULL UNIQUE,sale_date TEXT NOT NULL,buyer_name TEXT NOT NULL,
            buyer_tax_id TEXT,payment_method TEXT NOT NULL,total_weight REAL NOT NULL,total_cost REAL NOT NULL,
            sale_amount REAL NOT NULL,notes TEXT,created_by INTEGER,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS old_gold_bulk_sale_items(
            sale_id INTEGER NOT NULL,old_gold_item_id INTEGER NOT NULL UNIQUE,sale_allocated REAL NOT NULL,
            PRIMARY KEY(sale_id,old_gold_item_id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS stock_counts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,count_no TEXT NOT NULL UNIQUE,count_type TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open',
            count_date TEXT NOT NULL,location TEXT,expected_count INTEGER NOT NULL DEFAULT 0,counted_count INTEGER NOT NULL DEFAULT 0,
            missing_count INTEGER NOT NULL DEFAULT 0,unexpected_count INTEGER NOT NULL DEFAULT 0,note TEXT,created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,finalized_at TEXT,finalized_by INTEGER)""")
        c.execute("""CREATE TABLE IF NOT EXISTS stock_count_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,stock_count_id INTEGER NOT NULL,stock_type TEXT NOT NULL,item_id INTEGER,
            item_code TEXT NOT NULL,expected INTEGER NOT NULL DEFAULT 0,counted INTEGER NOT NULL DEFAULT 0,
            variance INTEGER NOT NULL DEFAULT 0,counted_at TEXT,UNIQUE(stock_count_id,stock_type,item_code))""")
        c.commit()

def start_exchange_workflow(created_by=None):
    ensure_operations_schema()
    with get_connection() as c:
        if created_by:
            existing=c.execute("""SELECT * FROM exchange_workflows WHERE created_by=?
                AND status IN ('draft','pending') AND gold_exchange_id IS NULL ORDER BY id DESC LIMIT 1""",(int(created_by),)).fetchone()
            if existing:return {"workflow_id":existing["id"],"workflow_no":existing["workflow_no"],"resumed":True}
        no=next_document_no(c,"exchange_workflow","EXW");cur=c.execute("INSERT INTO exchange_workflows(workflow_no,created_by) VALUES (?,?)",(no,created_by));c.commit()
    return {"workflow_id":cur.lastrowid,"workflow_no":no}

def get_exchange_workflow(workflow_id):
    ensure_operations_schema()
    with get_connection() as c:row=c.execute("SELECT * FROM exchange_workflows WHERE id=?",(int(workflow_id),)).fetchone()
    return dict(row) if row else None

def update_exchange_workflow(workflow_id,old_receipt_id=None,sale_id=None,exchange_id=None):
    ensure_operations_schema();fields=[];values=[]
    if old_receipt_id:fields.extend(["old_gold_receipt_id=?","current_step='new_gold'","status='pending'"]);values.append(int(old_receipt_id))
    if sale_id:fields.extend(["gold_sale_id=?","current_step='linking'"]);values.append(int(sale_id))
    if exchange_id:fields.extend(["gold_exchange_id=?","current_step='completed'","status='completed'"]);values.append(int(exchange_id))
    if not fields:return
    with get_connection() as c:c.execute(f"UPDATE exchange_workflows SET {','.join(fields)},updated_at=CURRENT_TIMESTAMP WHERE id=?",values+[int(workflow_id)]);c.commit()

def list_exchange_workflows(status=""):
    ensure_operations_schema();where="WHERE w.status=?" if status else "";params=(status,) if status else ()
    with get_connection() as c:rows=c.execute(f"""SELECT w.*,o.receipt_no,s.sale_no,e.exchange_no FROM exchange_workflows w
        LEFT JOIN old_gold_receipts o ON o.id=w.old_gold_receipt_id LEFT JOIN gold_sales s ON s.id=w.gold_sale_id
        LEFT JOIN gold_exchanges e ON e.id=w.gold_exchange_id {where} ORDER BY w.id DESC""",params).fetchall()
    return [dict(x) for x in rows]

def cancel_exchange_workflow(workflow_id,reason,user_id):
    reason=str(reason or "").strip()
    if not reason:raise ValueError("กรุณาระบุเหตุผล")
    rows=list_exchange_workflows();w=next((x for x in rows if x["id"]==int(workflow_id)),None)
    if not w or w["status"] in {"cancelled"}:raise ValueError("รายการนี้ยกเลิกไม่ได้")
    errors=[]
    if w.get("gold_sale_id"):
        try:cancel_gold_sale(w["gold_sale_id"],f"ยกเลิกรายการแลก {w['workflow_no']}: {reason}",user_id)
        except Exception as e:errors.append(f"ขายทอง: {e}")
    if w.get("old_gold_receipt_id"):
        try:cancel_old_gold_receipt(w["old_gold_receipt_id"],f"ยกเลิกรายการแลก {w['workflow_no']}: {reason}",user_id)
        except Exception as e:errors.append(f"รับซื้อทองเก่า: {e}")
    status="reversal_error" if errors else "cancelled"
    with get_connection() as c:
        c.execute("UPDATE exchange_workflows SET status=?,cancelled_at=CURRENT_TIMESTAMP,cancelled_by=?,cancel_reason=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(status,user_id,reason,int(workflow_id)))
        if w.get("gold_exchange_id"):c.execute("UPDATE gold_exchanges SET status=?,cancelled_at=CURRENT_TIMESTAMP,cancelled_by=?,cancel_reason=? WHERE id=?",(status,user_id,reason,w["gold_exchange_id"]))
        c.commit()
    return {"workflow_no":w["workflow_no"],"status":status,"errors":errors}

def create_tax_adjustment(adjustment_type,original_type,original_id,reason,amount_ex_vat,vat_amount,created_by=None):
    ensure_operations_schema();kind=str(adjustment_type)
    if kind not in {"credit_note","debit_note"}:raise ValueError("ประเภทเอกสารไม่ถูกต้อง")
    reason=str(reason or "").strip()
    if not reason:raise ValueError("กรุณาระบุเหตุผล")
    if original_type!="gold_sale":raise ValueError("ขณะนี้รองรับใบกำกับภาษีขายทองใหม่")
    with get_connection() as c:
        original=c.execute("SELECT sale_no FROM gold_sales WHERE id=?",(int(original_id),)).fetchone()
        if not original:raise ValueError("ไม่พบใบกำกับภาษีเดิม")
        prefix="CN" if kind=="credit_note" else "DN";no=next_document_no(c,kind,prefix)
        base=round(float(amount_ex_vat),2);vat=round(float(vat_amount),2);total=round(base+vat,2)
        cur=c.execute("""INSERT INTO tax_adjustments(document_no,adjustment_type,original_document_type,original_document_id,
            original_document_no,document_date,reason,amount_ex_vat,vat_amount,total_amount,created_by)
            VALUES (?,?,?,?,?,CURRENT_DATE,?,?,?,?,?)""",(no,kind,original_type,int(original_id),original["sale_no"],reason,base,vat,total,created_by));c.commit()
    return {"adjustment_id":cur.lastrowid,"document_no":no,"total_amount":total}

def get_tax_adjustment(adjustment_id):
    ensure_operations_schema()
    with get_connection() as c:row=c.execute("SELECT * FROM tax_adjustments WHERE id=?",(int(adjustment_id),)).fetchone()
    return dict(row) if row else None

def tax_report(date_from,date_to):
    ensure_operations_schema()
    with get_connection() as c:
        sales=c.execute("""SELECT sale_date document_date,sale_no document_no,'ขายทองใหม่' document_type,
            customer_name party,vat_base,vat_amount,grand_total total_amount,status FROM gold_sales WHERE sale_date BETWEEN ? AND ?""",(date_from,date_to)).fetchall()
        adj=c.execute("""SELECT document_date,document_no,CASE adjustment_type WHEN 'credit_note' THEN 'ใบลดหนี้' ELSE 'ใบเพิ่มหนี้' END document_type,
            original_document_no party,CASE WHEN adjustment_type='credit_note' THEN -amount_ex_vat ELSE amount_ex_vat END vat_base,
            CASE WHEN adjustment_type='credit_note' THEN -vat_amount ELSE vat_amount END vat_amount,
            CASE WHEN adjustment_type='credit_note' THEN -total_amount ELSE total_amount END total_amount,status
            FROM tax_adjustments WHERE document_date BETWEEN ? AND ?""",(date_from,date_to)).fetchall()
        q=c.execute("""SELECT substr(transaction_at,1,10) document_date,COALESCE(t.tax_document_no,'Q-'||printf('%06d',t.id)) document_no,
            CASE transaction_type WHEN 'renew' THEN 'ต่อสัญญา Q' ELSE 'ไถ่ถอน Q' END document_type,p.ticket_no party,
            t.vat_base,t.vat_amount,t.total_with_vat total_amount,t.transaction_status status FROM pawn_transactions t
            JOIN pawn_tickets p ON p.id=t.pawn_ticket_id WHERE p.series_code='Q' AND t.transaction_type IN ('renew','redeem')
            AND substr(t.transaction_at,1,10) BETWEEN ? AND ?""",(date_from,date_to)).fetchall()
    return [dict(x) for x in list(sales)+list(adj)+list(q)]

def cash_report(report_date):
    ensure_operations_schema();d=str(report_date)
    with get_connection() as c:
        rows=[]
        for sql,params in [
            ("SELECT sale_no document_no,'ขายทองใหม่' category,payment_method,amount_paid cash_in,0 cash_out FROM gold_sales WHERE sale_date=? AND status='completed'",(d,)),
            ("SELECT receipt_no document_no,'รับซื้อทองเก่า' category,payment_method,0 cash_in,paid_amount cash_out FROM old_gold_receipts o WHERE receipt_date=? AND source_type='customer_buyback' AND status='completed' AND NOT EXISTS(SELECT 1 FROM gold_exchanges e WHERE e.old_gold_receipt_id=o.id AND e.status='completed')",(d,)),
            ("SELECT exchange_no document_no,'คืนส่วนต่างแลกทอง' category,settlement_method payment_method,0 cash_in,-difference_amount cash_out FROM gold_exchanges WHERE substr(created_at,1,10)=? AND status='completed' AND difference_amount<0",(d,)),
            ("SELECT p.ticket_no document_no,CASE t.transaction_type WHEN 'renew' THEN 'ต่อสัญญา' ELSE 'ไถ่ถอน' END category,'เงินสด' payment_method,t.amount cash_in,0 cash_out FROM pawn_transactions t JOIN pawn_tickets p ON p.id=t.pawn_ticket_id WHERE substr(t.transaction_at,1,10)=? AND t.transaction_type IN ('renew','redeem') AND t.transaction_status='completed'",(d,))]:
            rows.extend(dict(x) for x in c.execute(sql,params).fetchall())
    return rows

def sell_old_gold_bulk(item_ids,buyer_name,sale_amount,payment_method="เงินสด",buyer_tax_id="",notes="",created_by=None):
    ensure_operations_schema();ids=list(dict.fromkeys(int(x) for x in item_ids));amount=float(sale_amount)
    if not ids or amount<=0 or not str(buyer_name).strip():raise ValueError("กรุณาเลือกรายการ ระบุคู่ค้า และราคาขาย")
    with get_connection() as c:
        marks=','.join('?'*len(ids));items=c.execute(f"SELECT * FROM old_gold_items WHERE id IN ({marks})",ids).fetchall()
        if len(items)!=len(ids) or any(x['status']!='old_gold_stock' for x in items):raise ValueError("ขายได้เฉพาะทองเก่าที่อยู่ในสต็อก")
        no=next_document_no(c,"old_gold_bulk_sale","OGB-S");weight=sum(x['net_weight'] for x in items);cost=sum(x['acquisition_cost'] for x in items)
        cur=c.execute("""INSERT INTO old_gold_bulk_sales(sale_no,sale_date,buyer_name,buyer_tax_id,payment_method,total_weight,total_cost,sale_amount,notes,created_by)
            VALUES (?,CURRENT_DATE,?,?,?,?,?,?,?,?)""",(no,buyer_name,buyer_tax_id,payment_method,weight,cost,amount,notes,created_by));sid=cur.lastrowid
        allocated=0
        for i,x in enumerate(items):
            part=round(amount-allocated,2) if i==len(items)-1 else round(amount*x['net_weight']/weight,2);allocated+=part
            c.execute("INSERT INTO old_gold_bulk_sale_items VALUES (?,?,?)",(sid,x['id'],part));c.execute("UPDATE old_gold_items SET status='sold_bulk' WHERE id=?",(x['id'],))
            c.execute("INSERT INTO old_gold_movements(old_gold_item_id,movement_type,from_status,to_status,reference_type,reference_id,note,created_by) VALUES (?,'sell_bulk','old_gold_stock','sold_bulk','old_gold_bulk_sale',?,?,?)",(x['id'],sid,notes,created_by))
        c.commit()
    return {"sale_id":sid,"sale_no":no,"items":len(items),"total_weight":weight,"total_cost":cost,"sale_amount":amount}

def get_old_gold_bulk_sale(sale_id):
    ensure_operations_schema()
    with get_connection() as c:
        row=c.execute("SELECT * FROM old_gold_bulk_sales WHERE id=?",(int(sale_id),)).fetchone()
        if not row:return None
        items=c.execute("""SELECT i.item_code,i.item_type,i.description,i.net_weight,i.purity,l.sale_allocated
            FROM old_gold_bulk_sale_items l JOIN old_gold_items i ON i.id=l.old_gold_item_id WHERE l.sale_id=? ORDER BY i.id""",(int(sale_id),)).fetchall()
    result=dict(row);result['items']=[dict(x) for x in items];return result

def start_stock_count(count_type="new_gold",location="",note="",created_by=None):
    ensure_operations_schema()
    if count_type not in {"new_gold","old_gold"}:raise ValueError("ประเภทการตรวจนับไม่ถูกต้อง")
    with get_connection() as c:
        no=next_document_no(c,"stock_count","COUNT");cur=c.execute("INSERT INTO stock_counts(count_no,count_type,count_date,location,note,created_by) VALUES (?,?,CURRENT_DATE,?,?,?)",(no,count_type,location,note,created_by));cid=cur.lastrowid
        if count_type=="new_gold":rows=c.execute("SELECT id,item_code FROM inventory_items WHERE status='in_stock' AND (?='' OR storage_location=?)",(location,location)).fetchall()
        else:rows=c.execute("SELECT id,item_code FROM old_gold_items WHERE status='old_gold_stock' AND (?='' OR storage_location=?)",(location,location)).fetchall()
        c.executemany("INSERT INTO stock_count_items(stock_count_id,stock_type,item_id,item_code,expected) VALUES (?,?,?,?,1)",[(cid,count_type,x['id'],x['item_code']) for x in rows]);c.execute("UPDATE stock_counts SET expected_count=? WHERE id=?",(len(rows),cid));c.commit()
    return {"count_id":cid,"count_no":no,"expected_count":len(rows)}

def scan_stock_count(count_id,item_code):
    code=str(item_code or '').strip().upper()
    with get_connection() as c:
        session=c.execute("SELECT * FROM stock_counts WHERE id=? AND status='open'",(int(count_id),)).fetchone()
        if not session:raise ValueError("รอบตรวจนับปิดแล้วหรือไม่พบข้อมูล")
        row=c.execute("SELECT * FROM stock_count_items WHERE stock_count_id=? AND UPPER(item_code)=?",(int(count_id),code)).fetchone()
        if row:
            if row['counted']>=1:raise ValueError("รหัสนี้ถูกตรวจนับแล้ว")
            c.execute("UPDATE stock_count_items SET counted=1,variance=1-expected,counted_at=CURRENT_TIMESTAMP WHERE id=?",(row['id'],))
        else:c.execute("INSERT INTO stock_count_items(stock_count_id,stock_type,item_code,expected,counted,variance,counted_at) VALUES (?,?,?,0,1,1,CURRENT_TIMESTAMP)",(int(count_id),session['count_type'],code))
        c.commit()

def set_stock_count_quantity(count_id,item_code,counted):
    qty=int(counted);code=str(item_code or '').strip().upper()
    if qty<0:raise ValueError("จำนวนที่นับได้ต้องไม่ติดลบ")
    if not code:raise ValueError("กรุณาเลือกรายการ")
    with get_connection() as c:
        session=c.execute("SELECT * FROM stock_counts WHERE id=? AND status='open'",(int(count_id),)).fetchone()
        if not session:raise ValueError("รอบตรวจนับปิดแล้วหรือไม่พบข้อมูล")
        row=c.execute("SELECT * FROM stock_count_items WHERE stock_count_id=? AND UPPER(item_code)=?",(int(count_id),code)).fetchone()
        if row:c.execute("UPDATE stock_count_items SET counted=?,variance=?-expected,counted_at=CASE WHEN ?>0 THEN CURRENT_TIMESTAMP ELSE NULL END WHERE id=?",(qty,qty,qty,row['id']))
        else:c.execute("INSERT INTO stock_count_items(stock_count_id,stock_type,item_code,expected,counted,variance,counted_at) VALUES (?,?,?,0,?,?,CASE WHEN ?>0 THEN CURRENT_TIMESTAMP END)",(int(count_id),session['count_type'],code,qty,qty,qty))
        c.commit()

def mark_stock_count_complete(count_id):
    with get_connection() as c:
        if not c.execute("SELECT 1 FROM stock_counts WHERE id=? AND status='open'",(int(count_id),)).fetchone():raise ValueError("รอบตรวจนับปิดแล้วหรือไม่พบข้อมูล")
        c.execute("UPDATE stock_count_items SET counted=expected,variance=0,counted_at=CURRENT_TIMESTAMP WHERE stock_count_id=?",(int(count_id),));c.commit()

def finalize_stock_count(count_id,user_id=None):
    with get_connection() as c:
        c.execute("UPDATE stock_count_items SET variance=counted-expected WHERE stock_count_id=?",(int(count_id),))
        totals=c.execute("SELECT SUM(counted) counted,SUM(CASE WHEN variance<0 THEN ABS(variance) ELSE 0 END) missing,SUM(CASE WHEN variance>0 THEN variance ELSE 0 END) unexpected FROM stock_count_items WHERE stock_count_id=?",(int(count_id),)).fetchone()
        c.execute("UPDATE stock_counts SET status='finalized',counted_count=?,missing_count=?,unexpected_count=?,finalized_at=CURRENT_TIMESTAMP,finalized_by=? WHERE id=? AND status='open'",(totals['counted'] or 0,totals['missing'] or 0,totals['unexpected'] or 0,user_id,int(count_id)));c.commit()
    return dict(totals)

def get_stock_count_items(count_id):
    with get_connection() as c:rows=c.execute("SELECT * FROM stock_count_items WHERE stock_count_id=? ORDER BY variance,item_code",(int(count_id),)).fetchall()
    return [dict(x) for x in rows]

ensure_operations_schema()
