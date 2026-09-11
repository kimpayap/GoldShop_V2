import tkinter as tk
import random
from tkinter import ttk,messagebox
from datetime import date
from modules.customers import search_customers
from modules.pawn import get_latest_gold_price,list_gold_types,list_gold_details,list_gold_purities,list_weight_options,get_settings
from modules.old_gold import calculate_buyback_line,create_customer_buyback
from modules.old_gold_receipt import print_old_gold_receipt
from modules.thai_datetime import format_thai_date,parse_thai_date_to_iso
from ui.date_picker import open_thai_calendar
from ui.theme import apply_theme,open_fullscreen,back_to_dashboard
from ui.settings_access import TouchKeypad

class OldGoldBuybackWindow(tk.Toplevel):
 def __init__(self,parent,user=None,on_completed=None,exchange_mode=False,exchange_workflow_id=None):
  super().__init__(parent);self.parent=parent;self.user=user or {};self.on_completed=on_completed;self.exchange_mode=exchange_mode;self.exchange_workflow_id=exchange_workflow_id;self.customer_map={};self.lines=[];self.selected={k:None for k in ("item_type","description","purity","gross_weight")}
  self.title("รับซื้อทองเก่าจากลูกค้า");self.geometry("1400x900");open_fullscreen(self);apply_theme(self);self.build();self.load_data()
 def build(self):
  outer=ttk.Frame(self);outer.pack(fill="both",expand=True);canvas=tk.Canvas(outer,highlightthickness=0);bar=ttk.Scrollbar(outer,orient="vertical",command=canvas.yview);canvas.pack(side="left",fill="both",expand=True);bar.pack(side="right",fill="y");canvas.configure(yscrollcommand=bar.set);self.body=ttk.Frame(canvas);wid=canvas.create_window((0,0),window=self.body,anchor="nw");self.body.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")));canvas.bind("<Configure>",lambda e:canvas.itemconfigure(wid,width=e.width))
  h=ttk.Frame(self.body,padding=12);h.pack(fill="x");ttk.Label(h,text="♻ รับซื้อทองเก่าจากลูกค้า",font=("Arial",22,"bold")).pack(side="left");ttk.Button(h,text="← กลับ Dashboard",command=lambda:back_to_dashboard(self)).pack(side="right")
  top=ttk.LabelFrame(self.body,text="1. ผู้ขายและข้อมูลการจ่ายเงิน",padding=10);top.pack(fill="x",padx=12,pady=5)
  self.customer=tk.StringVar();self.customer_box=ttk.Combobox(top,textvariable=self.customer,state="readonly");self._field(top,"ผู้ขาย/ลูกค้า",self.customer_box,0)
  self.receipt_date=tk.StringVar(value=format_thai_date(date.today()));dw=ttk.Frame(top);ttk.Entry(dw,textvariable=self.receipt_date,state="readonly").pack(side="left",fill="x",expand=True);ttk.Button(dw,text="📅",command=lambda:open_thai_calendar(self,self.receipt_date,"วันที่รับซื้อ")).pack(side="left");self._field(top,"วันที่รับซื้อ",dw,1)
  gold=get_latest_gold_price();self.current_bar_buy=float(gold["gold_bar_buy"] or 0) if gold else 0;self.purchase_discount_rate=round(random.uniform(3.5,5.0),2);default=round(self.current_bar_buy*(1-self.purchase_discount_rate/100),2);self.price=tk.StringVar(value=f"{default:.2f}");self.discount_info=tk.StringVar(value=f"จาก {self.current_bar_buy:,.2f} หัก {self.purchase_discount_rate:.2f}%");price_wrap=ttk.Frame(top);price_entry=ttk.Entry(price_wrap,textvariable=self.price,state="readonly");price_entry.bind("<Button-1>",self.reset_purchase_price);price_entry.pack(side="left",fill="x",expand=True);ttk.Label(price_wrap,textvariable=self.discount_info,font=("Arial",10)).pack(side="left",padx=6);self._field(top,"ราคาในใบรับซื้อ/บาททอง (คลิกเพื่อสุ่มใหม่)",price_wrap,2)
  for c in range(3):top.columnconfigure(c,weight=1)
  form=ttk.LabelFrame(self.body,text="2. กดปุ่มเลือกรายการทองเก่าและกำหนดจำนวนเงินต่อรายการ",padding=8);form.pack(fill="x",padx=12,pady=5);self.v={k:tk.StringVar(value=d) for k,d in [("item_type",""),("description",""),("gross_weight",""),("non_gold_weight","0"),("purity",""),("deduction_amount","0"),("receipt_amount",""),("actual_paid_amount",""),("inspection_method","ทดสอบน้ำยา"),("condition_note",""),("storage_location","คลังทองเก่า")]};self._amount_syncing=False
  preset=ttk.Frame(form);preset.pack(fill="x");self.frames={}
  for col,(key,title) in enumerate((("item_type","ประเภท"),("description","รายละเอียด"),("purity","%ทอง"),("gross_weight","น้ำหนัก"))):box=ttk.LabelFrame(preset,text=title,padding=5);box.grid(row=0,column=col,sticky="nsew",padx=3);preset.columnconfigure(col,weight=1);self.frames[key]=box
  extra=ttk.Frame(form);extra.pack(fill="x",pady=5)
  for i,(label,key) in enumerate((("หักสิ่งเจือปน (กรัม)","non_gold_weight"),("ยอดหัก/ค่าหลอม","deduction_amount"),("ราคาในใบรับซื้อ/รายการ","receipt_amount"),("จำนวนเงินจ่ายจริง/รายการ","actual_paid_amount"),("วิธีตรวจ","inspection_method"),("สภาพสินค้า","condition_note"),("ตำแหน่งจัดเก็บ","storage_location"))):
   ttk.Label(extra,text=label).grid(row=0,column=i,sticky="w");entry=ttk.Entry(extra,textvariable=self.v[key]);entry.grid(row=1,column=i,padx=3,sticky="ew");extra.columnconfigure(i,weight=1)
   if key in {"non_gold_weight","deduction_amount","receipt_amount","actual_paid_amount"}:
    changed=key if key in {"deduction_amount","receipt_amount","actual_paid_amount"} else None;self.bind_keypad(entry,self.v[key],label,changed);entry.bind("<KeyRelease>",lambda _e,k=changed:self.sync_amount_fields(k) if k else None)
  self.v["deduction_amount"].trace_add("write",lambda *_:self.sync_amount_fields("deduction_amount"))
  self.v["receipt_amount"].trace_add("write",lambda *_:self.sync_amount_fields("receipt_amount"))
  self.price.trace_add("write",lambda *_:self.sync_amount_fields("deduction_amount"))
  ttk.Button(form,text="＋ เพิ่มรายการ",style="TouchPrimary.TButton",command=self.add_line).pack(anchor="e",ipadx=20,pady=5)
  box=ttk.LabelFrame(self.body,text="3. รายการรับซื้อ",padding=6);box.pack(fill="both",expand=True,padx=12,pady=5);self.tree=ttk.Treeview(box,columns=("item","gross","net","purity","value","deduct","receipt","actual"),show="headings",height=9)
  for c,t,w in [("item","รายการ",250),("gross","น้ำหนักรวม",100),("net","น้ำหนักสุทธิ",100),("purity","%ทอง",75),("value","ราคาประเมิน",115),("deduct","ยอดหัก",90),("receipt","ราคาในใบรับซื้อ",140),("actual","จ่ายจริง",125)]:self.tree.heading(c,text=t);self.tree.column(c,width=w,anchor="center")
  self.tree.pack(fill="both",expand=True);foot=ttk.Frame(self.body,padding=12);foot.pack(fill="x");self.total=tk.StringVar(value="รวมจำนวนเงินที่จ่าย 0.00 บาท");ttk.Label(foot,textvariable=self.total,font=("Arial",18,"bold")).pack(side="left");ttk.Button(foot,text="ลบรายการ",command=self.remove_line).pack(side="right",padx=5);ttk.Button(foot,text="✓ ยืนยันรับซื้อและพิมพ์เอกสาร",style="TouchPrimary.TButton",command=self.confirm).pack(side="right")
 def _field(self,parent,label,widget,col):ttk.Label(parent,text=label,font=("Arial",12,"bold")).grid(row=0,column=col,sticky="w");widget.grid(row=1,column=col,padx=4,sticky="ew")
 def reset_purchase_price(self,event=None):
  gold=get_latest_gold_price();self.current_bar_buy=float(gold["gold_bar_buy"] or 0) if gold else 0;self.purchase_discount_rate=round(random.uniform(3.5,5.0),2);self.price.set(f"{self.current_bar_buy*(1-self.purchase_discount_rate/100):.2f}");self.discount_info.set(f"จาก {self.current_bar_buy:,.2f} หัก {self.purchase_discount_rate:.2f}%")
  self.sync_amount_fields("deduction_amount");return "break"
 def bind_keypad(self,entry,variable,title,changed_key=None):
  entry.bind("<Button-1>",lambda _e,v=variable,t=title,k=changed_key:self.open_keypad(v,t,k))
 def open_keypad(self,variable,title,changed_key=None):
  keypad=TouchKeypad(self,variable,title);keypad.update_idletasks();x=self.winfo_rootx()+max(0,(self.winfo_width()-keypad.winfo_width())//2);y=self.winfo_rooty()+max(0,(self.winfo_height()-keypad.winfo_height())//2);keypad.geometry(f"+{x}+{y}");self.wait_window(keypad)
  if changed_key:self.sync_amount_fields(changed_key)
  self.refresh()
 def sync_amount_fields(self,changed_key):
  if self._amount_syncing:return
  try:
   self._amount_syncing=True
   gross=float(self.v["gross_weight"].get());other=float(self.v["non_gold_weight"].get() or 0);purity=float(self.v["purity"].get());price=float(self.price.get().replace(",",""));grams=float(get_settings()["weight_per_baht_gram"]);value=round(((gross-other)/grams)*price*(purity/96.5),2)
   if changed_key=="deduction_amount":
    deduction=float(self.v["deduction_amount"].get() or 0);amount=max(0,value-deduction);self.v["receipt_amount"].set(f"{amount:.2f}");self.v["actual_paid_amount"].set(f"{amount:.2f}")
   elif changed_key=="receipt_amount":
    amount=float(self.v["receipt_amount"].get() or 0)
    if amount<=value:self.v["deduction_amount"].set(f"{value-amount:.2f}")
  except (TypeError,ValueError):pass
  finally:self._amount_syncing=False
 def load_data(self):
  rows=search_customers();self.customer_map={f"{x['customer_code']} | {x['first_name']} {x['last_name']}":x['id'] for x in rows};self.customer_box["values"]=list(self.customer_map);self.presets={"item_type":list_gold_types(True),"description":list_gold_details(True),"purity":list_gold_purities(True),"gross_weight":list_weight_options("baht",True)+list_weight_options("gram",True)};self.render_buttons()
 def render_buttons(self):
  for key,frame in self.frames.items():
   for w in frame.winfo_children():w.destroy()
   for i,row in enumerate(self.presets[key]):
    label=row["label"] if key=="gross_weight" else row["name"];chosen=self.selected[key]==(row.get("id"),row.get("unit"));ttk.Button(frame,text=("✓ "+label if chosen else label),style=("Selected.TButton" if chosen else "Touch.TButton"),command=lambda k=key,r=row:self.choose(k,r)).grid(row=i//3,column=i%3,sticky="ew",padx=2,pady=2)
   for c in range(3):frame.columnconfigure(c,weight=1)
 def choose(self,key,row):
  self.selected[key]=(row.get("id"),row.get("unit"))
  if key=="purity":self.v[key].set(f"{float(row['percent']):g}")
  elif key=="gross_weight":self.v[key].set(f"{float(row['value'])*float(get_settings()['weight_per_baht_gram']) if row['unit']=='baht' else float(row['value']):g}")
  else:self.v[key].set(row["name"])
  if key in {"purity","gross_weight"}:self.sync_amount_fields("deduction_amount")
  self.render_buttons()
 def add_line(self):
  try:
   for key,label in (("item_type","ประเภท"),("description","รายละเอียด"),("gross_weight","น้ำหนัก"),("purity","%ทอง")):
    if not self.v[key].get():raise ValueError(f"กรุณาเลือก{label}")
   if not self.v["receipt_amount"].get().strip():raise ValueError("กรุณาระบุราคาในใบรับซื้อ/รายการ")
   if not self.v["actual_paid_amount"].get().strip():raise ValueError("กรุณาระบุจำนวนเงินจ่ายจริง/รายการ")
   raw={k:x.get().strip() for k,x in self.v.items()};raw["reference_gold_price"]=self.price.get();self.lines.append(calculate_buyback_line(raw));self.refresh();self.selected["description"]=None;self.selected["gross_weight"]=None;self.v["description"].set("");self.v["gross_weight"].set("");self._amount_syncing=True;self.v["deduction_amount"].set("0");self.v["receipt_amount"].set("");self.v["actual_paid_amount"].set("");self._amount_syncing=False;self.render_buttons()
  except Exception as e:messagebox.showwarning("ข้อมูลไม่ถูกต้อง",str(e),parent=self)
 def refresh(self):
  self.tree.delete(*self.tree.get_children())
  paid=sum(float(x['paid_amount']) for x in self.lines)
  for i,x in enumerate(self.lines):
   self.tree.insert("","end",iid=str(i),values=(f"{x['item_type']} {x['description']}",f"{x['gross_weight']:,.3f}",f"{x['net_weight']:,.3f}",f"{x['purity']:,.2f}",f"{x['gross_value']:,.2f}",f"{x['deduction_amount']:,.2f}",f"{x['receipt_amount']:,.2f}",f"{x['paid_amount']:,.2f}"))
  self.total.set(f"รวมจำนวนเงินที่จ่าย {paid:,.2f} บาท")
 def remove_line(self):
  if self.tree.selection():self.lines.pop(int(self.tree.selection()[0]));self.refresh()
 def confirm(self):
  try:
   cid=self.customer_map.get(self.customer.get());paid=sum(float(x["paid_amount"]) for x in self.lines)
   if not cid:raise ValueError("กรุณาเลือกผู้ขาย/ลูกค้า")
   if not self.lines:raise ValueError("กรุณาเพิ่มรายการทองเก่า")
   if paid<=0:raise ValueError("กรุณาระบุจำนวนเงินที่จ่ายลูกค้า")
   if not messagebox.askyesno("ยืนยันรับซื้อ",f"จำนวน {len(self.lines)} รายการ\nจ่ายลูกค้า {paid:,.2f} บาท\n\nยืนยันทำรายการ?",parent=self):return
   result=create_customer_buyback({"customer_id":cid,"receipt_date":parse_thai_date_to_iso(self.receipt_date.get()),"reference_gold_price":self.price.get(),"purchase_discount_rate":self.purchase_discount_rate},self.lines,self.user.get("id"));result["customer_id"]=cid;result["customer_display"]=self.customer.get()
   if self.exchange_workflow_id:
    from modules.operations_control import update_exchange_workflow
    update_exchange_workflow(self.exchange_workflow_id,old_receipt_id=result["receipt_id"])
   if self.on_completed:self.on_completed(result)
   messagebox.showinfo("สำเร็จ",f"บันทึก {result['receipt_no']}\nจ่าย {result['paid_amount']:,.2f} บาท",parent=self);print_old_gold_receipt(result["receipt_id"])
   if self.on_completed:self.destroy();return
   self.lines=[];self.reset_purchase_price();self.refresh()
  except Exception as e:messagebox.showerror("บันทึกไม่ได้",str(e),parent=self)
