from pathlib import Path
import html
from modules.terminology import display_terms
import tempfile
import webbrowser

from modules.sales import get_gold_sale
from modules.business_settings import get_business_settings
from modules.thai_datetime import format_thai_date,format_thai_datetime


def _esc(value):return html.escape(display_terms(value))


def _paper(value):
    if value=="80mm":return "80mm auto; margin:4mm"
    if value=="9x5.5":return "9in 5.5in; margin:.25in"
    return "A4; margin:12mm"


def build_sale_receipt(sale_id):
    sale=get_gold_sale(sale_id)
    if not sale:raise ValueError("ไม่พบรายการขาย")
    business=get_business_settings();rows=[]
    for x in sale["items"]:
        rows.append(f"<tr><td>{x['line_no']}</td><td>{_esc(x['item_code'])}</td><td>{_esc(x['item_type'])} {_esc(x['description'])}</td><td class='n'>{x['purity']:g}%</td><td class='n'>{x['weight_grams']:,.3f}</td><td class='n'>{x['sale_price_ex_vat']:,.2f}</td><td class='n'>{x['gta_buy_reference']:,.2f}</td><td class='n'>{x['vat_base']:,.2f}</td><td class='n'>{x['vat_amount']:,.2f}</td><td class='n'>{x['total_incl_vat']:,.2f}</td></tr>")
    card="";cancelled="";exchange=""
    if sale["status"]=="cancelled":cancelled=f"<div class='cancelled'>ยกเลิกการขายแล้ว<br><small>เมื่อ {format_thai_datetime(sale['cancelled_at'])} โดย {_esc(sale.get('cancelled_by_name'))} — เหตุผล: {_esc(sale['cancel_reason'])}</small></div>"
    if sale["payment_method"]=="บัตรเครดิต":card=f"<tr><td>ค่าธรรมเนียมบัตร {sale['card_fee_rate']:g}%</td><td class='n'>{sale['card_fee_amount']:,.2f}</td></tr><tr><td><b>ยอดรับชำระรวมค่าธรรมเนียม</b></td><td class='n'><b>{sale['amount_paid']:,.2f}</b></td></tr>"
    if float(sale.get("exchange_credit") or 0)>0:exchange=f"<tr><td>หักเครดิตรับซื้อทองเก่า</td><td class='n'>-{sale['exchange_credit']:,.2f}</td></tr><tr><td><b>ยอดส่วนต่างก่อนค่าธรรมเนียม</b></td><td class='n'><b>{max(0,sale['grand_total']-sale['exchange_credit']):,.2f}</b></td></tr>"
    prices=(f"<div class='gold-prices'><b>ราคาทอง ณ วันที่ขาย</b> &nbsp; "
            f"ทองแท่งขายออก {sale['gold_bar_price']:,.2f} บาท/บาททอง &nbsp; | &nbsp; "
            f"ทองรูปพรรณขายออก {sale['gold_jewelry_price']:,.2f} บาท/บาททอง &nbsp; | &nbsp; "
            f"ทองรูปพรรณรับซื้อคืน {sale['gold_jewelry_buy_per_gram']:,.2f} บาท/กรัม</div>")
    return f"""<!doctype html><html lang='th'><head><meta charset='utf-8'><title>ใบเสร็จ {sale['sale_no']}</title><style>@page{{size:{_paper(business['receipt_paper'])}}}body{{font-family:Tahoma,sans-serif;font-size:13px}}h1,h2,.c{{text-align:center}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #333;padding:5px}}.n{{text-align:right}}.gold-prices{{border:1px solid #333;background:#f7f3df;padding:7px;margin:7px 0;font-size:11px;text-align:center}}.receiver-sign{{width:45%;margin:38px 0 0 auto;text-align:center}}.cancelled{{border:4px solid #b91c1c;color:#b91c1c;text-align:center;font-size:24px;font-weight:bold;padding:8px;margin:8px 0}}.cancelled small{{font-size:12px}}@media print{{button{{display:none}}}}</style></head><body><button onclick='window.print()'>พิมพ์ใบเสร็จ/ใบกำกับภาษี</button>{cancelled}<h1>{_esc(business['business_name'])}</h1><div class='c'>{_esc(business['business_address'])}<br>โทร {_esc(business['business_phone'])} เลขผู้เสียภาษี {_esc(business['business_tax_id'])}</div><h2>ใบเสร็จรับเงิน / ใบกำกับภาษี</h2><p><b>เลขที่:</b> {_esc(sale['sale_no'])} &nbsp; <b>วันที่:</b> {format_thai_date(sale['sale_date'])}<br><b>ลูกค้า:</b> {_esc(sale['customer_name'])} &nbsp; <b>เลขผู้เสียภาษี:</b> {_esc(sale['customer_tax_id'])}<br><b>ที่อยู่:</b> {_esc(sale['customer_address'])}</p>{prices}<table><thead><tr><th>#</th><th>รหัส</th><th>สินค้า</th><th>%ทอง</th><th>กรัม</th><th>ราคาขายไม่รวม VAT</th><th>ราคารับซื้ออ้างอิง</th><th>ฐาน VAT</th><th>VAT</th><th>รวม VAT</th></tr></thead><tbody>{''.join(rows)}</tbody></table><table style='width:390px;margin:12px 0 0 auto'><tr><td>ราคาขายไม่รวม VAT</td><td class='n'>{sale['subtotal_ex_vat']:,.2f}</td></tr><tr><td>ฐานภาษีจากส่วนต่าง</td><td class='n'>{sale['vat_base']:,.2f}</td></tr><tr><td>VAT 7%</td><td class='n'>{sale['vat_amount']:,.2f}</td></tr><tr><td><b>ยอดขายรวม VAT</b></td><td class='n'><b>{sale['grand_total']:,.2f}</b></td></tr>{exchange}<tr><td>ชำระโดย</td><td class='n'>{_esc(sale['payment_method'])}</td></tr>{card}</table><div class='receiver-sign'>ลงชื่อผู้รับเงิน<br><br>____________________________</div><div class='c' style='margin-top:20px'>{_esc(business['receipt_footer'])}</div></body></html>"""


def print_sale_receipt(sale_id):
    folder=Path(tempfile.gettempdir())/"GoldShop";folder.mkdir(parents=True,exist_ok=True);path=folder/f"sale_{sale_id}.html";path.write_text(build_sale_receipt(sale_id),encoding="utf-8")
    if not webbrowser.open(path.as_uri()):raise RuntimeError("ไม่สามารถเปิดใบพิมพ์ได้")
    return str(path)


def offer_sale_print(parent,sale_id):
    from tkinter import messagebox
    if messagebox.askyesno("พิมพ์เอกสาร","ต้องการพิมพ์ใบเสร็จ/ใบกำกับภาษีหรือไม่?",parent=parent):print_sale_receipt(sale_id)
