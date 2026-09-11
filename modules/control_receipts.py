from pathlib import Path
import html,tempfile,webbrowser
from modules.business_settings import get_business_settings
from modules.system_controls import get_shift
from modules.thai_datetime import format_thai_date,format_thai_datetime

def _e(value):return html.escape(str(value or ""))

def print_shift_receipt(shift_id):
    x=get_shift(shift_id)
    if not x:raise ValueError("ไม่พบข้อมูลกะ")
    b=get_business_settings();paper="9in 5.5in" if b.get('receipt_paper')=='9x5.5' else 'A4';methods=("เงินสด","โอนเงิน","บัตรเครดิต","อื่น ๆ")
    rows="".join(f"<tr><td>{m}</td><td class='n'>{x['expected'].get(m,0):,.2f}</td><td class='n'>{x['actual'].get(m,0):,.2f}</td><td class='n'>{x['difference'].get(m,0):,.2f}</td></tr>" for m in methods)
    page=f"""<!doctype html><html lang='th'><head><meta charset='utf-8'><style>@page{{size:{paper};margin:.25in}}body{{font:12px Tahoma,sans-serif}}h1,h2,.c{{text-align:center}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #333;padding:6px}}.n{{text-align:right}}@media print{{button{{display:none}}}}</style></head><body><button onclick='print()'>พิมพ์</button><h1>{_e(b['business_name'])}</h1><h2>ใบสรุปปิดกะ / ปิดยอดประจำวัน</h2><p><b>เลขที่:</b> {_e(x['shift_no'])} &nbsp; <b>วันที่:</b> {format_thai_date(x['shift_date'])}<br><b>เปิดกะ:</b> {_e(x.get('opened_name'))} เวลา {format_thai_datetime(x['opened_at'])}<br><b>เงินสดต้นกะ:</b> {x['opening_cash']:,.2f} บาท</p><table><tr><th>ช่องทาง</th><th>ยอดตามระบบ</th><th>ยอดนับจริง</th><th>ขาด/เกิน</th></tr>{rows}</table><p><b>หมายเหตุ:</b> {_e(x.get('note') or '-')}<br><b>ปิดกะโดย:</b> {_e(x.get('closed_name'))} &nbsp; <b>อนุมัติโดย:</b> {_e(x.get('approved_name'))}</p><div class='c' style='margin-top:40px'>ลงชื่อผู้ปิดกะ ____________________ &nbsp;&nbsp; ลงชื่อผู้ตรวจสอบ/อนุมัติ ____________________</div></body></html>"""
    folder=Path(tempfile.gettempdir())/'GoldShop';folder.mkdir(parents=True,exist_ok=True);path=folder/f"cash_shift_{shift_id}.html";path.write_text(page,encoding='utf-8');webbrowser.open(path.as_uri());return str(path)
