from pathlib import Path
from datetime import datetime
import html
import webbrowser
import tempfile

from database.database import get_connection
from modules.pawn import get_pawn
from modules.thai_datetime import format_thai_date, format_thai_datetime
from modules.business_settings import get_business_settings
from modules.qr_code import pawn_qr_payload, qr_data_uri
from modules.terminology import display_terms


def _esc(value):
    return html.escape(display_terms(value))


def build_pawn_receipt(ticket_id):
    pawn = get_pawn(ticket_id)
    if not pawn:
        raise ValueError("ไม่พบใบรับขายฝาก")

    business = get_business_settings()
    items_html = []
    for i, item in enumerate(pawn.get("items", []), 1):
        items_html.append(
            f"""
            <tr>
              <td>{i}</td>
              <td>{_esc(item["item_type"])}</td>
              <td>{_esc(item["description"])}</td>
              <td class="num">{float(item["purity"]):,.2f}</td>
              <td class="num">{float(item["weight_grams"]):,.2f}</td>
              <td class="num">{float(item["estimated_value"] or 0):,.2f}</td>
              <td class="num">{float(item["loan_value"] or 0):,.2f}</td>
            </tr>
            """
        )

    created = format_thai_datetime(pawn["opened_at"])
    pawn_qr = qr_data_uri(pawn_qr_payload(pawn["ticket_no"]), box_size=5)
    page_css = _page_css(business["receipt_paper"])
    html_doc = f"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<title>ใบรับขายฝาก { _esc(pawn["ticket_no"]) }</title>
<style>
@page {{ size: {page_css}; }}
body {{ position:relative; font-family: Tahoma, "Noto Sans Thai", sans-serif; font-size: 14px; color:#111; }}
h1 {{ text-align:center; margin:0 0 4px; font-size:24px; }}
h2 {{ text-align:center; margin:0 0 18px; font-size:17px; font-weight:normal; }}
.meta {{ display:grid; grid-template-columns:1fr 1fr; gap:6px 20px; margin-bottom:12px; }}
.box {{ border:1px solid #333; padding:8px; }}
table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
th,td {{ border:1px solid #333; padding:6px; }}
th {{ background:#eee; }}
.num {{ text-align:right; }}
.total {{ width:360px; margin-left:auto; margin-top:12px; }}
.total td {{ font-weight:bold; }}
.note {{ border:1px solid #333; min-height:55px; padding:8px; margin-top:12px; }}
.contract-terms {{ font-size:10px; line-height:1.35; margin-top:9px; text-align:justify; }}
.contract-terms p {{ margin:3px 0; }}
.sign {{ display:grid; grid-template-columns:1fr 1fr; gap:60px; margin-top:55px; text-align:center; }}
.pawn-qr {{ position:absolute; right:0; top:34px; width:105px; text-align:center; font-size:8px; overflow-wrap:anywhere; }} .pawn-qr img {{ width:95px; height:95px; }}
.receipt-head {{ padding-left:110px; padding-right:110px; min-height:115px; }}
@media print {{ .no-print {{ display:none; }} }}
</style>
</head>
<body>
<div class="no-print" style="text-align:right;margin-bottom:10px">
<button onclick="window.print()">พิมพ์ใบรับขายฝาก</button>
</div>

<div class="pawn-qr"><img src="{pawn_qr}" alt="QR ใบขายฝาก"><br>{_esc(pawn_qr_payload(pawn['ticket_no']))}</div>
<div class="receipt-head">
<h1>{_esc(business['business_name'])}</h1>
<div style="text-align:center">{_esc(business['business_address'])}<br>โทร {_esc(business['business_phone'])} &nbsp; เลขผู้เสียภาษี {_esc(business['business_tax_id'])}</div>
<h2>สัญญาขายฝาก ระบบ {_esc(pawn.get('series_code','P'))}</h2>
</div>

<div class="meta">
  <div class="box"><b>เลขที่ตั๋ว:</b> {_esc(pawn["ticket_no"])}</div>
  <div class="box"><b>วันที่ทำรายการ:</b> {_esc(created)}</div>
  <div class="box"><b>รหัสลูกค้า:</b> {_esc(pawn["customer_code"])}</div>
  <div class="box"><b>วันครบกำหนด:</b> {_esc(format_thai_date(pawn["due_date"]))}</div>
  <div class="box"><b>ชุดสัญญา:</b> ระบบ {_esc(pawn.get("series_code","P"))}</div>
  <div class="box"><b>ระยะเวลาสัญญา:</b> {int(pawn.get("contract_term_days") or 120)} วัน</div>
  <div class="box"><b>ลูกค้า:</b> {_esc(pawn["first_name"])} {_esc(pawn["last_name"])}</div>
  <div class="box"><b>เลขบัตรประชาชน:</b> {_esc(pawn["citizen_id"])}</div>
</div>

<table>
<thead>
<tr>
<th>ลำดับ</th><th>ประเภท</th><th>รายละเอียด</th><th>%ทอง</th>
<th>น้ำหนัก (กรัม)</th><th>ราคาประเมิน</th><th>วงเงิน</th>
</tr>
</thead>
<tbody>
{''.join(items_html)}
</tbody>
</table>

<table class="total">
<tr><td>เงินต้นขายฝาก</td><td class="num">{float(pawn["loan_amount"]):,.2f} บาท</td></tr>
</table>

<div class="note"><b>หมายเหตุ:</b><br>{_esc(pawn["notes"])}</div>

<div class="contract-terms">
<p>นับตั้งแต่วันที่ขายฝากหรือชำระค่าตอบแทนล่าสุด หากข้าพเจ้าไม่ดำเนินการตามที่กำหนดถือว่าสละสิทธิ์ในสิ่งของตามรายการดังกล่าวให้เป็นสิทธิ์แก่ทางร้าน</p>
<p>ขอรับรองว่าสิ่งของตามรายการเป็นของข้าพเจ้าที่ได้มาโดยชอบธรรมและไม่ใช่สิ่งของที่ได้มาจากการกระทำผิดกฎหมาย</p>
<p>เอกสารฉบับนี้ถือเป็นสำคัญและบุคคลที่ถือเอกสารฉบับนี้มีสิทธิแทนข้าพเจ้าทุกประการ ข้าพเจ้าได้อ่านและเข้าใจดีแล้วจึงลงรายมือชื่อไว้เป็นหลักฐาน</p>
</div>

<div class="sign">
<div>ลงชื่อผู้รับขายฝาก<br><br>____________________________</div>
<div>ลงชื่อลูกค้า<br><br>____________________________</div>
</div>
<div style="text-align:center;margin-top:25px">{_esc(business['receipt_footer'])}</div>
</body>
</html>"""
    return html_doc


def print_pawn_receipt(ticket_id):
    html_doc = build_pawn_receipt(ticket_id)
    folder = Path(tempfile.gettempdir()) / "GoldShop"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"pawn_{ticket_id}.html"
    path.write_text(html_doc, encoding="utf-8")
    opened = webbrowser.open(path.as_uri())
    if not opened:
        raise RuntimeError(
            "ไม่สามารถเปิดใบรับขายฝากใน Browser ได้\n"
            f"ไฟล์ถูกสร้างไว้ที่: {path}"
        )
    return str(path)


def _open_receipt(html_doc, filename):
    folder = Path(tempfile.gettempdir()) / "GoldShop"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    path.write_text(html_doc, encoding="utf-8")
    if not webbrowser.open(path.as_uri()):
        raise RuntimeError(f"ไม่สามารถเปิดใบพิมพ์ได้\nไฟล์ถูกสร้างไว้ที่: {path}")
    return str(path)


def _page_css(paper):
    if paper == "80mm": return "80mm auto; margin: 4mm"
    if paper == "9x5.5": return "9in 5.5in; margin: 0.25in"
    return "A4; margin: 12mm"


def _simple_receipt(title, ticket, rows, transaction_at, document_no=None, employee_only=False):
    business = get_business_settings()
    page_css = _page_css(business["receipt_paper"])
    detail_html = "".join(f"<tr><td>{_esc(label)}</td><td class='num'>{_esc(value)}</td></tr>" for label, value in rows)
    return f"""<!doctype html><html lang="th"><head><meta charset="utf-8"><title>{_esc(title)}</title>
<style>@page{{size:{page_css};}}body{{font-family:Tahoma,'Noto Sans Thai',sans-serif;font-size:14px;color:#111}}
h1,h2,.center{{text-align:center}}h1{{margin-bottom:4px}}h2{{margin:12px 0}}table{{width:100%;border-collapse:collapse}}
td{{border:1px solid #333;padding:8px}}.num{{text-align:right}}.sign{{display:grid;grid-template-columns:{'1fr' if employee_only else '1fr 1fr'};gap:45px;margin-top:55px;text-align:center}}
@media print{{.no-print{{display:none}}}}</style></head><body>
<div class="no-print" style="text-align:right"><button onclick="window.print()">พิมพ์</button></div>
<h1>{_esc(business['business_name'])}</h1><div class="center">{_esc(business['business_address'])}<br>
โทร {_esc(business['business_phone'])} &nbsp; เลขผู้เสียภาษี {_esc(business['business_tax_id'])}</div>
<h2>{_esc(title)}</h2><table>
{f'<tr><td>เลขที่ใบ</td><td class="num">{_esc(document_no)}</td></tr>' if document_no else ''}
<tr><td>เลขที่ตั๋ว</td><td class="num">{_esc(ticket['ticket_no'])}</td></tr>
<tr><td>ลูกค้า</td><td class="num">{_esc(ticket['first_name'])} {_esc(ticket['last_name'])}</td></tr>
<tr><td>วันที่ทำรายการ</td><td class="num">{_esc(format_thai_datetime(transaction_at))}</td></tr>
{detail_html}</table><div class="sign"><div>ลงชื่อพนักงาน/ผู้รับเงิน<br><br>____________________</div>{'' if employee_only else '<div>ลงชื่อลูกค้า<br><br>____________________</div>'}</div>
<div class="center" style="margin-top:25px">{_esc(business['receipt_footer'])}</div></body></html>"""


def build_renewal_receipt(ticket_id, renewal_id=None):
    ticket = get_pawn(ticket_id)
    with get_connection() as conn:
        if renewal_id is None:
            renewal = conn.execute("SELECT * FROM pawn_renewals WHERE pawn_ticket_id=? ORDER BY id DESC LIMIT 1", (int(ticket_id),)).fetchone()
        else:
            renewal = conn.execute("SELECT * FROM pawn_renewals WHERE id=? AND pawn_ticket_id=?", (int(renewal_id), int(ticket_id))).fetchone()
    if not ticket or not renewal: raise ValueError("ไม่พบรายการต่อดอก")
    is_q = str(ticket.get("series_code") or "P").upper() == "Q"
    rows = [
        ("เงินต้น", f"{ticket['loan_amount']:,.2f} บาท"),
        ("ระยะเวลาต่อดอก", f"{renewal['renew_months']} เดือน"),
        ("ผลตอบแทน (ฐานภาษี)", f"{renewal['vat_base']:,.2f} บาท") if is_q else
            ("ผลตอบแทนคำนวณ", f"{renewal['interest_amount']:,.2f} บาท"),
        (f"ภาษีมูลค่าเพิ่ม {renewal['vat_rate']:g}%", f"{renewal['vat_amount']:,.2f} บาท") if is_q else
            ("ยอดรับจริง", f"{renewal['paid_amount']:,.2f} บาท"),
        ("ผลตอบแทนรวมภาษีมูลค่าเพิ่ม", f"{renewal['total_with_vat']:,.2f} บาท") if is_q else
            ("", ""),
        ("ครบกำหนดเดิม", format_thai_date(renewal['previous_due_date'])),
        ("ครบกำหนดใหม่", format_thai_date(renewal['new_due_date'])),
    ]
    if not is_q:
        rows = [row for row in rows if row != ("", "")]
    title = "ใบกำกับภาษี ต่อสัญญาขายฝาก Q" if is_q else "ใบรับเงินต่อดอก"
    document_no = (renewal['tax_document_no'] or f"Q-RN-{int(renewal['id']):06d}") if is_q else None
    return _simple_receipt(title, ticket, rows, renewal["renewed_at"], document_no, employee_only=is_q)


def print_renewal_receipt(ticket_id, renewal_id=None):
    return _open_receipt(build_renewal_receipt(ticket_id, renewal_id), f"renew_{ticket_id}.html")


def build_redemption_receipt(ticket_id, transaction_id=None):
    ticket = get_pawn(ticket_id)
    with get_connection() as conn:
        if transaction_id is None:
            tx = conn.execute("SELECT * FROM pawn_transactions WHERE pawn_ticket_id=? AND transaction_type='redeem' ORDER BY id DESC LIMIT 1", (int(ticket_id),)).fetchone()
        else:
            tx = conn.execute("SELECT * FROM pawn_transactions WHERE id=? AND pawn_ticket_id=? AND transaction_type='redeem'", (int(transaction_id), int(ticket_id))).fetchone()
    if not ticket or not tx: raise ValueError("ไม่พบรายการไถ่ถอน")
    is_q = str(ticket.get("series_code") or "P").upper() == "Q"
    rows = [
        ("เงินต้น", f"{ticket['loan_amount']:,.2f} บาท"),
        ("ผลตอบแทน (ฐานภาษี)", f"{tx['vat_base']:,.2f} บาท") if is_q else
            ("ยอดรับไถ่ถอน", f"{tx['amount']:,.2f} บาท"),
        (f"ภาษีมูลค่าเพิ่ม {tx['vat_rate']:g}%", f"{tx['vat_amount']:,.2f} บาท") if is_q else
            ("", ""),
        ("ยอดคำนวณรวม", f"{tx['total_with_vat']:,.2f} บาท") if is_q else ("", ""),
        ("สถานะ", "ไถ่ถอนแล้ว"),
        ("หมายเหตุ", tx["note"] or "-"),
    ]
    rows = [row for row in rows if row != ("", "")]
    title = "ใบกำกับภาษี ไถ่ถอนสัญญาขายฝาก Q" if is_q else "ใบรับเงินไถ่ถอน"
    document_no = (tx['tax_document_no'] or f"Q-RD-{int(tx['id']):06d}") if is_q else None
    return _simple_receipt(title, ticket, rows, tx["transaction_at"], document_no, employee_only=is_q)


def print_redemption_receipt(ticket_id, transaction_id=None):
    return _open_receipt(build_redemption_receipt(ticket_id, transaction_id), f"redeem_{ticket_id}.html")


def build_correction_receipt(ticket_id, transaction_id):
    ticket = get_pawn(ticket_id)
    with get_connection() as conn:
        tx = conn.execute("SELECT * FROM pawn_transactions WHERE id=? AND pawn_ticket_id=?", (int(transaction_id), int(ticket_id))).fetchone()
    if not ticket or not tx: raise ValueError("ไม่พบรายการแก้ไข")
    titles = {
        "cancel_pawn": "ใบยกเลิกตั๋วขายฝาก",
        "void_renew": "ใบยกเลิกรายการต่อดอก",
        "void_redeem": "ใบยกเลิกรายการไถ่ถอน",
    }
    title = titles.get(tx["transaction_type"], "ใบแก้ไขรายการ")
    rows = [
        ("ประเภทการแก้ไข", title),
        ("เงินต้น", f"{ticket['loan_amount']:,.2f} บาท"),
        ("วันครบกำหนดปัจจุบัน", format_thai_date(ticket["due_date"])),
        ("เหตุผล", tx["note"] or "-"),
    ]
    return _simple_receipt(title, ticket, rows, tx["transaction_at"])


def print_correction_receipt(ticket_id, transaction_id):
    return _open_receipt(build_correction_receipt(ticket_id, transaction_id), f"correction_{ticket_id}_{transaction_id}.html")
