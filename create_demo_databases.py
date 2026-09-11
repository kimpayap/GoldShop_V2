from pathlib import Path
from datetime import date,timedelta,datetime
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import database.database as db


def initialize(path,mode):
    if path.exists():path.unlink()
    db.DB_PATH=path;db.init_db()
    from modules.pawn import ensure_pawn_schema
    from modules.stock import ensure_stock_schema
    from modules.sales import ensure_sales_schema
    ensure_pawn_schema();ensure_stock_schema();ensure_sales_schema()
    with db.get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO app_settings(setting_key,setting_value) VALUES ('database_mode',?)",(mode,))
        conn.execute("INSERT OR REPLACE INTO app_settings(setting_key,setting_value) VALUES ('business_name',?)",("ร้านทองตัวอย่าง — ข้อมูลทดสอบ" if mode=="demo" else "ร้านทอง",))
        conn.commit()


def seed_demo(path):
    db.DB_PATH=path
    from modules.stock import confirm_new_gold_receipt,list_inventory
    from modules.sales import calculate_sale_item,confirm_gold_sale
    from modules.pawn import create_pawn,get_settings
    today=date.today();now=datetime.now()
    with db.get_connection() as conn:
        conn.execute("DELETE FROM users")
        conn.execute("INSERT INTO users(username,password,full_name,role,active) VALUES ('admin','admin123','ผู้ดูแลระบบ (ทดลอง)','admin',1)")
        conn.execute("INSERT INTO users(username,password,full_name,role,active) VALUES ('staff','staff123','พนักงานทดลอง','staff',1)")
        customers=[
            ("CDEMO001","สมชาย","ข้อมูลทดสอบ","DEMO-CID-001","0800000001","กรุงเทพฯ"),("CDEMO002","สมหญิง","ข้อมูลทดสอบ","DEMO-CID-002","0800000002","นนทบุรี"),
            ("CDEMO003","อนันต์","ตัวอย่าง","DEMO-CID-003","0800000003","ปทุมธานี"),("CDEMO004","กานดา","ตัวอย่าง","DEMO-CID-004","0800000004","สมุทรปราการ"),
            ("CDEMO005","ณัฐ","ระบบทดลอง","DEMO-CID-005","0800000005","ชลบุรี"),("CDEMO006","มาลี","ระบบทดลอง","DEMO-CID-006","0800000006","เชียงใหม่"),
            ("CDEMO007","วีระ","ข้อมูลจำลอง","DEMO-CID-007","0800000007","ขอนแก่น"),("CDEMO008","นภา","ข้อมูลจำลอง","DEMO-CID-008","0800000008","ภูเก็ต"),
        ]
        conn.executemany("INSERT INTO customers(customer_code,first_name,last_name,citizen_id,phone,address,note) VALUES (?,?,?,?,?,?, 'ข้อมูลทดสอบ ห้ามใช้จริง')",customers)
        suppliers=[("SUPDEMO01","ผู้จำหน่าย","บริษัททองตัวอย่าง จำกัด","DEMO-TAX-001","ผู้ติดต่อทดลอง","0200000001","กรุงเทพฯ"),("SUPDEMO02","ผู้จำหน่ายและคู่ค้า","ห้างหุ้นส่วนลายทองจำลอง","DEMO-TAX-002","ฝ่ายขายทดลอง","0200000002","นครปฐม"),("SUPDEMO03","คู่ค้า","โรงงานทองข้อมูลทดสอบ","DEMO-TAX-003","ฝ่ายผลิตทดลอง","0200000003","สมุทรสาคร")]
        conn.executemany("INSERT INTO suppliers(supplier_code,supplier_type,business_name,tax_id,contact_name,phone,address,notes,active) VALUES (?,?,?,?,?,?,?,'ข้อมูลทดสอบ',1)",suppliers)
        for offset,values in enumerate(((69650,69850,68250,70650),(69500,69700,68100,70500),(69700,69900,68300,70700),(69400,69600,68000,70400),(69800,70000,68400,70800))):
            d=(today-timedelta(days=offset)).isoformat();conn.execute("INSERT INTO gold_prices(price_date,price_time,announcement_no,gold_bar_buy,gold_bar_sell,gold_jewelry_tax,gold_jewelry_sell,source) VALUES (?,?,?,?,?,?,?,'demo')",(d,"10:00",offset+1,*values))
        conn.commit()
        admin=conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()["id"]
        supplier_ids=[x["id"] for x in conn.execute("SELECT id FROM suppliers ORDER BY id").fetchall()]
        details={x["name"]:x["id"] for x in conn.execute("SELECT id,name FROM gold_details").fetchall()}

    receipt_specs=[
        (supplier_ids[0],"สร้อยคอ",96.5,15.244,5,69650,850,72500,"ตู้ A-01"),(supplier_ids[0],"แหวน",96.5,3.811,6,17412.5,350,18500,"ถาด A-02"),
        (supplier_ids[1],"สร้อยข้อมือ",96.5,7.622,4,34825,600,37000,"ตู้ B-01"),(supplier_ids[1],"กำไล",96.5,15.244,3,69650,900,73000,"ตู้ B-02"),
        (supplier_ids[2],"ต่างหู",90.0,3.811,4,16240,450,17800,"ถาด C-01"),(supplier_ids[2],"จี้",96.5,1.906,5,8706,300,9500,"ถาด C-02"),
    ]
    for index,(sid,detail,purity,weight,qty,cost,work,sale_price,location) in enumerate(receipt_specs,1):
        confirm_new_gold_receipt({"supplier_id":sid,"received_date":(today-timedelta(days=10-index)).isoformat(),"supplier_document_no":f"DEMO-GRN-{index:03d}","tax_invoice_no":f"DEMO-TAXINV-{index:03d}","document_date":today.isoformat(),"reference_gold_price":69650,"invoice_vat_amount":round(qty*work*.07,2),"payment_type":"เครดิต" if index%2==0 else "เงินสด","notes":"ข้อมูลรับทองทดสอบ"},[{"item_type":"ทองรูปพรรณ","description":detail,"gold_detail_id":details.get(detail),"purity":purity,"weight_grams":weight,"quantity":qty,"gold_cost":cost,"workmanship_cost":work,"discount":0,"suggested_sale_price":sale_price,"storage_location":location,"notes":"สินค้าทดสอบ"}],admin)

    inventory=list_inventory("","in_stock")
    methods=[("เงินสด",0),("โอนเงิน",0),("บัตรเครดิต",3)]
    for index,(method,fee) in enumerate(methods):
        item=inventory[index];line=calculate_sale_item(item,float(item["suggested_sale_price"]),68400,get_settings()["weight_per_baht_gram"])
        paid=round(line["total_incl_vat"]*(1+fee/100),2)
        confirm_gold_sale({"sale_date":today.isoformat(),"customer_name":f"ลูกค้าขายทดลอง {index+1}","customer_tax_id":f"DEMO-SALE-TAX-{index+1}","payment_method":method,"card_fee_rate":fee,"amount_paid":paid,"notes":"รายการขายทดสอบ"},[line],admin)

    with db.get_connection() as conn:customer_ids=[x["id"] for x in conn.execute("SELECT id FROM customers ORDER BY id LIMIT 6").fetchall()]
    pawn_ids=[]
    pawn_specs=[
        (customer_ids[0],12000,"active",today+timedelta(days=70)),(customer_ids[1],8500,"active",today+timedelta(days=5)),
        (customer_ids[2],15000,"active",today),(customer_ids[3],22000,"active",today-timedelta(days=12)),
        (customer_ids[4],9500,"redeemed",today-timedelta(days=30)),(customer_ids[5],18000,"forfeited",today-timedelta(days=60)),
    ]
    for index,(cid,loan,status,due) in enumerate(pawn_specs,1):
        item={"item_type":"ทองรูปพรรณ","description":["สร้อยคอ","แหวน","สร้อยข้อมือ","กำไล","ต่างหู","จี้"][index-1],"purity":96.5,"weight_grams":15.244 if index%2 else 7.622,"gold_price_per_baht":69650,"estimated_value":69650 if index%2 else 34825,"loan_value":loan}
        pid,_=create_pawn(cid,loan,[item],"ข้อมูลขายฝากทดสอบ",admin);pawn_ids.append(pid)
        with db.get_connection() as conn:
            opened=(now-timedelta(days=50+index*5)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("UPDATE pawn_tickets SET status=?,opened_at=?,due_date=? WHERE id=?",(status,opened,due.isoformat(),pid))
            if status=="redeemed":conn.execute("UPDATE pawn_tickets SET redeemed_at=?,redeemed_amount=? WHERE id=?",(now.isoformat(timespec="seconds"),loan,pid))
            if status=="forfeited":conn.execute("UPDATE pawn_tickets SET forfeited_at=?,forfeit_note='ตั๋วหลุดข้อมูลทดสอบ' WHERE id=?",(now.isoformat(timespec="seconds"),pid))
            conn.commit()
    with db.get_connection() as conn:
        conn.execute("INSERT INTO pawn_renewals(pawn_ticket_id,renew_months,interest_amount,paid_amount,previous_due_date,new_due_date,note,created_by) VALUES (?,?,?,?,?,?,?,?)",(pawn_ids[0],1,240,240,(today+timedelta(days=40)).isoformat(),(today+timedelta(days=70)).isoformat(),"ต่อดอกทดสอบ",admin))
        conn.execute("INSERT OR REPLACE INTO app_settings(setting_key,setting_value) VALUES ('database_mode','demo')")
        conn.commit()


if __name__=="__main__":
    demo=ROOT/"database"/"gold_shop_demo.db";empty=ROOT/"database"/"gold_shop_empty.db"
    initialize(demo,"demo");seed_demo(demo);initialize(empty,"real")
    print(f"created: {demo}")
    print(f"created: {empty}")
