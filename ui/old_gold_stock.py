import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from modules.old_gold import (list_old_gold,list_untransferred_forfeited_pawns,transfer_forfeited_pawns,
 create_old_gold_batch,list_old_gold_batches,send_batch_to_refinery,receive_refined_batch,sell_old_gold_item,cancel_old_gold_receipt)
from modules.old_gold_receipt import print_old_gold_receipt,print_old_gold_batch_document
from modules.suppliers import list_suppliers
from modules.thai_datetime import format_thai_date
from ui.theme import apply_theme,open_fullscreen,back_to_dashboard

class OldGoldStockWindow(tk.Toplevel):
 def __init__(self,parent,user=None):
  super().__init__(parent);self.parent=parent;self.user=user or {};self.title("จัดการสต็อกทองเก่า");self.geometry("1250x780");open_fullscreen(self);apply_theme(self);self.build();self.refresh_all()
 def build(self):
  h=ttk.Frame(self,padding=10);h.pack(fill="x");ttk.Label(h,text="♻ จัดการสต็อกทองเก่า",font=("Arial",22,"bold")).pack(side="left");ttk.Button(h,text="← กลับ Dashboard",command=lambda:back_to_dashboard(self)).pack(side="right")
  self.tabs=ttk.Notebook(self);self.tabs.pack(fill="both",expand=True,padx=10,pady=5);self.stock=ttk.Frame(self.tabs);self.forfeit=ttk.Frame(self.tabs);self.batch=ttk.Frame(self.tabs);self.tabs.add(self.stock,text="สต็อกทองเก่า");self.tabs.add(self.forfeit,text="รับจากตั๋วหลุด");self.tabs.add(self.batch,text="ล็อต / โรงหลอม")
  sf=ttk.Frame(self.stock,padding=5);sf.pack(fill="x");self.search=tk.StringVar();ttk.Entry(sf,textvariable=self.search,width=35).pack(side="left");ttk.Button(sf,text="ค้นหา/รีเฟรช",command=self.load_stock).pack(side="left",padx=5)
  ttk.Label(self.stock,text="วิธีเลือกหลายรายการ: Mac กด Command (⌘) ค้างแล้วคลิก | Windows กด Ctrl ค้างแล้วคลิก | เลือกช่วงต่อเนื่องใช้ Shift",foreground="#8a4b08").pack(anchor="w",padx=8)
  self.stock_tree=self._tree(self.stock,[("code","รหัส",110),("source","ที่มา",140),("ticket","เลขตั๋ว",100),("item","รายการ",250),("weight","น้ำหนัก",100),("purity","%ทอง",90),("cost","ต้นทุน",120),("status","สถานะ",140)])
  sa=ttk.Frame(self.stock,padding=8);sa.pack(fill="x");ttk.Button(sa,text="รวมรายการที่เลือกเป็นล็อต",command=self.make_batch).pack(side="left",padx=3);ttk.Button(sa,text="ขายทองเก่าเป็นชิ้น",command=self.sell_item).pack(side="left",padx=3);ttk.Button(sa,text="พิมพ์ใบรับเข้า",command=self.print_receipt).pack(side="left",padx=3);ttk.Button(sa,text="ยกเลิกรายการรับเข้า",command=self.cancel_receipt).pack(side="left",padx=3)
  ttk.Label(self.forfeit,text="เลือกตั๋วหลุดหลายใบ แล้วนำทรัพย์ทุกชิ้นเข้าสู่สต็อกทองเก่าพร้อมกัน",font=("Arial",13)).pack(anchor="w",padx=8,pady=8)
  ttk.Label(self.forfeit,text="เลือกหลายรายการ: Mac ใช้ Command (⌘)+คลิก | Windows ใช้ Ctrl+คลิก | เลือกช่วงใช้ Shift+คลิก",foreground="#8a4b08").pack(anchor="w",padx=8)
  self.forfeit_tree=self._tree(self.forfeit,[("ticket","เลขตั๋ว",140),("customer","ลูกค้า",260),("items","จำนวนทรัพย์",120),("weight","น้ำหนักรวม",120),("loan","เงินต้น/ต้นทุน",150),("date","วันที่หลุด",150)])
  fa=ttk.Frame(self.forfeit,padding=8);fa.pack(fill="x");ttk.Button(fa,text="✓ ยืนยันนำรายการที่เลือกเข้าสู่สต็อกทองเก่า",command=self.transfer_forfeit).pack(side="left");ttk.Button(fa,text="รีเฟรช",command=self.load_forfeit).pack(side="left",padx=5)
  self.batch_tree=self._tree(self.batch,[("no","เลขล็อต",130),("items","จำนวน",90),("weight","น้ำหนัก",110),("cost","ต้นทุน",130),("status","สถานะ",160),("refinery","โรงหลอม",220)])
  ba=ttk.Frame(self.batch,padding=8);ba.pack(fill="x");ttk.Button(ba,text="พิมพ์ใบรวมล็อต",command=lambda:self.print_batch("batch")).pack(side="left",padx=3);ttk.Button(ba,text="ส่งล็อตไปโรงหลอม",command=self.send_refinery).pack(side="left",padx=3);ttk.Button(ba,text="พิมพ์ใบส่งโรงหลอม",command=lambda:self.print_batch("shipment")).pack(side="left",padx=3);ttk.Button(ba,text="รับทองกลับจากโรงหลอม",command=self.receive_refinery).pack(side="left",padx=3);ttk.Button(ba,text="รีเฟรช",command=self.load_batches).pack(side="left",padx=3)
 def _tree(self,parent,columns):
  box=ttk.Frame(parent);box.pack(fill="both",expand=True,padx=6,pady=4);tree=ttk.Treeview(box,columns=[x[0] for x in columns],show="headings",selectmode="extended");bar=ttk.Scrollbar(box,orient="vertical",command=tree.yview);tree.configure(yscrollcommand=bar.set)
  for c,t,w in columns:tree.heading(c,text=t);tree.column(c,width=w,anchor="center")
  tree.pack(side="left",fill="both",expand=True);bar.pack(side="right",fill="y");return tree
 def refresh_all(self):self.load_stock();self.load_forfeit();self.load_batches()
 def load_stock(self):
  for x in self.stock_tree.get_children():self.stock_tree.delete(x)
  for x in list_old_gold(self.search.get().strip()):self.stock_tree.insert("","end",iid=str(x["id"]),values=(x["item_code"],"ลูกค้าขาย" if x["source_type"]=="customer_buyback" else "ตั๋วหลุด",x["ticket_no"] or "-",f"{x['item_type']} {x['description']}",f"{x['net_weight']:,.3f}",f"{x['purity']:,.2f}",f"{x['acquisition_cost']:,.2f}",x["status"]))
 def load_forfeit(self):
  for x in self.forfeit_tree.get_children():self.forfeit_tree.delete(x)
  for x in list_untransferred_forfeited_pawns():self.forfeit_tree.insert("","end",iid=str(x["id"]),values=(x["ticket_no"],x["customer_name"],x["item_count"],f"{x['total_weight']:,.3f}",f"{x['loan_amount']:,.2f}",format_thai_date(x["forfeited_at"])))
 def load_batches(self):
  for x in self.batch_tree.get_children():self.batch_tree.delete(x)
  for x in list_old_gold_batches():self.batch_tree.insert("","end",iid=str(x["id"]),values=(x["batch_no"],x["item_count"],f"{x['total_weight']:,.3f}",f"{x['total_cost']:,.2f}",x["status"],x["refinery_name"] or "-"))
 def make_batch(self):
  try:
   selected=[int(x) for x in self.stock_tree.selection()]
   if not selected:raise ValueError("กรุณาเลือกทองเก่าอย่างน้อย 1 รายการ")
   name=simpledialog.askstring("สร้างล็อต","ชื่อล็อต (เว้นว่างได้)",parent=self) or ""
   purpose=simpledialog.askstring("สร้างล็อต","วัตถุประสงค์",initialvalue="ส่งหลอม",parent=self)
   if purpose is None:return
   notes=simpledialog.askstring("สร้างล็อต","หมายเหตุ (เว้นว่างได้)",parent=self) or ""
   r=create_old_gold_batch(selected,notes=notes,created_by=self.user.get("id"),batch_name=name,purpose=purpose);messagebox.showinfo("สำเร็จ",f"สร้างล็อต {r['batch_no']} จำนวน {r['items']} รายการแล้ว",parent=self);self.refresh_all();print_old_gold_batch_document(r['batch_id'])
  except Exception as e:messagebox.showerror("สร้างล็อตไม่ได้",str(e),parent=self)
 def transfer_forfeit(self):
  try:r=transfer_forfeited_pawns([int(x) for x in self.forfeit_tree.selection()],"คลังทองเก่า",note="รับเข้าจากตั๋วหลุด",created_by=self.user.get("id"));messagebox.showinfo("สำเร็จ",f"รับเข้า {r['receipt_no']} จำนวน {r['ticket_count']} ตั๋ว",parent=self);print_old_gold_receipt(r["receipt_id"]);self.refresh_all()
  except Exception as e:messagebox.showerror("รับเข้าไม่ได้",str(e),parent=self)
 def selected_stock(self):
  if len(self.stock_tree.selection())!=1:raise ValueError("กรุณาเลือกหนึ่งรายการ")
  return int(self.stock_tree.selection()[0])
 def _item(self,item_id):return next(x for x in list_old_gold() if x["id"]==item_id)
 def sell_item(self):
  try:
   item=self._item(self.selected_stock());price=simpledialog.askfloat("ขายทองเก่า",f"ราคาขาย {item['item_code']}",parent=self,minvalue=0.01)
   if price is None:return
   buyer=simpledialog.askstring("ผู้ซื้อ","ชื่อผู้ซื้อ/คู่ค้า",parent=self) or "";r=sell_old_gold_item(item["id"],price,buyer_name=buyer,created_by=self.user.get("id"));messagebox.showinfo("สำเร็จ",f"ขายแล้ว เลขที่ {r['sale_no']}",parent=self);self.load_stock()
  except Exception as e:messagebox.showerror("ขายไม่ได้",str(e),parent=self)
 def print_receipt(self):
  try:print_old_gold_receipt(self._item(self.selected_stock())["old_gold_receipt_id"])
  except Exception as e:messagebox.showerror("พิมพ์ไม่ได้",str(e),parent=self)
 def cancel_receipt(self):
  try:
   receipt=self._item(self.selected_stock())["old_gold_receipt_id"];reason=simpledialog.askstring("ยกเลิกรายการ","เหตุผลการยกเลิก",parent=self)
   if not reason:return
   if not messagebox.askyesno("ยืนยัน", "ยกเลิกใบรับเข้าและสินค้าทุกชิ้นในเอกสารนี้?",parent=self):return
   cancel_old_gold_receipt(receipt,reason,self.user.get("id"));print_old_gold_receipt(receipt);self.refresh_all()
  except Exception as e:messagebox.showerror("ยกเลิกไม่ได้",str(e),parent=self)
 def _selected_batch(self):
  if len(self.batch_tree.selection())!=1:raise ValueError("กรุณาเลือกหนึ่งล็อต")
  return int(self.batch_tree.selection()[0])
 def send_refinery(self):
  try:
   suppliers=list_suppliers(active_only=True)
   if not suppliers:raise ValueError("ยังไม่มีข้อมูลคู่ค้า/โรงหลอม")
   names={f"{x['supplier_code']} {x['business_name']}":x['id'] for x in suppliers};dlg=tk.Toplevel(self);dlg.title("ข้อมูลส่งโรงหลอม");v=tk.StringVar(value=next(iter(names)));shipment=tk.StringVar();purity=tk.StringVar(value="96.5");cost=tk.StringVar(value="0");note=tk.StringVar()
   for label,var in (("โรงหลอม",v),("เลขที่ใบส่ง",shipment),("%ทองคาดหมาย",purity),("ค่าหลอม",cost),("หมายเหตุ",note)):
    ttk.Label(dlg,text=label).pack(anchor="w",padx=15,pady=(6,0));(ttk.Combobox(dlg,textvariable=var,values=list(names),state="readonly",width=45) if var is v else ttk.Entry(dlg,textvariable=var,width=48)).pack(padx=15)
   def save():
    send_batch_to_refinery(self._selected_batch(),names[v.get()],shipment.get(),float(purity.get()),float(cost.get()),note.get(),self.user.get("id"));batch=self._selected_batch();dlg.destroy();self.load_batches();print_old_gold_batch_document(batch,"shipment")
   ttk.Button(dlg,text="ยืนยันและพิมพ์ใบส่ง",command=save).pack(pady=12)
  except Exception as e:messagebox.showerror("ส่งไม่ได้",str(e),parent=self)
 def receive_refinery(self):
  try:
   weight=simpledialog.askfloat("รับจากโรงหลอม","น้ำหนักรับกลับ (กรัม)",parent=self,minvalue=0.001)
   if weight is None:return
   purity=simpledialog.askfloat("รับจากโรงหลอม","เปอร์เซ็นต์ทองจริง",parent=self,minvalue=0.01,maxvalue=100)
   if purity is None:return
   r=receive_refined_batch(self._selected_batch(),weight,purity,created_by=self.user.get("id"));messagebox.showinfo("สำเร็จ",f"รับกลับแล้ว น้ำหนักสูญเสีย {r['loss_weight']:,.3f} กรัม",parent=self);self.refresh_all()
  except Exception as e:messagebox.showerror("รับกลับไม่ได้",str(e),parent=self)
 def print_batch(self,kind):
  try:print_old_gold_batch_document(self._selected_batch(),kind)
  except Exception as e:messagebox.showerror("พิมพ์ไม่ได้",str(e),parent=self)
