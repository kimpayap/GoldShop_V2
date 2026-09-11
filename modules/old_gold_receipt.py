from pathlib import Path
import html, tempfile, webbrowser
from modules.terminology import display_terms
from modules.business_settings import get_business_settings
from modules.old_gold import get_old_gold_receipt,get_old_gold_batch
from modules.thai_datetime import format_thai_date, format_thai_datetime
from modules.qr_code import qr_data_uri

def _e(v): return html.escape(display_terms(v))

def build_old_gold_receipt(receipt_id):
    r=get_old_gold_receipt(receipt_id)
    if not r: raise ValueError("ไม่พบเอกสารทองเก่า")
    b=get_business_settings(); is_customer=r["source_type"]=="customer_buyback";source="ใบรับซื้อทองเก่า/ใบสำคัญจ่ายเงิน" if is_customer else "ใบรับเข้าสต็อกจากตั๋วหลุดขายฝาก"
    lines=[]
    for n,x in enumerate(r["items"],1):
        qr=qr_data_uri(x["qr_payload"],box_size=3)
        lines.append(f"<tr><td>{n}</td><td>{_e(x['item_code'])}<br><img src='{qr}' width='55'></td><td>{_e(x['ticket_no'] or '-')}</td><td>{_e(x['item_type'])} {_e(x['description'])}</td><td class='n'>{x['net_weight']:,.3f}</td><td class='n'>{x['purity']:,.2f}</td><td class='n'>{x['receipt_amount']:,.2f}</td></tr>")
    cancelled=f"<div class='cancel'>ยกเลิกรายการ<br>{_e(r['cancel_reason'])}</div>" if r["status"]=="cancelled" else ""
    seller=(f"<div class='seller'><b>ชื่อผู้ขาย:</b> {_e(r.get('first_name'))} &nbsp; <b>นามสกุล:</b> {_e(r.get('last_name'))}<br>"
            f"<b>เลขประจำตัวประชาชน/เลขประจำตัวผู้เสียภาษี:</b> {_e(r.get('citizen_id') or '-')}<br>"
            f"<b>ที่อยู่:</b> {_e(r.get('address') or '-')} &nbsp; <b>โทร:</b> {_e(r.get('phone') or '-')}</div>") if is_customer else "<div class='seller'><b>แหล่งที่มา:</b> ทรัพย์จากตั๋วหลุดขายฝาก</div>"
    declaration=("<div class='declare'>ข้าพเจ้าขอรับรองว่าสิ่งของตามรายการต่อไปนี้เป็นสมบัติของข้าพเจ้าโดยแท้จริง "
        "และขอรับรองว่าสิ่งของที่นำมาขายนั้นเป็นของที่บริสุทธิ์ หากเป็นของทุจริตแล้วข้าพเจ้าขอรับผิดชอบทั้งสิ้น "
        "และได้อ่านทวนเรียบร้อยแล้วจึงลงนามไว้เป็นหลักฐาน</div>") if is_customer else ""
    paper="9in 5.5in" if b.get("receipt_paper")=="9x5.5" else ("80mm auto" if b.get("receipt_paper")=="80mm" else "A4")
    price_note=(f"<p><b>ราคาทองแท่งรับซื้อปัจจุบัน:</b> {r['reference_gold_price']/(1-r['purchase_discount_rate']/100):,.2f} บาท/บาททอง &nbsp; <b>หัก:</b> {r['purchase_discount_rate']:.2f}% &nbsp; <b>ราคาในใบรับซื้อ:</b> {r['reference_gold_price']:,.2f} บาท/บาททอง</p>" if is_customer and r['purchase_discount_rate'] else "")
    return f"""<!doctype html><html lang='th'><head><meta charset='utf-8'><title>{source}</title><style>@page{{size:{paper};margin:.22in}}body{{font:10px Tahoma,'Noto Sans Thai',sans-serif;position:relative}}h1,h2,.c{{text-align:center}}h1{{font-size:17px;margin:0}}h2{{font-size:14px;margin:3px}}p{{margin:4px 0}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #333;padding:3px}}img{{width:32px!important;height:32px!important}}.n{{text-align:right}}.seller,.declare{{border:1px solid #333;padding:4px;margin:4px 0}}.cancel{{position:absolute;top:100px;left:30%;color:#c00;border:4px solid #c00;padding:14px;font-size:24px;font-weight:bold;transform:rotate(-12deg);text-align:center}}.sign{{display:grid;grid-template-columns:1fr 1fr;gap:45px;text-align:center;margin-top:20px}}@media print{{.np{{display:none}}}}</style></head><body><div class='np' style='text-align:right'><button onclick='print()'>พิมพ์</button></div>{cancelled}<h1>{_e(b['business_name'])}</h1><div class='c'>{_e(b['business_address'])} โทร {_e(b['business_phone'])} เลขผู้เสียภาษี {_e(b['business_tax_id'])}</div><h2>{source}</h2><p><b>เลขที่:</b> {_e(r['receipt_no'])} &nbsp; <b>วันที่:</b> {_e(format_thai_date(r['receipt_date']))}</p>{seller}{price_note}<table><thead><tr><th>#</th><th>รหัส/QR</th><th>เลขตั๋ว</th><th>รายการ</th><th>น้ำหนักสุทธิ</th><th>%ทอง</th><th>จำนวนเงินในใบรับซื้อ</th></tr></thead><tbody>{''.join(lines)}</tbody><tfoot><tr><th colspan='4'>รวม</th><th class='n'>{r['total_net_weight']:,.3f}</th><th></th><th class='n'>{r['receipt_total']:,.2f}</th></tr></tfoot></table><p><b>จำนวนเงินจ่ายจริง:</b> {r['paid_amount']:,.2f} บาท &nbsp; <b>ชำระโดย:</b> {_e(r['payment_method'])} &nbsp; <b>หมายเหตุ:</b> {_e(r['notes'] or '-')}</p>{declaration}<div class='sign'><div>ลงชื่อผู้ขาย/ผู้รับเงิน<br><br>___________________</div><div>ลงชื่อผู้จ่ายเงิน/ผู้ตรวจสอบ<br><br>___________________</div></div></body></html>"""

def print_old_gold_receipt(receipt_id):
    folder=Path(tempfile.gettempdir())/"GoldShop";folder.mkdir(parents=True,exist_ok=True);path=folder/f"old_gold_{receipt_id}.html";path.write_text(build_old_gold_receipt(receipt_id),encoding="utf-8")
    if not webbrowser.open(path.as_uri()): raise RuntimeError(f"ไม่สามารถเปิดเอกสารได้\nไฟล์อยู่ที่: {path}")
    return str(path)

def build_old_gold_batch_document(batch_id,document_type="batch"):
    x=get_old_gold_batch(batch_id)
    if not x:raise ValueError("ไม่พบล็อตทองเก่า")
    b=get_business_settings();title="ใบรวมล็อตทองเก่า" if document_type=="batch" else "ใบส่งมอบทองเก่าให้โรงหลอม"
    rows="".join(f"<tr><td>{n}</td><td>{_e(i['item_code'])}</td><td>{_e(i['item_type'])} {_e(i['description'])}</td><td class='n'>{i['net_weight']:,.3f}</td><td class='n'>{i['purity']:,.2f}</td><td class='n'>{i['acquisition_cost']:,.2f}</td></tr>" for n,i in enumerate(x['items'],1))
    refinery=(f"<p><b>โรงหลอม:</b> {_e(x.get('refinery_name') or '-')} &nbsp; <b>เลขที่ใบส่ง:</b> {_e(x.get('shipment_no') or '-')} &nbsp; <b>%ทองคาดหมาย:</b> {_e(x.get('expected_purity') or '-')}</p>" if document_type!='batch' else '')
    paper="9in 5.5in" if b.get("receipt_paper")=="9x5.5" else "A4"
    return f"""<!doctype html><html lang='th'><head><meta charset='utf-8'><style>@page{{size:{paper};margin:.22in}}body{{font:10px Tahoma,sans-serif}}h1,h2,.c{{text-align:center}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #333;padding:4px}}.n{{text-align:right}}@media print{{button{{display:none}}}}</style></head><body><button onclick='print()'>พิมพ์</button><h1>{_e(b['business_name'])}</h1><div class='c'>{_e(b['business_address'])}</div><h2>{title}</h2><p><b>เลขล็อต:</b> {_e(x['batch_no'])} &nbsp; <b>ชื่อล็อต:</b> {_e(x.get('batch_name') or '-')} &nbsp; <b>วันที่:</b> {_e(format_thai_datetime(x['created_at']))}<br><b>วัตถุประสงค์:</b> {_e(x.get('purpose') or '-')} &nbsp; <b>หมายเหตุ:</b> {_e(x.get('notes') or '-')}</p>{refinery}<table><tr><th>#</th><th>รหัส</th><th>รายการ</th><th>กรัม</th><th>%ทอง</th><th>ต้นทุน</th></tr>{rows}<tr><th colspan='3'>รวม {len(x['items'])} รายการ</th><th class='n'>{x['total_weight']:,.3f}</th><th></th><th class='n'>{x['total_cost']:,.2f}</th></tr></table><div class='c' style='margin-top:35px'>ลงชื่อผู้จัดทำ ____________________ &nbsp;&nbsp; ลงชื่อผู้ตรวจสอบ/ผู้รับมอบ ____________________</div></body></html>"""

def print_old_gold_batch_document(batch_id,document_type="batch"):
    folder=Path(tempfile.gettempdir())/"GoldShop";folder.mkdir(parents=True,exist_ok=True);path=folder/f"old_gold_batch_{document_type}_{batch_id}.html";path.write_text(build_old_gold_batch_document(batch_id,document_type),encoding="utf-8");webbrowser.open(path.as_uri());return str(path)
