from datetime import date,datetime

from database.database import get_connection
from modules.pawn import ensure_pawn_schema,get_settings
from modules.qr_code import qr_payload
from modules.document_numbers import next_document_no


SOURCE_CUSTOMER="customer_buyback"
SOURCE_FORFEIT="forfeited_pawn"


def ensure_old_gold_schema():
    ensure_pawn_schema()
    with get_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS old_gold_receipts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,receipt_no TEXT NOT NULL UNIQUE,
            source_type TEXT NOT NULL,customer_id INTEGER,forfeit_batch_id INTEGER,
            receipt_date TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'completed',
            reference_gold_price REAL NOT NULL DEFAULT 0,total_gross_weight REAL NOT NULL DEFAULT 0,
            total_non_gold_weight REAL NOT NULL DEFAULT 0,total_net_weight REAL NOT NULL DEFAULT 0,
            gross_value REAL NOT NULL DEFAULT 0,deduction_amount REAL NOT NULL DEFAULT 0,
            paid_amount REAL NOT NULL DEFAULT 0,payment_method TEXT NOT NULL DEFAULT 'เงินสด',
            payment_reference TEXT,notes TEXT,created_by INTEGER,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            cancelled_at TEXT,cancelled_by INTEGER,cancel_reason TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id),FOREIGN KEY(created_by) REFERENCES users(id))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS old_gold_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,item_code TEXT NOT NULL UNIQUE,qr_payload TEXT NOT NULL UNIQUE,
            old_gold_receipt_id INTEGER NOT NULL,source_type TEXT NOT NULL,source_pawn_ticket_id INTEGER,
            source_pawn_item_id INTEGER,item_type TEXT NOT NULL,description TEXT NOT NULL,quantity INTEGER NOT NULL DEFAULT 1,
            gross_weight REAL NOT NULL DEFAULT 0,non_gold_weight REAL NOT NULL DEFAULT 0,net_weight REAL NOT NULL,
            purity REAL NOT NULL,reference_gold_price REAL NOT NULL DEFAULT 0,gross_value REAL NOT NULL DEFAULT 0,
            deduction_amount REAL NOT NULL DEFAULT 0,acquisition_cost REAL NOT NULL DEFAULT 0,
            inspection_method TEXT,condition_note TEXT,storage_location TEXT,destination TEXT NOT NULL DEFAULT 'old_gold_stock',
            status TEXT NOT NULL DEFAULT 'old_gold_stock',batch_id INTEGER,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(old_gold_receipt_id) REFERENCES old_gold_receipts(id),FOREIGN KEY(source_pawn_ticket_id) REFERENCES pawn_tickets(id),
            FOREIGN KEY(source_pawn_item_id) REFERENCES pawn_items(id))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS old_gold_movements(
            id INTEGER PRIMARY KEY AUTOINCREMENT,old_gold_item_id INTEGER,movement_type TEXT NOT NULL,
            from_status TEXT,to_status TEXT,reference_type TEXT NOT NULL,reference_id INTEGER NOT NULL,
            note TEXT,created_by INTEGER,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(old_gold_item_id) REFERENCES old_gold_items(id),FOREIGN KEY(created_by) REFERENCES users(id))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS old_gold_batches(
            id INTEGER PRIMARY KEY AUTOINCREMENT,batch_no TEXT NOT NULL UNIQUE,status TEXT NOT NULL DEFAULT 'assembled',
            total_weight REAL NOT NULL,total_cost REAL NOT NULL,destination TEXT NOT NULL DEFAULT 'awaiting_decision',
            refinery_id INTEGER,shipment_no TEXT,expected_purity REAL,actual_purity REAL,received_weight REAL,
            loss_weight REAL DEFAULT 0,service_cost REAL DEFAULT 0,notes TEXT,created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,sent_at TEXT,received_at TEXT,
            FOREIGN KEY(refinery_id) REFERENCES suppliers(id),FOREIGN KEY(created_by) REFERENCES users(id))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS old_gold_batch_items(
            batch_id INTEGER NOT NULL,old_gold_item_id INTEGER NOT NULL UNIQUE,
            PRIMARY KEY(batch_id,old_gold_item_id),FOREIGN KEY(batch_id) REFERENCES old_gold_batches(id),
            FOREIGN KEY(old_gold_item_id) REFERENCES old_gold_items(id))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS old_gold_sales(
            id INTEGER PRIMARY KEY AUTOINCREMENT,sale_no TEXT NOT NULL UNIQUE,old_gold_item_id INTEGER NOT NULL UNIQUE,
            sale_date TEXT NOT NULL,sale_price REAL NOT NULL,payment_method TEXT NOT NULL,buyer_name TEXT,
            notes TEXT,created_by INTEGER,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(old_gold_item_id) REFERENCES old_gold_items(id),FOREIGN KEY(created_by) REFERENCES users(id))""")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_old_gold_pawn_item ON old_gold_items(source_pawn_item_id) WHERE source_pawn_item_id IS NOT NULL")
        receipt_columns={row[1] for row in conn.execute("PRAGMA table_info(old_gold_receipts)").fetchall()}
        if "purchase_discount_rate" not in receipt_columns:
            conn.execute("ALTER TABLE old_gold_receipts ADD COLUMN purchase_discount_rate REAL NOT NULL DEFAULT 0")
        if "receipt_total" not in receipt_columns:
            conn.execute("ALTER TABLE old_gold_receipts ADD COLUMN receipt_total REAL NOT NULL DEFAULT 0")
            conn.execute("UPDATE old_gold_receipts SET receipt_total=paid_amount WHERE receipt_total=0")
        item_columns={row[1] for row in conn.execute("PRAGMA table_info(old_gold_items)").fetchall()}
        if "receipt_amount" not in item_columns:
            conn.execute("ALTER TABLE old_gold_items ADD COLUMN receipt_amount REAL NOT NULL DEFAULT 0")
            conn.execute("UPDATE old_gold_items SET receipt_amount=acquisition_cost WHERE receipt_amount=0")
        batch_columns={row[1] for row in conn.execute("PRAGMA table_info(old_gold_batches)").fetchall()}
        for column,definition in (("batch_name","TEXT"),("purpose","TEXT")):
            if column not in batch_columns:conn.execute(f"ALTER TABLE old_gold_batches ADD COLUMN {column} {definition}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_old_gold_status ON old_gold_items(status,source_type)")
        conn.commit()


def _next(conn,table,column,prefix):
    kinds={"OGB":"old_gold_buyback","OGF":"old_gold_forfeit","OLD":"old_gold_item","LOT":"old_gold_batch","OGS":"old_gold_sale"}
    while True:
        number=next_document_no(conn,kinds.get(prefix,prefix),prefix)
        if not conn.execute(f"SELECT 1 FROM {table} WHERE {column}=?",(number,)).fetchone():return number


def calculate_buyback_line(line,weight_per_baht=None):
    grams=float(weight_per_baht or get_settings()["weight_per_baht_gram"]);gross=float(line.get("gross_weight") or 0);other=float(line.get("non_gold_weight") or 0);purity=float(line.get("purity") or 0);price=float(line.get("reference_gold_price") or 0);deduction=float(line.get("deduction_amount") or 0);quantity=int(line.get("quantity") or 1)
    if quantity<=0:raise ValueError("จำนวนต้องมากกว่า 0")
    if gross<=0:raise ValueError("น้ำหนักรวมต้องมากกว่า 0")
    if other<0 or other>=gross:raise ValueError("น้ำหนักสิ่งเจือปนต้องไม่ติดลบและน้อยกว่าน้ำหนักรวม")
    if purity<=0 or purity>100:raise ValueError("เปอร์เซ็นต์ทองต้องอยู่ระหว่าง 0–100")
    if price<=0:raise ValueError("ราคารับซื้ออ้างอิงต้องมากกว่า 0")
    if deduction<0:raise ValueError("ยอดหักต้องไม่ติดลบ")
    net=gross-other;value=round((net/grams)*price*(purity/96.5),2);estimated=round(value-deduction,2)
    receipt_input=line.get("receipt_amount")
    receipt_amount=round(float(receipt_input),2) if receipt_input not in (None,"") else estimated
    actual_input=line.get("actual_paid_amount",line.get("paid_amount"))
    actual_paid=round(float(actual_input),2) if actual_input not in (None,"") else receipt_amount
    if receipt_amount<=0:raise ValueError("ราคาในใบรับซื้อ/รายการต้องมากกว่า 0")
    if actual_paid<=0:raise ValueError("จำนวนเงินจ่ายจริง/รายการต้องมากกว่า 0")
    return {**line,"quantity":quantity,"gross_weight":gross,"non_gold_weight":other,"net_weight":round(net,3),"purity":purity,"reference_gold_price":price,"gross_value":value,"deduction_amount":deduction,"estimated_amount":estimated,"receipt_amount":receipt_amount,"paid_amount":actual_paid,"acquisition_cost":actual_paid}


def create_customer_buyback(header,lines,created_by=None):
    ensure_old_gold_schema()
    if not lines:raise ValueError("กรุณาเพิ่มทองเก่าอย่างน้อย 1 รายการ")
    customer_id=int(header.get("customer_id") or 0);calculated=[calculate_buyback_line(x) for x in lines]
    calculated_total=round(sum(x["acquisition_cost"] for x in calculated),2)
    requested=header.get("paid_amount")
    paid=round(float(requested),2) if requested not in (None,"") else calculated_total
    if paid<=0:raise ValueError("จำนวนเงินที่จ่ายลูกค้าต้องมากกว่า 0")
    # ต้นทุนสต็อกต้องตรงกับเงินจริงที่จ่าย โดยกระจายตามสัดส่วนราคาประเมิน
    if requested not in (None,""):
        allocated=0.0
        for index,x in enumerate(calculated):
            cost=round(paid-allocated,2) if index==len(calculated)-1 else round(paid*(x["acquisition_cost"]/calculated_total),2) if calculated_total else round(paid/len(calculated),2)
            x["acquisition_cost"]=cost;allocated+=cost
    with get_connection() as conn:
        if not conn.execute("SELECT id FROM customers WHERE id=?",(customer_id,)).fetchone():raise ValueError("กรุณาเลือกลูกค้า")
        receipt_no=_next(conn,"old_gold_receipts","receipt_no","OGB")
        receipt_total=round(sum(x["receipt_amount"] for x in calculated),2)
        cursor=conn.execute("""INSERT INTO old_gold_receipts(receipt_no,source_type,customer_id,receipt_date,reference_gold_price,total_gross_weight,total_non_gold_weight,total_net_weight,gross_value,deduction_amount,paid_amount,payment_method,payment_reference,notes,created_by,purchase_discount_rate,receipt_total)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(receipt_no,SOURCE_CUSTOMER,customer_id,str(header.get("receipt_date") or date.today().isoformat()),float(header.get("reference_gold_price") or 0),sum(x["gross_weight"] for x in calculated),sum(x["non_gold_weight"] for x in calculated),sum(x["net_weight"] for x in calculated),sum(x["gross_value"] for x in calculated),sum(x["deduction_amount"] for x in calculated),paid,str(header.get("payment_method") or "เงินสด"),str(header.get("payment_reference") or ""),str(header.get("notes") or ""),created_by,float(header.get("purchase_discount_rate") or 0),receipt_total))
        receipt_id=cursor.lastrowid;item_ids=[]
        for x in calculated:
            code=_next(conn,"old_gold_items","item_code","OLD")
            cur=conn.execute("""INSERT INTO old_gold_items(item_code,qr_payload,old_gold_receipt_id,source_type,item_type,description,quantity,gross_weight,non_gold_weight,net_weight,purity,reference_gold_price,gross_value,deduction_amount,acquisition_cost,inspection_method,condition_note,storage_location,destination,status,receipt_amount)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'old_gold_stock',?)""",(code,qr_payload(code),receipt_id,SOURCE_CUSTOMER,str(x.get("item_type") or "ทองเก่า"),str(x.get("description") or ""),x["quantity"],x["gross_weight"],x["non_gold_weight"],x["net_weight"],x["purity"],x["reference_gold_price"],x["gross_value"],x["deduction_amount"],x["acquisition_cost"],str(x.get("inspection_method") or "ระบุโดยผู้ใช้"),str(x.get("condition_note") or ""),str(x.get("storage_location") or ""),str(x.get("destination") or "old_gold_stock"),x["receipt_amount"]))
            item_ids.append(cur.lastrowid);conn.execute("INSERT INTO old_gold_movements(old_gold_item_id,movement_type,from_status,to_status,reference_type,reference_id,note,created_by) VALUES (?,'buyback_in',NULL,'old_gold_stock','old_gold_receipt',?,'รับซื้อทองเก่าจากลูกค้า',?)",(cur.lastrowid,receipt_id,created_by))
        conn.commit()
    return {"receipt_id":receipt_id,"receipt_no":receipt_no,"item_ids":item_ids,"paid_amount":paid}


def list_untransferred_forfeited_pawns(keyword=""):
    ensure_old_gold_schema();params=[];sql="""SELECT p.id,p.ticket_no,p.loan_amount,p.forfeited_at,c.first_name||' '||c.last_name customer_name,
        COUNT(pi.id) item_count,COALESCE(SUM(pi.weight_grams),0) total_weight FROM pawn_tickets p JOIN customers c ON c.id=p.customer_id
        JOIN pawn_items pi ON pi.pawn_ticket_id=p.id WHERE p.status='forfeited' AND NOT EXISTS(SELECT 1 FROM old_gold_items oi WHERE oi.source_pawn_ticket_id=p.id)"""
    if keyword:term=f"%{keyword}%";sql+=" AND (p.ticket_no LIKE ? OR c.first_name LIKE ? OR c.last_name LIKE ?)";params.extend([term]*3)
    sql+=" GROUP BY p.id ORDER BY p.forfeited_at DESC,p.id DESC"
    with get_connection() as conn:rows=conn.execute(sql,params).fetchall()
    return [dict(x) for x in rows]


def transfer_forfeited_pawns(ticket_ids,storage_location="",destination="old_gold_stock",note="",created_by=None):
    ensure_old_gold_schema();ids=list(dict.fromkeys(int(x) for x in ticket_ids))
    if not ids:raise ValueError("กรุณาเลือกตั๋วหลุดอย่างน้อย 1 ใบ")
    with get_connection() as conn:
        receipt_no=_next(conn,"old_gold_receipts","receipt_no","OGF");pawns=[]
        for pid in ids:
            pawn=conn.execute("SELECT * FROM pawn_tickets WHERE id=? AND status='forfeited'",(pid,)).fetchone()
            if not pawn:raise ValueError(f"ตั๋วรหัส {pid} ไม่อยู่ในสถานะหลุดขายฝาก")
            if conn.execute("SELECT 1 FROM old_gold_items WHERE source_pawn_ticket_id=?",(pid,)).fetchone():raise ValueError(f"ตั๋ว {pawn['ticket_no']} ถูกนำเข้าสต็อกแล้ว")
            items=conn.execute("SELECT * FROM pawn_items WHERE pawn_ticket_id=? ORDER BY item_no",(pid,)).fetchall()
            if not items:raise ValueError(f"ตั๋ว {pawn['ticket_no']} ไม่มีรายการทรัพย์")
            pawns.append((pawn,items))
        total_cost=sum(float(x[0]["loan_amount"]) for x in pawns);total_weight=sum(float(i["weight_grams"] or 0) for _,items in pawns for i in items)
        cursor=conn.execute("""INSERT INTO old_gold_receipts(receipt_no,source_type,receipt_date,total_gross_weight,total_net_weight,gross_value,paid_amount,payment_method,notes,created_by)
            VALUES (?,?,CURRENT_DATE,?,?,?,0,'โอนจากตั๋วหลุด',?,?)""",(receipt_no,SOURCE_FORFEIT,total_weight,total_weight,total_cost,str(note or "โอนทรัพย์หลุดขายฝากเข้าสู่สต็อกทองเก่า"),created_by));receipt_id=cursor.lastrowid;item_ids=[]
        for pawn,items in pawns:
            pawn_weight=sum(float(i["weight_grams"] or 0) for i in items);allocated=0.0
            for index,item in enumerate(items):
                cost=(float(pawn["loan_amount"])-allocated) if index==len(items)-1 else round(float(pawn["loan_amount"])*(float(item["weight_grams"] or 0)/pawn_weight),2) if pawn_weight else round(float(pawn["loan_amount"])/len(items),2);allocated+=cost
                code=_next(conn,"old_gold_items","item_code","OLD");net=float(item["weight_grams"] or 0)
                cur=conn.execute("""INSERT INTO old_gold_items(item_code,qr_payload,old_gold_receipt_id,source_type,source_pawn_ticket_id,source_pawn_item_id,item_type,description,quantity,gross_weight,non_gold_weight,net_weight,purity,reference_gold_price,gross_value,deduction_amount,acquisition_cost,inspection_method,condition_note,storage_location,destination,status)
                    VALUES (?,?,?,?,?,?,?,?,1,?,0,?,?,?,?,0,?,'ข้อมูลจากใบขายฝาก',?,?,?,'old_gold_stock')""",(code,qr_payload(code),receipt_id,SOURCE_FORFEIT,pawn["id"],item["id"],item["item_type"],item["description"],net,net,float(item["purity"] or 0),float(item["gold_price_per_baht"] or 0),float(item["estimated_value"] or 0),cost,str(note or ""),str(storage_location or ""),str(destination or "old_gold_stock")))
                item_ids.append(cur.lastrowid);conn.execute("INSERT INTO old_gold_movements(old_gold_item_id,movement_type,from_status,to_status,reference_type,reference_id,note,created_by) VALUES (?,'forfeit_in',NULL,'old_gold_stock','old_gold_receipt',?,'รับเข้าจากตั๋วหลุดขายฝาก',?)",(cur.lastrowid,receipt_id,created_by))
        conn.commit()
    return {"receipt_id":receipt_id,"receipt_no":receipt_no,"item_ids":item_ids,"ticket_count":len(ids),"total_cost":round(total_cost,2)}


def get_old_gold_receipt(receipt_id):
    ensure_old_gold_schema()
    with get_connection() as conn:
        row=conn.execute("""SELECT r.*,c.customer_code,c.first_name,c.last_name,c.citizen_id,c.address,c.phone,u.full_name created_by_name,cu.full_name cancelled_by_name
            FROM old_gold_receipts r LEFT JOIN customers c ON c.id=r.customer_id LEFT JOIN users u ON u.id=r.created_by LEFT JOIN users cu ON cu.id=r.cancelled_by WHERE r.id=?""",(int(receipt_id),)).fetchone()
        if not row:return None
        items=conn.execute("""SELECT i.*,p.ticket_no FROM old_gold_items i LEFT JOIN pawn_tickets p ON p.id=i.source_pawn_ticket_id WHERE i.old_gold_receipt_id=? ORDER BY i.id""",(int(receipt_id),)).fetchall()
    result=dict(row);result["items"]=[dict(x) for x in items];return result


def list_old_gold(keyword="",source_type="",status=""):
    ensure_old_gold_schema();params=[];sql="""SELECT i.*,r.receipt_no,p.ticket_no,c.first_name||' '||c.last_name customer_name,b.batch_no
        FROM old_gold_items i JOIN old_gold_receipts r ON r.id=i.old_gold_receipt_id LEFT JOIN customers c ON c.id=r.customer_id
        LEFT JOIN pawn_tickets p ON p.id=i.source_pawn_ticket_id LEFT JOIN old_gold_batches b ON b.id=i.batch_id WHERE r.status<>'cancelled'"""
    if keyword:term=f"%{keyword}%";sql+=" AND (i.item_code LIKE ? OR i.item_type LIKE ? OR i.description LIKE ? OR r.receipt_no LIKE ? OR p.ticket_no LIKE ? OR c.first_name LIKE ? OR c.last_name LIKE ?)";params.extend([term]*7)
    if source_type:sql+=" AND i.source_type=?";params.append(source_type)
    if status:sql+=" AND i.status=?";params.append(status)
    sql+=" ORDER BY i.id DESC"
    with get_connection() as conn:rows=conn.execute(sql,params).fetchall()
    return [dict(x) for x in rows]


def cancel_old_gold_receipt(receipt_id,reason,cancelled_by):
    ensure_old_gold_schema();reason=str(reason or "").strip()
    if not reason:raise ValueError("กรุณาระบุเหตุผล")
    with get_connection() as conn:
        receipt=conn.execute("SELECT * FROM old_gold_receipts WHERE id=?",(int(receipt_id),)).fetchone()
        if not receipt or receipt["status"]!="completed":raise ValueError("รายการนี้ไม่สามารถยกเลิกได้")
        items=conn.execute("SELECT * FROM old_gold_items WHERE old_gold_receipt_id=?",(int(receipt_id),)).fetchall()
        blocked=[x["item_code"] for x in items if x["status"] not in {"old_gold_stock","pending_inspection"}]
        if blocked:raise ValueError("ยกเลิกไม่ได้เพราะสินค้าถูกนำไปดำเนินการแล้ว: "+", ".join(blocked))
        conn.execute("UPDATE old_gold_receipts SET status='cancelled',cancelled_at=CURRENT_TIMESTAMP,cancelled_by=?,cancel_reason=? WHERE id=?",(cancelled_by,reason,int(receipt_id)))
        for x in items:
            conn.execute("UPDATE old_gold_items SET status='cancelled' WHERE id=?",(x["id"],));conn.execute("INSERT INTO old_gold_movements(old_gold_item_id,movement_type,from_status,to_status,reference_type,reference_id,note,created_by) VALUES (?,'cancel',?,'cancelled','old_gold_receipt',?,?,?)",(x["id"],x["status"],int(receipt_id),reason,cancelled_by))
        conn.commit()
    return {"receipt_id":int(receipt_id),"receipt_no":receipt["receipt_no"],"items":len(items)}


def create_old_gold_batch(item_ids,destination="awaiting_decision",notes="",created_by=None,batch_name="",purpose="ส่งหลอม"):
    ensure_old_gold_schema();ids=list(dict.fromkeys(int(x) for x in item_ids))
    if not ids:raise ValueError("กรุณาเลือกทองเก่าอย่างน้อย 1 รายการ")
    with get_connection() as conn:
        marks=",".join("?"*len(ids));items=conn.execute(f"SELECT * FROM old_gold_items WHERE id IN ({marks})",ids).fetchall()
        if len(items)!=len(ids) or any(x["status"]!="old_gold_stock" for x in items):raise ValueError("รวมล็อตได้เฉพาะสินค้าที่อยู่ในสต็อกทองเก่า")
        no=_next(conn,"old_gold_batches","batch_no","LOT");cur=conn.execute("INSERT INTO old_gold_batches(batch_no,total_weight,total_cost,destination,notes,created_by,batch_name,purpose) VALUES (?,?,?,?,?,?,?,?)",(no,sum(x["net_weight"] for x in items),sum(x["acquisition_cost"] for x in items),destination,notes,created_by,str(batch_name),str(purpose)));bid=cur.lastrowid
        for x in items:
            conn.execute("INSERT INTO old_gold_batch_items(batch_id,old_gold_item_id) VALUES (?,?)",(bid,x["id"]));conn.execute("UPDATE old_gold_items SET status='batched',batch_id=? WHERE id=?",(bid,x["id"]));conn.execute("INSERT INTO old_gold_movements(old_gold_item_id,movement_type,from_status,to_status,reference_type,reference_id,note,created_by) VALUES (?,'batch','old_gold_stock','batched','old_gold_batch',?,?,?)",(x["id"],bid,notes,created_by))
        conn.commit()
    return {"batch_id":bid,"batch_no":no,"items":len(items)}


def send_batch_to_refinery(batch_id,refinery_id,shipment_no,expected_purity,service_cost=0,notes="",created_by=None):
    ensure_old_gold_schema()
    with get_connection() as conn:
        batch=conn.execute("SELECT * FROM old_gold_batches WHERE id=? AND status='assembled'",(int(batch_id),)).fetchone()
        if not batch:raise ValueError("ล็อตนี้ไม่พร้อมส่งหลอม")
        if not conn.execute("SELECT id FROM suppliers WHERE id=? AND active=1",(int(refinery_id),)).fetchone():raise ValueError("กรุณาเลือกโรงหลอม/คู่ค้า")
        conn.execute("UPDATE old_gold_batches SET status='sent_to_refinery',destination='refinery',refinery_id=?,shipment_no=?,expected_purity=?,service_cost=?,notes=?,sent_at=CURRENT_TIMESTAMP WHERE id=?",(int(refinery_id),str(shipment_no),float(expected_purity),float(service_cost),str(notes),int(batch_id)))
        items=conn.execute("SELECT old_gold_item_id FROM old_gold_batch_items WHERE batch_id=?",(int(batch_id),)).fetchall()
        for row in items:conn.execute("UPDATE old_gold_items SET status='sent_to_refinery' WHERE id=?",(row["old_gold_item_id"],));conn.execute("INSERT INTO old_gold_movements(old_gold_item_id,movement_type,from_status,to_status,reference_type,reference_id,note,created_by) VALUES (?,'send_refinery','batched','sent_to_refinery','old_gold_batch',?,?,?)",(row["old_gold_item_id"],int(batch_id),notes,created_by))
        conn.commit()
    return {"batch_id":int(batch_id),"batch_no":batch["batch_no"]}


def receive_refined_batch(batch_id,received_weight,actual_purity,service_cost=None,notes="",created_by=None):
    ensure_old_gold_schema()
    with get_connection() as conn:
        batch=conn.execute("SELECT * FROM old_gold_batches WHERE id=? AND status='sent_to_refinery'",(int(batch_id),)).fetchone()
        if not batch:raise ValueError("ล็อตนี้ไม่ได้อยู่ระหว่างส่งหลอม")
        received=float(received_weight);purity=float(actual_purity)
        if received<=0 or purity<=0 or purity>100:raise ValueError("น้ำหนักรับกลับหรือเปอร์เซ็นต์ทองไม่ถูกต้อง")
        loss=round(float(batch["total_weight"])-received,3)
        conn.execute("UPDATE old_gold_batches SET status='melted',destination='refined_material',received_weight=?,actual_purity=?,loss_weight=?,service_cost=?,notes=?,received_at=CURRENT_TIMESTAMP WHERE id=?",(received,purity,loss,float(service_cost if service_cost is not None else batch["service_cost"]),str(notes),int(batch_id)))
        items=conn.execute("SELECT old_gold_item_id FROM old_gold_batch_items WHERE batch_id=?",(int(batch_id),)).fetchall()
        for row in items:conn.execute("UPDATE old_gold_items SET status='melted' WHERE id=?",(row["old_gold_item_id"],));conn.execute("INSERT INTO old_gold_movements(old_gold_item_id,movement_type,from_status,to_status,reference_type,reference_id,note,created_by) VALUES (?,'refinery_receive','sent_to_refinery','melted','old_gold_batch',?,?,?)",(row["old_gold_item_id"],int(batch_id),notes,created_by))
        conn.commit()
    return {"batch_id":int(batch_id),"batch_no":batch["batch_no"],"loss_weight":loss}


def sell_old_gold_item(item_id,sale_price,payment_method="เงินสด",buyer_name="",notes="",created_by=None):
    ensure_old_gold_schema();price=float(sale_price)
    if price<=0:raise ValueError("ราคาขายต้องมากกว่า 0")
    with get_connection() as conn:
        item=conn.execute("SELECT * FROM old_gold_items WHERE id=? AND status='old_gold_stock'",(int(item_id),)).fetchone()
        if not item:raise ValueError("ขายได้เฉพาะทองเก่าที่อยู่ในสต็อก")
        no=_next(conn,"old_gold_sales","sale_no","OGS");cur=conn.execute("INSERT INTO old_gold_sales(sale_no,old_gold_item_id,sale_date,sale_price,payment_method,buyer_name,notes,created_by) VALUES (?,?,CURRENT_DATE,?,?,?,?,?)",(no,int(item_id),price,str(payment_method),str(buyer_name),str(notes),created_by))
        conn.execute("UPDATE old_gold_items SET status='sold_as_is' WHERE id=?",(int(item_id),));conn.execute("INSERT INTO old_gold_movements(old_gold_item_id,movement_type,from_status,to_status,reference_type,reference_id,note,created_by) VALUES (?,'sell_as_is','old_gold_stock','sold_as_is','old_gold_sale',?,?,?)",(int(item_id),cur.lastrowid,notes,created_by));conn.commit()
    return {"sale_id":cur.lastrowid,"sale_no":no,"item_code":item["item_code"]}


def list_old_gold_batches(status=""):
    ensure_old_gold_schema();params=[];sql="""SELECT b.*,s.business_name refinery_name,(SELECT COUNT(*) FROM old_gold_batch_items bi WHERE bi.batch_id=b.id) item_count FROM old_gold_batches b LEFT JOIN suppliers s ON s.id=b.refinery_id WHERE 1=1"""
    if status:sql+=" AND b.status=?";params.append(status)
    sql+=" ORDER BY b.id DESC"
    with get_connection() as conn:rows=conn.execute(sql,params).fetchall()
    return [dict(x) for x in rows]

def get_old_gold_batch(batch_id):
    ensure_old_gold_schema()
    with get_connection() as conn:
        row=conn.execute("""SELECT b.*,s.business_name refinery_name,u.full_name created_by_name FROM old_gold_batches b
            LEFT JOIN suppliers s ON s.id=b.refinery_id LEFT JOIN users u ON u.id=b.created_by WHERE b.id=?""",(int(batch_id),)).fetchone()
        if not row:return None
        items=conn.execute("""SELECT i.item_code,i.item_type,i.description,i.net_weight,i.purity,i.acquisition_cost
            FROM old_gold_batch_items bi JOIN old_gold_items i ON i.id=bi.old_gold_item_id WHERE bi.batch_id=? ORDER BY i.id""",(int(batch_id),)).fetchall()
    result=dict(row);result['items']=[dict(x) for x in items];return result


ensure_old_gold_schema()
