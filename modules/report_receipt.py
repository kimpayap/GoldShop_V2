from pathlib import Path
import html,tempfile,webbrowser
from modules.business_settings import get_business_settings
from modules.thai_datetime import format_thai_date
from modules.reporting import summarize_report

def _e(value):return html.escape(str(value or ""))

def print_report(title,date_from,date_to,rows):
    business=get_business_settings();summary=summarize_report(rows);paper="9in 5.5in" if business.get("receipt_paper")=="9x5.5" else "A4"
    body="".join(f"<tr><td>{n}</td><td>{_e(format_thai_date(x['report_date']))}</td><td>{_e(x['document_no'])}</td><td>{_e(x['category'])}</td><td>{_e(x['party'])}</td><td>{_e(x['detail'])}</td><td class='n'>{float(x.get('quantity') or 0):,.0f}</td><td class='n'>{float(x.get('weight') or 0):,.3f}</td><td class='n'>{float(x.get('amount_in') or 0):,.2f}</td><td class='n'>{float(x.get('amount_out') or 0):,.2f}</td><td class='n'>{float(x.get('vat') or 0):,.2f}</td><td>{_e(x['status'])}</td></tr>" for n,x in enumerate(rows,1))
    page=f"""<!doctype html><html lang='th'><head><meta charset='utf-8'><style>@page{{size:{paper};margin:.2in}}body{{font:8px Tahoma,sans-serif}}h1,h2,.c{{text-align:center}}h1{{font-size:15px;margin:0}}h2{{font-size:13px;margin:3px}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #444;padding:2px}}th{{background:#eee}}.n{{text-align:right}}.summary{{font-size:10px;font-weight:bold;margin:5px 0}}@media print{{button{{display:none}}}}</style></head><body><button onclick='print()'>พิมพ์รายงาน</button><h1>{_e(business['business_name'])}</h1><h2>{_e(title)}</h2><div class='c'>ตั้งแต่ {format_thai_date(date_from)} ถึง {format_thai_date(date_to)}</div><div class='summary'>จำนวน {summary['records']:,} รายการ | จำนวนชิ้น {summary['quantity']:,.0f} | น้ำหนัก {summary['weight']:,.3f} กรัม | เงินเข้า {summary['amount_in']:,.2f} | เงินออก/ต้นทุน {summary['amount_out']:,.2f} | VAT {summary['vat']:,.2f} | สุทธิ {summary['amount_in']-summary['amount_out']:,.2f} บาท</div><table><thead><tr><th>#</th><th>วันที่</th><th>เลขเอกสาร</th><th>ประเภท</th><th>ลูกค้า/คู่ค้า</th><th>รายละเอียด</th><th>จำนวน</th><th>กรัม</th><th>เงินเข้า</th><th>เงินออก/ต้นทุน</th><th>VAT</th><th>สถานะ</th></tr></thead><tbody>{body}</tbody></table><p>ผู้จัดทำ ____________________ ผู้ตรวจสอบ ____________________</p></body></html>"""
    folder=Path(tempfile.gettempdir())/"GoldShop";folder.mkdir(parents=True,exist_ok=True);path=folder/"report.html";path.write_text(page,encoding="utf-8");webbrowser.open(path.as_uri());return str(path)
