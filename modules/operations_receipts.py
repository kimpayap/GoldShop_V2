from pathlib import Path
import html,tempfile,webbrowser
from modules.business_settings import get_business_settings
from modules.operations_control import get_tax_adjustment,get_old_gold_bulk_sale
from modules.thai_datetime import format_thai_date
def _e(x):return html.escape(str(x or ''))
def _open(content,name):
 folder=Path(tempfile.gettempdir())/'GoldShop';folder.mkdir(parents=True,exist_ok=True);path=folder/name;path.write_text(content,encoding='utf-8');webbrowser.open(path.as_uri());return str(path)
def _head(title,no,date):
 b=get_business_settings();paper='9in 5.5in' if b.get('receipt_paper')=='9x5.5' else 'A4'
 return f"<!doctype html><html lang='th'><head><meta charset='utf-8'><style>@page{{size:{paper};margin:.25in}}body{{font:12px Tahoma,sans-serif}}h1,h2,.c{{text-align:center}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #333;padding:6px}}.n{{text-align:right}}</style></head><body><button onclick='print()'>พิมพ์</button><h1>{_e(b['business_name'])}</h1><div class='c'>{_e(b['business_address'])}<br>เลขผู้เสียภาษี {_e(b['business_tax_id'])}</div><h2>{title}</h2><p><b>เลขที่:</b> {_e(no)} &nbsp; <b>วันที่:</b> {_e(format_thai_date(date))}</p>"
def build_adjustment_receipt(adjustment_id):
 x=get_tax_adjustment(adjustment_id)
 if not x:raise ValueError('ไม่พบเอกสาร')
 title='ใบลดหนี้' if x['adjustment_type']=='credit_note' else 'ใบเพิ่มหนี้'
 return _head(title,x['document_no'],x['document_date'])+f"<p><b>อ้างอิงใบกำกับภาษีเดิม:</b> {_e(x['original_document_no'])}<br><b>เหตุผล:</b> {_e(x['reason'])}</p><table><tr><td>มูลค่าก่อน VAT</td><td class='n'>{x['amount_ex_vat']:,.2f}</td></tr><tr><td>VAT</td><td class='n'>{x['vat_amount']:,.2f}</td></tr><tr><th>ยอดรวม</th><th class='n'>{x['total_amount']:,.2f}</th></tr></table><div class='c' style='margin-top:45px'>ลงชื่อผู้จัดทำ ____________________ &nbsp;&nbsp; ลงชื่อผู้อนุมัติ ____________________</div></body></html>"
def print_adjustment_receipt(adjustment_id):return _open(build_adjustment_receipt(adjustment_id),f'adjustment_{adjustment_id}.html')
def build_old_gold_bulk_sale_receipt(sale_id):
 x=get_old_gold_bulk_sale(sale_id)
 if not x:raise ValueError('ไม่พบรายการขายทองเก่า')
 rows=''.join(f"<tr><td>{n}</td><td>{_e(i['item_code'])}</td><td>{_e(i['item_type'])} {_e(i['description'])}</td><td class='n'>{i['net_weight']:,.3f}</td><td class='n'>{i['purity']:,.2f}</td><td class='n'>{i['sale_allocated']:,.2f}</td></tr>" for n,i in enumerate(x['items'],1))
 return _head('ใบขายทองเก่าให้คู่ค้า',x['sale_no'],x['sale_date'])+f"<p><b>ผู้ซื้อ/คู่ค้า:</b> {_e(x['buyer_name'])} &nbsp; <b>เลขผู้เสียภาษี:</b> {_e(x['buyer_tax_id'] or '-')}</p><table><tr><th>#</th><th>รหัส</th><th>รายการ</th><th>กรัม</th><th>%ทอง</th><th>จำนวนเงิน</th></tr>{rows}<tr><th colspan='3'>รวม</th><th class='n'>{x['total_weight']:,.3f}</th><th></th><th class='n'>{x['sale_amount']:,.2f}</th></tr></table><p><b>ชำระโดย:</b> {_e(x['payment_method'])} &nbsp; <b>หมายเหตุ:</b> {_e(x['notes'] or '-')}</p><div class='c' style='margin-top:40px'>ลงชื่อผู้ส่งมอบ ____________________ &nbsp;&nbsp; ลงชื่อผู้รับมอบ ____________________</div></body></html>"
def print_old_gold_bulk_sale_receipt(sale_id):return _open(build_old_gold_bulk_sale_receipt(sale_id),f'old_gold_bulk_{sale_id}.html')
