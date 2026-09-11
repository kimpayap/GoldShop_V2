from pathlib import Path
import html
from modules.terminology import display_terms
import tempfile
import webbrowser

from modules.business_settings import get_business_settings
from modules.stock import get_stock_receipt
from modules.thai_datetime import format_thai_date, format_thai_datetime
from modules.qr_code import qr_data_uri


def _esc(value): return html.escape(display_terms(value))


def _page_css(paper):
    if paper=="80mm":return "80mm auto; margin:4mm"
    if paper=="9x5.5":return "9in 5.5in; margin:0.25in"
    return "A4; margin:12mm"


def _open(content,filename):
    folder=Path(tempfile.gettempdir())/"GoldShop";folder.mkdir(parents=True,exist_ok=True)
    path=folder/filename;path.write_text(content,encoding="utf-8")
    if not webbrowser.open(path.as_uri()):raise RuntimeError(f"ไม่สามารถเปิดใบพิมพ์ได้\n{path}")
    return str(path)


def build_stock_receipt(receipt_id):
    receipt=get_stock_receipt(receipt_id)
    if not receipt:raise ValueError("ไม่พบใบรับสินค้า")
    business=get_business_settings();rows=[]
    for line in receipt["lines"]:
        rows.append(f"<tr><td>{line['line_no']}</td><td>{_esc(line['item_type'])}</td><td>{_esc(line['description'])}</td><td>{line['purity']:g}</td><td>{line['weight_grams']:,.3f}</td><td>{line['quantity']}</td><td class='num'>{line['unit_subtotal']*line['quantity']:,.2f}</td><td class='num'>{line['unit_vat']*line['quantity']:,.2f}</td><td class='num'>{line['unit_total']*line['quantity']:,.2f}</td></tr>")
    return f"""<!doctype html><html lang='th'><head><meta charset='utf-8'><title>ใบรับทองใหม่ {receipt['receipt_no']}</title>
<style>@page{{size:{_page_css(business['receipt_paper'])}}}body{{font-family:Tahoma,sans-serif;font-size:13px}}h1,h2,.center{{text-align:center}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #333;padding:6px}}.num{{text-align:right}}@media print{{.no-print{{display:none}}}}</style></head><body>
<div class='no-print' style='text-align:right'><button onclick='window.print()'>พิมพ์ใบรับสินค้า</button></div><h1>{_esc(business['business_name'])}</h1><div class='center'>{_esc(business['business_address'])}<br>โทร {_esc(business['business_phone'])} เลขผู้เสียภาษี {_esc(business['business_tax_id'])}</div><h2>ใบรับทองใหม่เข้าสต็อก</h2>
<p><b>เลขที่:</b> {_esc(receipt['receipt_no'])} &nbsp; <b>วันที่รับ:</b> {format_thai_date(receipt['received_date'])}<br><b>ผู้จำหน่าย:</b> {_esc(receipt['supplier_code'])} {_esc(receipt['business_name'])} &nbsp; <b>เลขผู้เสียภาษี:</b> {_esc(receipt['tax_id'])}<br><b>ใบส่งสินค้า:</b> {_esc(receipt['supplier_document_no'])} &nbsp; <b>ใบกำกับภาษี:</b> {_esc(receipt['tax_invoice_no'])}</p>
<table><thead><tr><th>#</th><th>ประเภท</th><th>รายละเอียด</th><th>%ทอง</th><th>กรัม/ชิ้น</th><th>จำนวน</th><th>ก่อนภาษี</th><th>VAT</th><th>รวม</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<table style='width:360px;margin:12px 0 0 auto'><tr><td>ก่อนภาษี</td><td class='num'>{receipt['subtotal']:,.2f}</td></tr><tr><td>VAT</td><td class='num'>{receipt['vat_amount']:,.2f}</td></tr><tr><td><b>ยอดรวม</b></td><td class='num'><b>{receipt['grand_total']:,.2f}</b></td></tr></table>
<p>จำนวน {receipt['total_quantity']} ชิ้น น้ำหนักรวม {receipt['total_weight_grams']:,.3f} กรัม<br>ยืนยันเมื่อ {format_thai_datetime(receipt['confirmed_at'])}</p><div style='display:grid;grid-template-columns:1fr 1fr;text-align:center;margin-top:45px'><div>ผู้รับสินค้า<br><br>________________</div><div>ผู้ส่งสินค้า<br><br>________________</div></div><div class='center'>{_esc(business['receipt_footer'])}</div></body></html>"""


def build_qr_labels(receipt_id):
    receipt=get_stock_receipt(receipt_id)
    if not receipt:raise ValueError("ไม่พบใบรับสินค้า")
    business=get_business_settings();labels=[]
    for item in receipt["items"]:
        qr=qr_data_uri(item["qr_payload"],box_size=4,border=1)
        labels.append(f"<div class='label'><img src='{qr}'><div><b>{_esc(item['item_code'])}</b><br>{_esc(item['item_type'])} {_esc(item['description'])}<br>ทอง {item['purity']:g}% | {item['weight_grams']:,.3f} กรัม<br>ราคาแนะนำ {item['suggested_sale_price']:,.2f} บาท<br><small>{_esc(item['qr_payload'])}</small></div></div>")
    return f"""<!doctype html><html lang='th'><head><meta charset='utf-8'><title>QR {receipt['receipt_no']}</title><style>@page{{size:{_page_css(business['receipt_paper'])}}}body{{font-family:Tahoma,sans-serif}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:6mm}}.label{{border:1px dashed #555;padding:5mm;display:flex;gap:4mm;align-items:center;break-inside:avoid}}img{{width:30mm;height:30mm}}small{{font-size:8px}}@media print{{button{{display:none}}}}</style></head><body><button onclick='window.print()'>พิมพ์ป้าย QR</button><h3>{_esc(business['business_name'])} — {_esc(receipt['receipt_no'])}</h3><div class='grid'>{''.join(labels)}</div></body></html>"""


def print_stock_receipt(receipt_id):return _open(build_stock_receipt(receipt_id),f"stock_receipt_{receipt_id}.html")
def print_qr_labels(receipt_id):return _open(build_qr_labels(receipt_id),f"stock_qr_{receipt_id}.html")


def offer_stock_prints(parent,receipt_id):
    from tkinter import messagebox
    if messagebox.askyesno("พิมพ์ใบรับสินค้า","ต้องการพิมพ์ใบรับทองใหม่หรือไม่?",parent=parent):print_stock_receipt(receipt_id)
    if messagebox.askyesno("พิมพ์ QR Code","ต้องการพิมพ์ป้าย QR Code ของสินค้าทุกชิ้นหรือไม่?",parent=parent):print_qr_labels(receipt_id)
