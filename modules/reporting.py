from database.database import get_connection,init_db
from modules.operations_control import ensure_operations_schema


REPORT_TYPES = (
    "สรุปยอดขายฝาก/ต่อสัญญา", "วิเคราะห์ทรัพย์ขายฝาก", "สัญญาขายฝาก", "รับชำระขายฝาก", "ขายทองใหม่", "กำไรขั้นต้นขายทองใหม่",
    "รับซื้อทองเก่า", "สต็อกทองใหม่", "สต็อกทองเก่า", "ล็อตและโรงหลอม",
    "ความเคลื่อนไหวสต็อก", "ตรวจนับสต็อก", "ภาษีขาย", "กระแสเงินสด",
)


def _where_date(column, date_from, date_to):
    return f"date({column}) BETWEEN ? AND ?", [date_from, date_to]


def _rows(sql, params):
    with get_connection() as conn:return [dict(x) for x in conn.execute(sql, params).fetchall()]


def get_pawn_report_filters():
    init_db();ensure_operations_schema()
    with get_connection() as conn:
        types=[x[0] for x in conn.execute("SELECT item_type FROM (SELECT item_type FROM pawn_items UNION SELECT item_type FROM inventory_items UNION SELECT item_type FROM old_gold_items) WHERE item_type<>'' ORDER BY item_type")]
        details=[x[0] for x in conn.execute("SELECT description FROM (SELECT description FROM pawn_items UNION SELECT description FROM inventory_items UNION SELECT description FROM old_gold_items) WHERE description<>'' ORDER BY description")]
        purities=[x[0] for x in conn.execute("SELECT purity FROM (SELECT purity FROM pawn_items UNION SELECT purity FROM inventory_items UNION SELECT purity FROM old_gold_items) ORDER BY purity DESC")]
    return {"types":["ทั้งหมด"]+types,"details":["ทั้งหมด"]+details,"purities":["ทั้งหมด"]+[f"{x:g}%" for x in purities]}


def get_report(report_type, date_from, date_to, status="ทั้งหมด", series="ทั้งหมด", keyword="",transaction_type="ทั้งหมด",item_type="ทั้งหมด",item_detail="ทั้งหมด",purity="ทั้งหมด",group_by="ประเภทและรายละเอียด"):
    init_db();ensure_operations_schema();where,params=_where_date("opened_at",date_from,date_to);keyword=str(keyword or "").strip()
    if report_type=="สรุปยอดขายฝาก/ต่อสัญญา":
        filters=[]
        if transaction_type in {"ทั้งหมด","รับขายฝาก"}:
            sql="""SELECT p.series_code series,'รับขายฝาก' transaction_name,COUNT(*) records,SUM(p.loan_amount) total
                FROM pawn_tickets p WHERE date(p.opened_at) BETWEEN ? AND ?""";values=[date_from,date_to]
            if series!="ทั้งหมด":sql+=" AND p.series_code=?";values.append(series)
            if status!="ทั้งหมด":sql+=" AND p.status=?";values.append(status)
            if keyword:sql+=" AND p.ticket_no LIKE ?";values.append(f"%{keyword}%")
            sql+=" GROUP BY p.series_code";filters.extend(_rows(sql,values))
        tx_map={"ต่อสัญญา":"renew","ไถ่ถอน":"redeem"}
        for label,code in tx_map.items():
            if transaction_type not in {"ทั้งหมด",label}:continue
            sql="""SELECT p.series_code series,? transaction_name,COUNT(*) records,SUM(t.amount) total
                FROM pawn_transactions t JOIN pawn_tickets p ON p.id=t.pawn_ticket_id
                WHERE date(t.transaction_at) BETWEEN ? AND ? AND t.transaction_type=? AND t.transaction_status='completed'""";values=[label,date_from,date_to,code]
            if series!="ทั้งหมด":sql+=" AND p.series_code=?";values.append(series)
            if keyword:sql+=" AND (p.ticket_no LIKE ? OR t.tax_document_no LIKE ?)";values += [f"%{keyword}%"]*2
            sql+=" GROUP BY p.series_code";filters.extend(_rows(sql,values))
        return [{"id":n,"report_date":date_to,"document_no":x['series'],"category":x['transaction_name']+" ระบบ "+x['series'],"party":"-","detail":f"รวม {x['records']:,} รายการ","quantity":x['records'],"weight":0,"amount_in":x['total'] or 0,"amount_out":0,"vat":0,"status":"สรุป","secondary_date":None} for n,x in enumerate(filters,1)]
    if report_type=="วิเคราะห์ทรัพย์ขายฝาก":
        groups={"ประเภทสินค้า":("pi.item_type","pi.item_type"),"รายละเอียดสินค้า":("pi.description","pi.description"),"เปอร์เซ็นต์ทอง":("printf('%g%%',pi.purity)","pi.purity"),"ประเภทและรายละเอียด":("pi.item_type||' / '||pi.description","pi.item_type,pi.description")}
        label_expr,group_expr=groups.get(group_by,groups["ประเภทและรายละเอียด"]);where,params=_where_date("p.opened_at",date_from,date_to);extra=""
        if status!="ทั้งหมด":extra+=" AND p.status=?";params.append(status)
        if series!="ทั้งหมด":extra+=" AND p.series_code=?";params.append(series)
        if item_type!="ทั้งหมด":extra+=" AND pi.item_type=?";params.append(item_type)
        if item_detail!="ทั้งหมด":extra+=" AND pi.description=?";params.append(item_detail)
        if purity!="ทั้งหมด":extra+=" AND ABS(pi.purity-?)<0.001";params.append(float(str(purity).replace('%','')))
        if keyword:extra+=" AND (p.ticket_no LIKE ? OR pi.item_type LIKE ? OR pi.description LIKE ? OR c.first_name||' '||c.last_name LIKE ?)";params += [f"%{keyword}%"]*4
        return _rows(f"""SELECT MIN(pi.id) id,MAX(date(p.opened_at)) report_date,'-' document_no,{label_expr} category,'-' party,
          'จำนวนสัญญา '||COUNT(DISTINCT p.id)||' ฉบับ' detail,COUNT(pi.id) quantity,SUM(pi.weight_grams) weight,
          SUM(CASE WHEN COALESCE((SELECT SUM(x.estimated_value) FROM pawn_items x WHERE x.pawn_ticket_id=p.id),0)>0
            THEN p.loan_amount*pi.estimated_value/(SELECT SUM(x.estimated_value) FROM pawn_items x WHERE x.pawn_ticket_id=p.id)
            ELSE p.loan_amount/(SELECT COUNT(*) FROM pawn_items x WHERE x.pawn_ticket_id=p.id) END) amount_in,
          0 amount_out,0 vat,'สรุป' status,NULL secondary_date
          FROM pawn_items pi JOIN pawn_tickets p ON p.id=pi.pawn_ticket_id JOIN customers c ON c.id=p.customer_id
          WHERE {where}{extra} GROUP BY {group_expr} ORDER BY weight DESC""",params)
    if report_type=="สัญญาขายฝาก":
        extra=""
        if status!="ทั้งหมด":extra+=" AND p.status=?";params.append(status)
        if series!="ทั้งหมด":extra+=" AND p.series_code=?";params.append(series)
        if keyword:extra+=" AND (p.ticket_no LIKE ? OR c.first_name||' '||c.last_name LIKE ? OR c.citizen_id LIKE ?)";params += [f"%{keyword}%"]*3
        return _rows(f"""SELECT p.id,date(p.opened_at) report_date,p.ticket_no document_no,'ขายฝาก '||p.series_code category,
          c.first_name||' '||c.last_name party,(SELECT GROUP_CONCAT(item_type||' '||description,', ') FROM pawn_items WHERE pawn_ticket_id=p.id) detail,
          (SELECT COUNT(*) FROM pawn_items WHERE pawn_ticket_id=p.id) quantity,(SELECT COALESCE(SUM(weight_grams),0) FROM pawn_items WHERE pawn_ticket_id=p.id) weight,
          p.loan_amount amount_in,0 amount_out,0 vat,p.status status,p.due_date secondary_date
          FROM pawn_tickets p JOIN customers c ON c.id=p.customer_id WHERE {where}{extra} ORDER BY p.opened_at""",params)
    if report_type=="รับชำระขายฝาก":
        where,params=_where_date("t.transaction_at",date_from,date_to);extra=""
        if status!="ทั้งหมด":extra+=" AND t.transaction_status=?";params.append(status)
        if series!="ทั้งหมด":extra+=" AND p.series_code=?";params.append(series)
        if keyword:extra+=" AND (p.ticket_no LIKE ? OR c.first_name||' '||c.last_name LIKE ?)";params += [f"%{keyword}%"]*2
        return _rows(f"""SELECT t.id,date(t.transaction_at) report_date,COALESCE(t.tax_document_no,p.ticket_no) document_no,
          CASE t.transaction_type WHEN 'renew' THEN 'ต่อสัญญา '||p.series_code WHEN 'redeem' THEN 'ไถ่ถอน '||p.series_code ELSE t.transaction_type END category,
          c.first_name||' '||c.last_name party,p.ticket_no detail,1 quantity,0 weight,
          CASE WHEN t.transaction_status='completed' THEN t.amount ELSE 0 END amount_in,0 amount_out,t.vat_amount vat,t.transaction_status status,NULL secondary_date
          FROM pawn_transactions t JOIN pawn_tickets p ON p.id=t.pawn_ticket_id JOIN customers c ON c.id=p.customer_id WHERE {where}{extra} ORDER BY t.transaction_at""",params)
    if report_type in {"ขายทองใหม่","กำไรขั้นต้นขายทองใหม่"}:
        where,params=_where_date("s.sale_date",date_from,date_to);extra=""
        if status!="ทั้งหมด":extra+=" AND s.status=?";params.append(status)
        if keyword:extra+=" AND (s.sale_no LIKE ? OR s.customer_name LIKE ? OR s.customer_tax_id LIKE ?)";params += [f"%{keyword}%"]*3
        product_filters=[];product_values=[]
        if item_type!="ทั้งหมด":product_filters.append("si.item_type=?");product_values.append(item_type)
        if item_detail!="ทั้งหมด":product_filters.append("si.description=?");product_values.append(item_detail)
        if purity!="ทั้งหมด":product_filters.append("ABS(si.purity-?)<0.001");product_values.append(float(str(purity).replace('%','')))
        if product_filters:extra+=" AND EXISTS(SELECT 1 FROM gold_sale_items si WHERE si.sale_id=s.id AND "+" AND ".join(product_filters)+")";params += product_values
        profit="s.grand_total-COALESCE((SELECT SUM(i.total_cost) FROM gold_sale_items si JOIN inventory_items i ON i.id=si.inventory_item_id WHERE si.sale_id=s.id),0)"
        return _rows(f"""SELECT s.id,s.sale_date report_date,s.sale_no document_no,'ขายทองใหม่' category,s.customer_name party,
          (SELECT GROUP_CONCAT(item_code||' '||description,', ') FROM gold_sale_items WHERE sale_id=s.id) detail,
          (SELECT COUNT(*) FROM gold_sale_items WHERE sale_id=s.id) quantity,(SELECT COALESCE(SUM(weight_grams),0) FROM gold_sale_items WHERE sale_id=s.id) weight,
          {profit if report_type=='กำไรขั้นต้นขายทองใหม่' else 's.amount_paid'} amount_in,
          {f's.grand_total-({profit})' if report_type=='กำไรขั้นต้นขายทองใหม่' else '0'} amount_out,s.vat_amount vat,s.status status,NULL secondary_date
          FROM gold_sales s WHERE {where}{extra} ORDER BY s.sale_date,s.id""",params)
    if report_type=="รับซื้อทองเก่า":
        where,params=_where_date("r.receipt_date",date_from,date_to);extra=""
        if status!="ทั้งหมด":extra+=" AND r.status=?";params.append(status)
        if keyword:extra+=" AND (r.receipt_no LIKE ? OR c.first_name||' '||c.last_name LIKE ?)";params += [f"%{keyword}%"]*2
        return _rows(f"""SELECT r.id,r.receipt_date report_date,r.receipt_no document_no,
          CASE r.source_type WHEN 'customer_buyback' THEN 'รับซื้อจากลูกค้า' ELSE 'รับจากตั๋วหลุด' END category,
          COALESCE(c.first_name||' '||c.last_name,'ตั๋วหลุดขายฝาก') party,r.notes detail,
          (SELECT COUNT(*) FROM old_gold_items WHERE old_gold_receipt_id=r.id) quantity,r.total_net_weight weight,0 amount_in,r.paid_amount amount_out,0 vat,r.status status,NULL secondary_date
          FROM old_gold_receipts r LEFT JOIN customers c ON c.id=r.customer_id WHERE {where}{extra} ORDER BY r.receipt_date,r.id""",params)
    if report_type in {"สต็อกทองใหม่","สต็อกทองเก่า"}:
        if report_type=="สต็อกทองใหม่":
            where,params=_where_date("i.acquired_at",date_from,date_to);sql=f"""SELECT i.id,date(i.acquired_at) report_date,i.item_code document_no,'ทองใหม่' category,
              COALESCE(s.business_name,'-') party,i.item_type||' '||i.description detail,1 quantity,i.weight_grams weight,0 amount_in,i.total_cost amount_out,0 vat,i.status status,NULL secondary_date
              FROM inventory_items i LEFT JOIN suppliers s ON s.id=i.supplier_id WHERE {where}"""
        else:
            where,params=_where_date("i.created_at",date_from,date_to);sql=f"""SELECT i.id,date(i.created_at) report_date,i.item_code document_no,'ทองเก่า' category,
              CASE i.source_type WHEN 'customer_buyback' THEN 'ลูกค้าขาย' ELSE 'ตั๋วหลุด' END party,i.item_type||' '||i.description detail,i.quantity quantity,i.net_weight weight,
              0 amount_in,i.acquisition_cost amount_out,0 vat,i.status status,NULL secondary_date FROM old_gold_items i WHERE {where}"""
        if status!="ทั้งหมด":sql+=" AND i.status=?";params.append(status)
        if item_type!="ทั้งหมด":sql+=" AND i.item_type=?";params.append(item_type)
        if item_detail!="ทั้งหมด":sql+=" AND i.description=?";params.append(item_detail)
        if purity!="ทั้งหมด":sql+=" AND ABS(i.purity-?)<0.001";params.append(float(str(purity).replace('%','')))
        if keyword:sql+=" AND (i.item_code LIKE ? OR i.description LIKE ?)";params += [f"%{keyword}%"]*2
        return _rows(sql+" ORDER BY report_date,document_no",params)
    if report_type=="ล็อตและโรงหลอม":
        where,params=_where_date("b.created_at",date_from,date_to);extra=""
        if status!="ทั้งหมด":extra+=" AND b.status=?";params.append(status)
        if keyword:extra+=" AND (b.batch_no LIKE ? OR b.batch_name LIKE ? OR s.business_name LIKE ?)";params += [f"%{keyword}%"]*3
        return _rows(f"""SELECT b.id,date(b.created_at) report_date,b.batch_no document_no,'ล็อตทองเก่า' category,COALESCE(s.business_name,'-') party,
          COALESCE(b.batch_name,'')||' '||COALESCE(b.purpose,'') detail,(SELECT COUNT(*) FROM old_gold_batch_items WHERE batch_id=b.id) quantity,b.total_weight weight,
          0 amount_in,b.total_cost+COALESCE(b.service_cost,0) amount_out,0 vat,b.status status,b.received_at secondary_date
          FROM old_gold_batches b LEFT JOIN suppliers s ON s.id=b.refinery_id WHERE {where}{extra} ORDER BY b.created_at""",params)
    if report_type=="ความเคลื่อนไหวสต็อก":
        where,params=_where_date("m.created_at",date_from,date_to);extra=""
        if keyword:extra+=" AND (i.item_code LIKE ? OR m.movement_type LIKE ?)";params += [f"%{keyword}%"]*2
        return _rows(f"""SELECT m.id,date(m.created_at) report_date,i.item_code document_no,'ทองใหม่' category,'-' party,
          m.movement_type||' : '||COALESCE(m.from_status,'-')||' → '||m.to_status detail,1 quantity,i.weight_grams weight,0 amount_in,0 amount_out,0 vat,m.movement_status status,NULL secondary_date
          FROM stock_movements m JOIN inventory_items i ON i.id=m.inventory_item_id WHERE {where}{extra} ORDER BY m.created_at""",params)
    if report_type=="ตรวจนับสต็อก":
        where,params=_where_date("c.count_date",date_from,date_to);extra=""
        if status!="ทั้งหมด":extra+=" AND c.status=?";params.append(status)
        return _rows(f"""SELECT c.id,c.count_date report_date,c.count_no document_no,CASE c.count_type WHEN 'new_gold' THEN 'ตรวจทองใหม่' ELSE 'ตรวจทองเก่า' END category,
          COALESCE(c.location,'-') party,'ขาด '||c.missing_count||' / เกิน '||c.unexpected_count detail,c.counted_count quantity,0 weight,0 amount_in,0 amount_out,0 vat,c.status status,c.finalized_at secondary_date
          FROM stock_counts c WHERE {where}{extra} ORDER BY c.count_date,c.id""",params)
    if report_type=="ภาษีขาย":
        from modules.operations_control import tax_report
        return [{"id":n,"report_date":x['document_date'],"document_no":x['document_no'],"category":x['document_type'],"party":x.get('party',''),"detail":"ฐานภาษี {:,.2f}".format(x['vat_base']),"quantity":1,"weight":0,"amount_in":x['total_amount'],"amount_out":0,"vat":x['vat_amount'],"status":x['status'],"secondary_date":None} for n,x in enumerate(tax_report(date_from,date_to),1)]
    if report_type=="กระแสเงินสด":
        rows=[]
        from datetime import date,timedelta
        from modules.operations_control import cash_report
        current=date.fromisoformat(date_from);end=date.fromisoformat(date_to);n=0
        while current<=end:
            for x in cash_report(current.isoformat()):
                n+=1;rows.append({"id":n,"report_date":current.isoformat(),"document_no":x['document_no'],"category":x['category'],"party":x['payment_method'],"detail":"","quantity":1,"weight":0,"amount_in":x['cash_in'],"amount_out":x['cash_out'],"vat":0,"status":"completed","secondary_date":None})
            current+=timedelta(days=1)
        return rows
    return []


def summarize_report(rows):
    return {"records":len(rows),"quantity":sum(float(x.get('quantity') or 0) for x in rows),"weight":sum(float(x.get('weight') or 0) for x in rows),
        "amount_in":sum(float(x.get('amount_in') or 0) for x in rows),"amount_out":sum(float(x.get('amount_out') or 0) for x in rows),"vat":sum(float(x.get('vat') or 0) for x in rows)}
