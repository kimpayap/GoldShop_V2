from pathlib import Path
import html,tempfile,webbrowser
from modules.business_settings import get_business_settings
from modules.gold_exchange import get_gold_exchange
from modules.thai_datetime import format_thai_datetime

def _e(value):return html.escape(str(value or ""))

def build_exchange_receipt(exchange_id):
    x=get_gold_exchange(exchange_id)
    if not x:raise ValueError("ไม่พบรายการแลกทอง")
    b=get_business_settings();paper="9in 5.5in" if b.get("receipt_paper")=="9x5.5" else "A4"
    if x["settlement_direction"]=="customer_pays":result=f"ลูกค้าชำระเพิ่ม {abs(x['difference_amount']):,.2f} บาท"
    elif x["settlement_direction"]=="shop_refunds":result=f"ร้านคืนเงินลูกค้า {abs(x['difference_amount']):,.2f} บาท"
    else:result="ไม่มีเงินส่วนต่าง"
    return f"""<!doctype html><html lang='th'><head><meta charset='utf-8'><style>@page{{size:{paper};margin:.25in}}body{{font:13px Tahoma,sans-serif}}h1,h2,.c{{text-align:center}}table{{width:100%;border-collapse:collapse}}td{{border:1px solid #333;padding:8px}}.n{{text-align:right}}.result{{font-size:20px;font-weight:bold;background:#fff3bf}}</style></head><body><button onclick='print()'>พิมพ์</button><h1>{_e(b['business_name'])}</h1><div class='c'>{_e(b['business_address'])}</div><h2>ใบสรุปการแลกทองเก่าเป็นทองใหม่</h2><table><tr><td>เลขที่รายการแลกทอง</td><td class='n'>{_e(x['exchange_no'])}</td></tr><tr><td>วันที่ทำรายการ</td><td class='n'>{_e(format_thai_datetime(x['created_at']))}</td></tr><tr><td>ใบรับซื้อทองเก่า</td><td class='n'>{_e(x['receipt_no'])}</td></tr><tr><td>ใบกำกับภาษีขายทองใหม่</td><td class='n'>{_e(x['sale_no'])}</td></tr><tr><td>มูลค่าทองเก่า (ยอดจ่ายจริง)</td><td class='n'>{x['trade_in_amount']:,.2f} บาท</td></tr><tr><td>ยอดขายทองใหม่รวม VAT</td><td class='n'>{x['new_gold_amount']:,.2f} บาท</td></tr><tr class='result'><td>ผลต่าง</td><td class='n'>{result}</td></tr><tr><td>ชำระส่วนต่างโดย</td><td class='n'>{_e(x['settlement_method'])}</td></tr></table><div class='c' style='margin-top:45px'>ลงชื่อพนักงาน ________________________</div></body></html>"""

def print_exchange_receipt(exchange_id):
    folder=Path(tempfile.gettempdir())/"GoldShop";folder.mkdir(parents=True,exist_ok=True);path=folder/f"exchange_{exchange_id}.html";path.write_text(build_exchange_receipt(exchange_id),encoding="utf-8")
    if not webbrowser.open(path.as_uri()):raise RuntimeError("ไม่สามารถเปิดใบสรุปการแลกทองได้")
    return str(path)
