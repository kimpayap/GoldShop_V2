from pathlib import Path
import html
import tempfile
import webbrowser
from modules.terminology import display_terms

from modules.business_settings import get_business_settings
from modules.pawn import get_forfeit_batch
from modules.thai_datetime import format_thai_date, format_thai_datetime


def _e(value):
    return html.escape(display_terms(value))


def build_forfeit_batch_document(batch_id):
    batch = get_forfeit_batch(batch_id)
    if not batch:
        raise ValueError("ไม่พบชุดยืนยันตั๋วหลุดขายฝาก")
    business = get_business_settings()
    rows = []
    index = 0
    total_weight = 0.0
    for ticket in batch["tickets"]:
        items = ticket.get("items") or [{}]
        for item_index, item in enumerate(items):
            index += 1
            weight = float(item.get("weight_grams") or 0)
            total_weight += weight
            loan_display = f"{float(ticket['loan_amount']):,.2f}" if item_index == 0 else "-"
            rows.append(f"""<tr><td>{index}</td><td>{_e(ticket['ticket_no'])}</td>
                <td>{_e(ticket['first_name'])} {_e(ticket['last_name'])}</td>
                <td>{_e(item.get('item_type'))}</td><td>{_e(item.get('description'))}</td>
                <td class='num'>{float(item.get('purity') or 0):,.2f}</td>
                <td class='num'>{weight:,.3f}</td><td class='num'>{loan_display}</td></tr>""")
    paper = business.get("receipt_paper", "A4")
    page = "9in 5.5in" if paper == "9x5.5" else ("80mm auto" if paper == "80mm" else "A4")
    return f"""<!doctype html><html lang='th'><head><meta charset='utf-8'><title>รายการตั๋วหลุด {_e(batch['batch_no'])}</title>
    <style>@page{{size:{page};margin:10mm}}body{{font-family:Tahoma,'Noto Sans Thai',sans-serif;font-size:12px}}
    h1,h2,.center{{text-align:center}}h1{{margin:0}}h2{{margin:8px}}table{{width:100%;border-collapse:collapse}}
    th,td{{border:1px solid #333;padding:5px}}th{{background:#eee}}.num{{text-align:right}}.meta{{display:grid;grid-template-columns:1fr 1fr;gap:5px;margin:10px 0}}
    .sign{{display:grid;grid-template-columns:1fr 1fr;gap:80px;margin-top:45px;text-align:center}}@media print{{.no-print{{display:none}}}}</style></head><body>
    <div class='no-print' style='text-align:right'><button onclick='window.print()'>พิมพ์เอกสาร</button></div>
    <h1>{_e(business['business_name'])}</h1><div class='center'>{_e(business['business_address'])}<br>โทร {_e(business['business_phone'])}</div>
    <h2>เอกสารยืนยันรายการสินค้าหลุดขายฝาก</h2>
    <div class='meta'><div><b>เลขที่ชุด:</b> {_e(batch['batch_no'])}</div><div><b>วันที่:</b> {_e(format_thai_datetime(batch['created_at']))}</div>
    <div><b>ผู้ยืนยัน:</b> {_e(batch.get('created_by_name') or '-')}</div><div><b>จำนวน:</b> {batch['ticket_count']} ตั๋ว</div></div>
    <table><thead><tr><th>#</th><th>เลขตั๋ว</th><th>ลูกค้า</th><th>ประเภท</th><th>รายละเอียด</th><th>%ทอง</th><th>น้ำหนัก</th><th>เงินต้น</th></tr></thead>
    <tbody>{''.join(rows)}</tbody><tfoot><tr><th colspan='6'>รวม</th><th class='num'>{total_weight:,.3f}</th><th class='num'>{float(batch['total_loan']):,.2f}</th></tr></tfoot></table>
    <p><b>หมายเหตุ:</b> {_e(batch.get('note') or '-')}</p><p>เอกสารนี้เป็นหลักฐานการยืนยันสถานะตั๋วหลุดขายฝาก และยังไม่ถือว่าโอนสินค้าเข้าสู่สต็อกทองเก่า</p>
    <div class='sign'><div>ลงชื่อผู้จัดทำ<br><br>________________________</div><div>ลงชื่อผู้ตรวจสอบ/อนุมัติ<br><br>________________________</div></div></body></html>"""


def print_forfeit_batch_document(batch_id):
    doc = build_forfeit_batch_document(batch_id)
    folder = Path(tempfile.gettempdir()) / "GoldShop"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"forfeit_batch_{int(batch_id)}.html"
    path.write_text(doc, encoding="utf-8")
    if not webbrowser.open(path.as_uri()):
        raise RuntimeError(f"ไม่สามารถเปิดเอกสารได้\nไฟล์อยู่ที่: {path}")
    return str(path)
