import csv
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog,filedialog
from datetime import date
from modules.operations_control import (list_exchange_workflows,cancel_exchange_workflow,create_tax_adjustment,
 tax_report,cash_report,sell_old_gold_bulk,start_stock_count,scan_stock_count,finalize_stock_count,get_stock_count_items,
 set_stock_count_quantity,mark_stock_count_complete)
from modules.sales import list_gold_sales
from modules.old_gold import list_old_gold
from ui.theme import apply_theme,open_fullscreen,back_to_dashboard

class OperationsCenterWindow(tk.Toplevel):
 def __init__(self,parent,user=None):
  super().__init__(parent);self.parent=parent;self.user=user or {};self.current_count=None;self.title("ศูนย์บริหารและตรวจสอบ");self.geometry("1400x900");open_fullscreen(self);apply_theme(self);self.build();self.load_workflows();self.load_old_gold()
 def build(self):
  h=ttk.Frame(self,padding=10);h.pack(fill="x");ttk.Label(h,text="🛡 ศูนย์บริหารและตรวจสอบ",font=("Arial",23,"bold")).pack(side="left");ttk.Button(h,text="← กลับ Dashboard",command=lambda:back_to_dashboard(self)).pack(side="right")
  tabs=ttk.Notebook(self);tabs.pack(fill="both",expand=True,padx=10,pady=5)
  self.ex=ttk.Frame(tabs);self.tax=ttk.Frame(tabs);self.reports=ttk.Frame(tabs);self.old=ttk.Frame(tabs);self.count=ttk.Frame(tabs)
  for frame,title in ((self.ex,"รายการแลกค้าง/ยกเลิก"),(self.tax,"ใบลดหนี้/เพิ่มหนี้"),(self.reports,"รายงานภาษีและเงินสด"),(self.old,"ขายทองเก่าให้คู่ค้า"),(self.count,"ตรวจนับสต็อก")):tabs.add(frame,text=title)
  self.workflow_tree=self._tree(self.ex,[("no","เลข workflow",130),("status","สถานะ",130),("step","ขั้นตอน",130),("old","ใบรับซื้อ",130),("sale","ใบขาย",130),("exchange","เลขแลก",120),("created","สร้างเมื่อ",170)])
  a=ttk.Frame(self.ex,padding=8);a.pack(fill="x");ttk.Button(a,text="รีเฟรช",command=self.load_workflows).pack(side="left");ttk.Button(a,text="ยกเลิกและย้อนรายการที่เลือก",style="Danger.TButton",command=self.cancel_workflow).pack(side="left",padx=8)
  f=ttk.Frame(self.tax,padding=12);f.pack(fill="x");self.adjust_type=tk.StringVar(value="ใบลดหนี้");self.adjust_sale=tk.StringVar();self.adjust_base=tk.StringVar();self.adjust_vat=tk.StringVar();self.adjust_reason=tk.StringVar()
  self.sale_combo=ttk.Combobox(f,textvariable=self.adjust_sale,state="readonly",width=32);self.sale_combo.grid(row=1,column=0,padx=4);self.adjust_map={}
  for col,(label,var) in enumerate((("ประเภท",self.adjust_type),("ใบกำกับภาษีเดิม",self.adjust_sale),("มูลค่าก่อน VAT",self.adjust_base),("VAT",self.adjust_vat),("เหตุผล",self.adjust_reason))):
   ttk.Label(f,text=label).grid(row=0,column=col,sticky="w",padx=4)
   if col==0:ttk.Combobox(f,textvariable=var,values=("ใบลดหนี้","ใบเพิ่มหนี้"),state="readonly",width=15).grid(row=1,column=col,padx=4)
   elif col>1:ttk.Entry(f,textvariable=var,width=20).grid(row=1,column=col,padx=4,ipady=5)
  ttk.Button(f,text="ออกเอกสาร",style="TouchPrimary.TButton",command=self.make_adjustment).grid(row=1,column=5,padx=8);self.load_sales()
  rf=ttk.Frame(self.reports,padding=8);rf.pack(fill="x");self.date_from=tk.StringVar(value=date.today().replace(day=1).isoformat());self.date_to=tk.StringVar(value=date.today().isoformat());self.cash_date=tk.StringVar(value=date.today().isoformat())
  for label,var in (("ตั้งแต่",self.date_from),("ถึง",self.date_to),("วันที่เงินสด",self.cash_date)):ttk.Label(rf,text=label).pack(side="left",padx=(8,2));ttk.Entry(rf,textvariable=var,width=13).pack(side="left")
  ttk.Button(rf,text="รายงานภาษี",command=self.show_tax_report).pack(side="left",padx=5);ttk.Button(rf,text="รายงานเงินสด",command=self.show_cash_report).pack(side="left",padx=5);ttk.Button(rf,text="ส่งออก CSV",command=self.export_report).pack(side="right")
  self.report_rows=[];self.report_tree=self._tree(self.reports,[("date","วันที่",110),("no","เลขเอกสาร",145),("type","ประเภท",170),("party","ลูกค้า/อ้างอิง",190),("base","ฐาน/เงินเข้า",130),("vat","VAT/เงินออก",130),("total","ยอดรวม",130),("status","สถานะ",110)])
  self.old_tree=self._tree(self.old,[("code","รหัส",120),("item","รายการ",250),("weight","กรัม",100),("purity","%ทอง",90),("cost","ต้นทุน",120)])
  ttk.Label(self.old,text="เลือกหลายรายการ: Mac ใช้ Command (⌘)+คลิก | Windows ใช้ Ctrl+คลิก | เลือกช่วงใช้ Shift+คลิก",foreground="#8a4b08").pack(anchor="w",padx=8)
  of=ttk.Frame(self.old,padding=8);of.pack(fill="x");self.buyer=tk.StringVar();self.bulk_amount=tk.StringVar();self.bulk_method=tk.StringVar(value="เงินสด")
  for label,var in (("คู่ค้า",self.buyer),("ราคาขายรวม",self.bulk_amount)):ttk.Label(of,text=label).pack(side="left",padx=(8,2));ttk.Entry(of,textvariable=var,width=22).pack(side="left")
  ttk.Combobox(of,textvariable=self.bulk_method,values=("เงินสด","โอนเงิน"),state="readonly",width=14).pack(side="left",padx=5);ttk.Button(of,text="ขายรายการที่เลือก",style="TouchPrimary.TButton",command=self.sell_bulk).pack(side="left",padx=8)
  cf=ttk.Frame(self.count,padding=8);cf.pack(fill="x");self.count_type=tk.StringVar(value="ทองใหม่");self.scan_code=tk.StringVar();ttk.Combobox(cf,textvariable=self.count_type,values=("ทองใหม่","ทองเก่า"),state="readonly",width=15).pack(side="left");ttk.Button(cf,text="เริ่มรอบตรวจนับ",command=self.start_count).pack(side="left",padx=5);ttk.Label(cf,text="สแกน QR/กรอกรหัส:").pack(side="left",padx=(10,2));entry=ttk.Entry(cf,textvariable=self.scan_code,font=("Arial",16));entry.pack(side="left",fill="x",expand=True,padx=4);entry.bind("<Return>",lambda _e:self.scan());ttk.Button(cf,text="บันทึกรหัส",command=self.scan).pack(side="left");ttk.Button(cf,text="ปิดรอบและสรุปผลต่าง",style="TouchPrimary.TButton",command=self.finish_count).pack(side="right")
  edit=ttk.Frame(self.count,padding=(8,2));edit.pack(fill="x");self.count_qty=tk.IntVar(value=1);ttk.Label(edit,text="เลือกแถวแล้วกำหนดจำนวนที่นับได้:").pack(side="left");ttk.Spinbox(edit,from_=0,to=999,textvariable=self.count_qty,width=8,font=("Arial",15)).pack(side="left",padx=5);ttk.Button(edit,text="บันทึกจำนวน",command=self.save_count_qty).pack(side="left");ttk.Button(edit,text="−",command=lambda:self.change_count(-1)).pack(side="left",padx=(10,2));ttk.Button(edit,text="+",command=lambda:self.change_count(1)).pack(side="left");ttk.Button(edit,text="นับครบตามระบบ",command=self.mark_all_counted).pack(side="right")
  self.count_info=tk.StringVar(value="ยังไม่ได้เริ่มรอบตรวจนับ");ttk.Label(self.count,textvariable=self.count_info,font=("Arial",15,"bold"),padding=8).pack(anchor="w");self.count_tree=self._tree(self.count,[("code","รหัส",180),("expected","ควรมี",100),("counted","นับได้",100),("variance","ผลต่าง",100),("time","เวลานับ",180)]);self.count_tree.bind("<<TreeviewSelect>>",self.pick_count_row);self.count_tree.bind("<Double-1>",lambda _e:self.save_count_qty())
 def _tree(self,parent,columns):
  tree=ttk.Treeview(parent,columns=[x[0] for x in columns],show="headings",selectmode="extended")
  for c,t,w in columns:tree.heading(c,text=t);tree.column(c,width=w,anchor="center")
  tree.pack(fill="both",expand=True,padx=8,pady=6);return tree
 def load_workflows(self):
  self.workflow_tree.delete(*self.workflow_tree.get_children())
  for x in list_exchange_workflows():self.workflow_tree.insert("","end",iid=str(x["id"]),values=(x["workflow_no"],x["status"],x["current_step"],x["receipt_no"] or "-",x["sale_no"] or "-",x["exchange_no"] or "-",x["created_at"]))
 def cancel_workflow(self):
  if len(self.workflow_tree.selection())!=1:messagebox.showwarning("เลือกข้อมูล","กรุณาเลือกหนึ่งรายการ",parent=self);return
  reason=simpledialog.askstring("ยกเลิกรายการแลก","ระบุเหตุผล",parent=self)
  if not reason:return
  try:r=cancel_exchange_workflow(int(self.workflow_tree.selection()[0]),reason,self.user.get("id"));messagebox.showinfo("ผลการยกเลิก",f"{r['workflow_no']}\nสถานะ {r['status']}"+("\n"+"\n".join(r['errors']) if r['errors'] else ""),parent=self);self.load_workflows()
  except Exception as e:messagebox.showerror("ยกเลิกไม่ได้",str(e),parent=self)
 def load_sales(self):
  rows=list_gold_sales(status="completed");self.adjust_map={f"{x['sale_no']} | {x['grand_total']:,.2f}":x['id'] for x in rows};self.sale_combo["values"]=list(self.adjust_map)
 def make_adjustment(self):
  try:
   r=create_tax_adjustment("credit_note" if self.adjust_type.get()=="ใบลดหนี้" else "debit_note","gold_sale",self.adjust_map.get(self.adjust_sale.get()),self.adjust_reason.get(),self.adjust_base.get(),self.adjust_vat.get(),self.user.get("id"));messagebox.showinfo("สำเร็จ",f"เลขที่ {r['document_no']}\nรวม {r['total_amount']:,.2f} บาท",parent=self)
   from modules.operations_receipts import print_adjustment_receipt
   print_adjustment_receipt(r['adjustment_id'])
  except Exception as e:messagebox.showerror("ออกเอกสารไม่ได้",str(e),parent=self)
 def show_tax_report(self):
  self.report_rows=tax_report(self.date_from.get(),self.date_to.get());self._render_report([[x['document_date'],x['document_no'],x['document_type'],x.get('party',''),x['vat_base'],x['vat_amount'],x['total_amount'],x['status']] for x in self.report_rows])
 def show_cash_report(self):
  self.report_rows=cash_report(self.cash_date.get());self._render_report([[self.cash_date.get(),x['document_no'],x['category'],x['payment_method'],x['cash_in'],x['cash_out'],x['cash_in']-x['cash_out'],''] for x in self.report_rows])
 def _render_report(self,rows):
  self.report_tree.delete(*self.report_tree.get_children())
  for row in rows:self.report_tree.insert("","end",values=[f"{v:,.2f}" if isinstance(v,float) else v for v in row])
 def export_report(self):
  if not self.report_rows:messagebox.showwarning("ไม่มีข้อมูล","กรุณาเรียกรายงานก่อน",parent=self);return
  path=filedialog.asksaveasfilename(parent=self,defaultextension=".csv",filetypes=[("CSV","*.csv")])
  if not path:return
  with open(path,"w",newline="",encoding="utf-8-sig") as f:w=csv.DictWriter(f,fieldnames=list(self.report_rows[0]));w.writeheader();w.writerows(self.report_rows)
  messagebox.showinfo("สำเร็จ",f"บันทึกแล้ว\n{path}",parent=self)
 def load_old_gold(self):
  self.old_tree.delete(*self.old_tree.get_children())
  for x in list_old_gold(status="old_gold_stock"):self.old_tree.insert("","end",iid=str(x['id']),values=(x['item_code'],f"{x['item_type']} {x['description']}",f"{x['net_weight']:,.3f}",f"{x['purity']:,.2f}",f"{x['acquisition_cost']:,.2f}"))
 def sell_bulk(self):
  try:r=sell_old_gold_bulk([int(x) for x in self.old_tree.selection()],self.buyer.get(),self.bulk_amount.get(),self.bulk_method.get(),created_by=self.user.get("id"));messagebox.showinfo("ขายสำเร็จ",f"{r['sale_no']}\n{r['items']} รายการ\n{r['sale_amount']:,.2f} บาท",parent=self);from modules.operations_receipts import print_old_gold_bulk_sale_receipt;print_old_gold_bulk_sale_receipt(r['sale_id']);self.load_old_gold()
  except Exception as e:messagebox.showerror("ขายไม่ได้",str(e),parent=self)
 def start_count(self):
  try:r=start_stock_count("new_gold" if self.count_type.get()=="ทองใหม่" else "old_gold",created_by=self.user.get("id"));self.current_count=r['count_id'];self.count_info.set(f"รอบ {r['count_no']} | ควรมี {r['expected_count']} รายการ");self.load_count()
  except Exception as e:messagebox.showerror("เริ่มไม่ได้",str(e),parent=self)
 def scan(self):
  if not self.current_count:return
  try:scan_stock_count(self.current_count,self.scan_code.get());self.scan_code.set("");self.load_count()
  except Exception as e:messagebox.showerror("บันทึกไม่ได้",str(e),parent=self)
 def load_count(self):
  self.count_tree.delete(*self.count_tree.get_children())
  rows=get_stock_count_items(self.current_count);expected=sum(x['expected'] for x in rows);counted=sum(x['counted'] for x in rows)
  for x in rows:self.count_tree.insert("","end",iid=x['item_code'],values=(x['item_code'],x['expected'],x['counted'],x['variance'],x['counted_at'] or '-'))
  self.count_info.set(f"ควรมี {expected} | นับแล้ว {counted} | คงเหลือ {max(0,expected-counted)} | เกิน {max(0,counted-expected)}")
 def pick_count_row(self,_event=None):
  selected=self.count_tree.selection()
  if selected:self.count_qty.set(int(self.count_tree.item(selected[0],'values')[2]))
 def save_count_qty(self):
  if not self.current_count:return
  selected=self.count_tree.selection()
  if len(selected)!=1:messagebox.showwarning("เลือกรายการ","กรุณาเลือกหนึ่งแถวที่ต้องการแก้จำนวน",parent=self);return
  try:set_stock_count_quantity(self.current_count,selected[0],self.count_qty.get());self.load_count()
  except Exception as e:messagebox.showerror("บันทึกไม่ได้",str(e),parent=self)
 def change_count(self,amount):
  self.count_qty.set(max(0,self.count_qty.get()+amount));self.save_count_qty()
 def mark_all_counted(self):
  if not self.current_count:return
  if messagebox.askyesno("ยืนยัน","กำหนดให้ทุกรายการมีจำนวนเท่ากับยอดในระบบหรือไม่?",parent=self):mark_stock_count_complete(self.current_count);self.load_count()
 def finish_count(self):
  if not self.current_count:return
  try:r=finalize_stock_count(self.current_count,self.user.get("id"));messagebox.showinfo("สรุปตรวจนับ",f"นับได้ {r['counted'] or 0}\nขาด {r['missing'] or 0}\nเกิน {r['unexpected'] or 0}",parent=self);self.load_count();self.current_count=None
  except Exception as e:messagebox.showerror("ปิดรอบไม่ได้",str(e),parent=self)
