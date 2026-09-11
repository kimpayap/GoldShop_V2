import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import date
from pathlib import Path
from PIL import Image, ImageTk

from modules.stock import list_inventory
from modules.pawn import (get_latest_gold_price, get_settings, list_gold_types,
                          list_gold_details, list_gold_purities, list_weight_options)
from modules.sales import (get_inventory_by_scan, calculate_sale_item, calculate_sale_totals,
                           calculate_card_payment, get_card_fee_rate, save_card_fee_rate,
                           confirm_gold_sale)
from modules.thai_datetime import format_thai_date
from ui.theme import apply_theme, open_fullscreen, back_to_dashboard


class PatternItemPicker(tk.Toplevel):
    def __init__(self,parent,title,rows,on_select):
        super().__init__(parent);self.rows=rows;self.on_select=on_select;self.title(title);self.geometry("1050x620");apply_theme(self);self.transient(parent);self.grab_set()
        ttk.Label(self,text=title,font=("Arial",20,"bold"),padding=10).pack(anchor="w")
        cols=("code","purity","weight","price","location")
        self.tree=ttk.Treeview(self,columns=cols,show="headings",selectmode="extended")
        for key,label,width in (("code","รหัสสินค้า",150),("purity","%ทอง",100),("weight","น้ำหนัก (กรัม)",150),("price","ราคาแนะนำ",170),("location","ตำแหน่งจัดเก็บ",180)):
            self.tree.heading(key,text=label);self.tree.column(key,width=width,anchor="center")
        self.tree.pack(fill="both",expand=True,padx=10,pady=6)
        for row in rows:self.tree.insert("","end",iid=str(row["id"]),values=(row["item_code"],f'{row["purity"]:g}',f'{row["weight_grams"]:,.3f}',f'{row["suggested_sale_price"]:,.2f}',row.get("storage_location") or ""))
        ttk.Button(self,text="✓ เพิ่มชิ้นที่เลือกลงรายการขาย",style="TouchPrimary.TButton",command=self.choose).pack(pady=10,ipadx=22)

    def choose(self):
        ids={int(x) for x in self.tree.selection()}
        if not ids:messagebox.showwarning("เลือกสินค้า","กรุณาเลือกสินค้าอย่างน้อย 1 ชิ้น",parent=self);return
        self.on_select([x for x in self.rows if x["id"] in ids]);self.destroy()


class InventoryPicker(tk.Toplevel):
    def __init__(self,parent,on_select):
        super().__init__(parent);self.on_select=on_select;self.title("เลือกสินค้าตามลายทอง");self.geometry("1250x800");self.photos=[];self.selected={"type":None,"detail":None,"purity":None,"weight":None}
        apply_theme(self);self.transient(parent);self.grab_set()
        top=ttk.LabelFrame(self,text="ค้นหาและกรอง",padding=10);top.pack(fill="x",padx=10,pady=8)
        self.keyword=tk.StringVar();self.location_filter=tk.StringVar(value="ทั้งหมด")
        entry=ttk.Entry(top,textvariable=self.keyword,font=("Arial",15));entry.grid(row=1,column=0,sticky="ew",padx=4,ipady=6)
        ttk.Label(top,text="ตำแหน่งจัดเก็บ").grid(row=0,column=1,sticky="w",padx=4);self.location_combo=ttk.Combobox(top,textvariable=self.location_filter,state="readonly");self.location_combo.grid(row=1,column=1,sticky="ew",padx=4,ipady=5);self.location_combo.bind("<<ComboboxSelected>>",lambda _e:self.render())
        ttk.Label(top,text="ชื่อ/รหัส/ลาย").grid(row=0,column=0,sticky="w",padx=4)
        ttk.Button(top,text="ค้นหา",command=self.render).grid(row=1,column=2,padx=4);ttk.Button(top,text="ล้างตัวกรองทั้งหมด",command=self.clear_filters).grid(row=1,column=3,padx=4)
        top.columnconfigure(0,weight=2)
        top.columnconfigure(1,weight=1)
        quick=ttk.Frame(self);quick.pack(fill="x",padx=10,pady=(0,5));self.quick_frames={}
        for col,(key,title) in enumerate((("type","ประเภท"),("detail","รายละเอียด"),("purity","%ทอง"),("weight","น้ำหนัก"))):
            box=ttk.LabelFrame(quick,text=title,padding=4);box.grid(row=0,column=col,sticky="nsew",padx=3);quick.columnconfigure(col,weight=1);self.quick_frames[key]=box
        self.count_var=tk.StringVar();ttk.Label(self,textvariable=self.count_var,font=("Arial",14,"bold"),padding=(12,3)).pack(anchor="w")
        outer=ttk.Frame(self);outer.pack(fill="both",expand=True,padx=10,pady=5);self.canvas=tk.Canvas(outer,highlightthickness=0);scroll=ttk.Scrollbar(outer,orient="vertical",command=self.canvas.yview)
        self.cards=ttk.Frame(self.canvas);self.card_window=self.canvas.create_window((0,0),window=self.cards,anchor="nw");self.cards.bind("<Configure>",lambda _e:self.canvas.configure(scrollregion=self.canvas.bbox("all")));self.canvas.bind("<Configure>",lambda e:self.canvas.itemconfigure(self.card_window,width=e.width));self.canvas.configure(yscrollcommand=scroll.set);self.canvas.pack(side="left",fill="both",expand=True);scroll.pack(side="right",fill="y")
        self.all_rows=list_inventory("","in_stock");self.load_filter_values();self.render_filter_buttons();entry.bind("<Return>",lambda _e:self.render());self.render();entry.focus_set()

    def load_filter_values(self):
        self.location_combo["values"]=["ทั้งหมด"]+sorted({str(x.get("storage_location") or "ไม่ระบุ") for x in self.all_rows})

    def render_filter_buttons(self):
        data={"type":list_gold_types(True),"detail":list_gold_details(True),"purity":list_gold_purities(True),"weight":list_weight_options("baht",True)+list_weight_options("gram",True)};self.filter_data=data
        for key,frame in self.quick_frames.items():
            for child in frame.winfo_children():child.destroy()
            for index,row in enumerate(data[key]):
                if key=="weight":value=(row["unit"],float(row["value"]));label=row["label"]
                elif key=="purity":value=float(row["percent"]);label=row["name"]
                else:value=int(row["id"]);label=row["name"]
                selected=self.selected[key]==value
                ttk.Button(frame,text=(f"✓ {label}" if selected else label),style=("Selected.TButton" if selected else "Touch.TButton"),command=lambda k=key,v=value:self.select_filter(k,v)).grid(row=index//3,column=index%3,sticky="ew",padx=2,pady=2)
            for col in range(3):frame.columnconfigure(col,weight=1)

    def select_filter(self,key,value):
        self.selected[key]=None if self.selected[key]==value else value
        self.render_filter_buttons();self.render()

    def clear_filters(self):
        self.keyword.set("");self.location_filter.set("ทั้งหมด")
        for key in self.selected:self.selected[key]=None
        self.render_filter_buttons();self.render()

    def filtered_rows(self):
        term=self.keyword.get().strip().lower();result=[]
        for row in self.all_rows:
            hay=" ".join(str(row.get(k) or "") for k in ("item_code","item_type","description","storage_location")).lower()
            if term and term not in hay:continue
            if self.selected["type"] is not None:
                selected_type=next((x["name"] for x in self.filter_data["type"] if int(x["id"])==self.selected["type"]),None)
                if row["item_type"]!=selected_type:continue
            if self.selected["detail"] is not None and int(row.get("gold_detail_id") or 0)!=self.selected["detail"]:continue
            if self.selected["purity"] is not None and abs(float(row["purity"])-self.selected["purity"])>0.001:continue
            if self.selected["weight"] is not None:
                unit,value=self.selected["weight"];target=value*float(get_settings()["weight_per_baht_gram"]) if unit=="baht" else value
                if abs(float(row["weight_grams"])-target)>0.02:continue
            location=str(row.get("storage_location") or "ไม่ระบุ")
            if self.location_filter.get()!="ทั้งหมด" and location!=self.location_filter.get():continue
            result.append(row)
        return result

    def thumbnail(self,path):
        if not path or not Path(path).is_file():return None
        try:
            image=Image.open(path);image.thumbnail((150,110));photo=ImageTk.PhotoImage(image);self.photos.append(photo);return photo
        except Exception:return None

    def render(self):
        for child in self.cards.winfo_children():child.destroy()
        self.photos=[];rows=self.filtered_rows();groups={}
        for row in rows:groups.setdefault((row.get("gold_detail_id") or row["description"],row["item_type"],row["description"]),[]).append(row)
        self.count_var.set(f"พบ {len(groups)} ลาย รวม {len(rows)} ชิ้น — เลือกลายก่อน แล้วเลือกชิ้นตามน้ำหนักและตำแหน่ง")
        for index,((_detail_id,item_type,description),items) in enumerate(sorted(groups.items(),key=lambda x:(str(x[0][1]),str(x[0][2])))):
            card=ttk.LabelFrame(self.cards,text=f"{item_type} — {description}",padding=8);card.grid(row=index//3,column=index%3,sticky="nsew",padx=6,pady=6)
            photo=self.thumbnail(items[0].get("image_path"));image_label=ttk.Label(card,image=photo if photo else "",text="ยังไม่มีรูปตัวอย่าง" if not photo else "",anchor="center",width=24);image_label.pack(fill="x",pady=(0,5))
            purities=", ".join(sorted({f'{x["purity"]:g}%' for x in items}));weights=sorted(float(x["weight_grams"]) for x in items)
            ttk.Label(card,text=f"มีในสต็อก {len(items)} ชิ้น",font=("Arial",15,"bold")).pack(anchor="w")
            ttk.Label(card,text=f"%ทอง: {purities}\nน้ำหนัก: {weights[0]:,.3f}–{weights[-1]:,.3f} กรัม",justify="left").pack(anchor="w",pady=4)
            ttk.Button(card,text="ดูและเลือกสินค้า",style="TouchPrimary.TButton",command=lambda title=f"{item_type} — {description}",r=items:PatternItemPicker(self,title,r,self.choose_items)).pack(fill="x",pady=(5,0))
        for col in range(3):self.cards.columnconfigure(col,weight=1)

    def choose_items(self,rows):
        self.on_select(rows);self.destroy()


class GoldSaleWindow(tk.Toplevel):
    def __init__(self,parent,user=None,on_completed=None,initial_customer=None,exchange_mode=False,exchange_credit=0):
        super().__init__(parent);self.parent=parent;self.user=user or {};self.on_completed=on_completed;self.initial_customer=initial_customer or {};self.exchange_mode=exchange_mode;self.exchange_credit=float(exchange_credit or 0);self.items=[];self.payment_guard=False;self.confirming=False
        self.title("ขายทองใหม่ - Gold Shop System");self.geometry("1400x900");self.minsize(1150,760)
        open_fullscreen(self);apply_theme(self);self.create_widgets();self.load_prices();self.load_initial_customer()

    def load_initial_customer(self):
        for key in ("customer_name","customer_tax_id","customer_address"):
            if self.initial_customer.get(key):self.vars[key].set(str(self.initial_customer[key]))

    def create_widgets(self):
        head=ttk.Frame(self,padding=12);head.pack(fill="x")
        ttk.Label(head,text="🛒 ขายทองใหม่",font=("Arial",24,"bold")).pack(side="left")
        ttk.Button(head,text="← กลับ Dashboard",command=lambda:back_to_dashboard(self)).pack(side="right")
        ttk.Button(head,text="🧾 ประวัติการขาย",command=self.open_history).pack(side="right",padx=6)

        customer=ttk.LabelFrame(self,text="1. ลูกค้าและราคาอ้างอิง",padding=10);customer.pack(fill="x",padx=12,pady=5)
        self.vars={key:tk.StringVar() for key in ("customer_name","customer_tax_id","customer_address","scan","jewelry_buy","jewelry_sell","notes")}
        ttk.Label(customer,text=f"วันที่ขาย: {format_thai_date(date.today())}",font=("Arial",13,"bold")).grid(row=0,column=0,sticky="w",padx=5)
        for col,(label,key) in enumerate((("ชื่อลูกค้า (ไม่บังคับ)","customer_name"),("เลขผู้เสียภาษี","customer_tax_id"),("ที่อยู่","customer_address"))):
            ttk.Label(customer,text=label).grid(row=1,column=col,sticky="w",padx=5);ttk.Entry(customer,textvariable=self.vars[key]).grid(row=2,column=col,sticky="ew",padx=5,ipady=5)
        ttk.Label(customer,text="ราคารับซื้อทองรูปพรรณ/บาท").grid(row=3,column=0,sticky="w",padx=5)
        self.buy_entry=ttk.Entry(customer,textvariable=self.vars["jewelry_buy"]);self.buy_entry.grid(row=4,column=0,sticky="ew",padx=5,ipady=5)
        ttk.Label(customer,text="ราคาขายทองรูปพรรณ/บาท").grid(row=3,column=1,sticky="w",padx=5)
        ttk.Entry(customer,textvariable=self.vars["jewelry_sell"]).grid(row=4,column=1,sticky="ew",padx=5,ipady=5)
        for col in range(3):customer.columnconfigure(col,weight=1)

        pick=ttk.LabelFrame(self,text="2. เลือกสินค้า",padding=10);pick.pack(fill="x",padx=12,pady=5)
        ttk.Label(pick,text="สแกน QR หรือกรอกรหัสสินค้า").pack(side="left")
        scan=ttk.Entry(pick,textvariable=self.vars["scan"],font=("Arial",16));scan.pack(side="left",fill="x",expand=True,padx=8,ipady=6);scan.bind("<Return>",lambda _e:self.add_scan())
        ttk.Button(pick,text="เพิ่มจาก QR",command=self.add_scan).pack(side="left",padx=4)
        ttk.Button(pick,text="เลือกจากสต็อก",style="TouchPrimary.TButton",command=lambda:InventoryPicker(self,self.add_items)).pack(side="left",padx=4)

        listing=ttk.LabelFrame(self,text="3. รายการขาย — ดับเบิลคลิกเพื่อแก้ราคาขายรวม VAT",padding=8);listing.pack(fill="both",expand=True,padx=12,pady=5)
        cols=("no","code","type","desc","purity","weight","reference","exvat","vatbase","vat","total")
        self.tree=ttk.Treeview(listing,columns=cols,show="headings",height=9,selectmode="extended")
        for key,title,width in (("no","#",38),("code","รหัส",95),("type","ประเภท",95),("desc","รายละเอียด",135),("purity","%ทอง",60),("weight","กรัม",75),("reference","รับซื้ออ้างอิง",110),("exvat","ขายไม่รวม VAT",110),("vatbase","ฐาน VAT",95),("vat","VAT",80),("total","รวม VAT",110)):
            self.tree.heading(key,text=title);self.tree.column(key,width=width,anchor="center")
        self.tree.pack(fill="both",expand=True);self.tree.bind("<Double-1>",self.edit_price)
        row=ttk.Frame(listing);row.pack(fill="x",pady=5)
        ttk.Button(row,text="ลบรายการที่เลือก",command=self.remove_items).pack(side="left")
        self.summary=tk.StringVar(value="0 ชิ้น | VAT 0.00 | ยอดขาย 0.00 บาท");ttk.Label(row,textvariable=self.summary,font=("Arial",16,"bold")).pack(side="right")

        pay=ttk.LabelFrame(self,text="4. รับชำระเงิน",padding=10);pay.pack(fill="x",padx=12,pady=5)
        self.pay={"method":tk.StringVar(value="เงินสด"),"rate":tk.StringVar(value=f"{get_card_fee_rate():g}"),"before":tk.StringVar(value="0.00"),"fee":tk.StringVar(value="0.00"),"after":tk.StringVar(value="0.00")}
        ttk.Label(pay,text="วิธีชำระ").grid(row=0,column=0,sticky="w");method=ttk.Combobox(pay,textvariable=self.pay["method"],values=("เงินสด","โอนเงิน","บัตรเครดิต"),state="readonly");method.grid(row=1,column=0,sticky="ew",padx=(0,6),ipady=5);method.bind("<<ComboboxSelected>>",lambda _e:self.payment_from_before())
        for col,(label,key,state) in enumerate((("ค่าธรรมเนียมบัตร %","rate","normal"),("ยอดก่อนค่าธรรมเนียม","before","normal"),("ค่าธรรมเนียม","fee","readonly"),("ยอดหลังรวมค่าธรรมเนียม","after","normal")),1):
            ttk.Label(pay,text=label).grid(row=0,column=col,sticky="w");ttk.Entry(pay,textvariable=self.pay[key],state=state).grid(row=1,column=col,sticky="ew",padx=3,ipady=5)
        ttk.Button(pay,text="บันทึก % เป็นค่าเริ่มต้น",command=self.save_default_fee).grid(row=1,column=5,padx=6)
        self.confirm_button=ttk.Button(pay,text="✅ ยืนยันการขาย",style="TouchPrimary.TButton",command=self.confirm)
        self.confirm_button.grid(row=1,column=6,padx=6,ipadx=14,ipady=7)
        for col in range(7):pay.columnconfigure(col,weight=1)
        self.pay["rate"].trace_add("write",lambda *_:self.payment_from_before());self.pay["before"].trace_add("write",lambda *_:self.payment_from_before());self.pay["after"].trace_add("write",lambda *_:self.payment_from_after())
        scan.focus_set()

    def load_prices(self):
        gold=get_latest_gold_price()
        if gold:
            self.vars["jewelry_buy"].set(f'{float(gold["gold_jewelry_tax"] or 0):.2f}');self.vars["jewelry_sell"].set(f'{float(gold["gold_jewelry_sell"] or 0):.2f}')

    def open_history(self):
        from ui.sale_history import SaleHistoryWindow
        SaleHistoryWindow(self,self.user)

    def _calculate(self,item,total):
        return calculate_sale_item(item,total,self.vars["jewelry_buy"].get(),get_settings()["weight_per_baht_gram"])

    def suggested_total(self,item):
        stored=float(item.get("suggested_sale_price") or 0)
        if stored>0:return stored
        try:return round((float(item["weight_grams"])/get_settings()["weight_per_baht_gram"])*float(self.vars["jewelry_sell"].get())*(float(item["purity"])/96.5),2)
        except Exception:return 0

    def add_scan(self):
        item=get_inventory_by_scan(self.vars["scan"].get());self.vars["scan"].set("")
        if not item:messagebox.showwarning("ไม่พบสินค้า","ไม่พบ QR หรือรหัสสินค้านี้",parent=self);return
        self.add_items([item])

    def add_items(self,items):
        existing={x["id"] for x in self.items}
        try:
            for item in items:
                if item["id"] in existing:continue
                if item.get("status")!="in_stock":raise ValueError(f"{item['item_code']} ไม่อยู่ในสต็อก")
                total=self.suggested_total(item)
                if total<=0:raise ValueError(f"กรุณากำหนดราคาขายแนะนำของ {item['item_code']}")
                self.items.append(self._calculate(item,total));existing.add(item["id"])
            self.refresh()
        except Exception as error:messagebox.showerror("เพิ่มสินค้าไม่ได้",str(error),parent=self)

    def edit_price(self,_event=None):
        selected=self.tree.selection()
        if not selected:return
        index=int(selected[0]);item=self.items[index]
        value=simpledialog.askfloat("แก้ราคาขาย",f"{item['item_code']} {item['item_type']}\nราคาขายรวม VAT",initialvalue=item["total_incl_vat"],minvalue=0.01,parent=self)
        if value is not None:
            try:self.items[index]=self._calculate(item,value);self.refresh()
            except Exception as error:messagebox.showerror("ราคาไม่ถูกต้อง",str(error),parent=self)

    def remove_items(self):
        for index in sorted((int(x) for x in self.tree.selection()),reverse=True):self.items.pop(index)
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i,x in enumerate(self.items):self.tree.insert("","end",iid=str(i),values=(i+1,x["item_code"],x["item_type"],x["description"],f'{x["purity"]:g}',f'{x["weight_grams"]:,.3f}',f'{x["gta_buy_reference"]:,.2f}',f'{x["sale_price_ex_vat"]:,.2f}',f'{x["vat_base"]:,.2f}',f'{x["vat_amount"]:,.2f}',f'{x["total_incl_vat"]:,.2f}'))
        totals=calculate_sale_totals(self.items);credit_text=f" | เครดิตทองเก่า {self.exchange_credit:,.2f} | ส่วนต่าง {totals['grand_total']-self.exchange_credit:,.2f}" if self.exchange_mode else "";self.summary.set(f"{len(self.items)} ชิ้น | VAT {totals['vat_amount']:,.2f} | ยอดขาย {totals['grand_total']:,.2f} บาท{credit_text}")
        settlement=max(0,totals["grand_total"]-self.exchange_credit) if self.exchange_mode else totals["grand_total"]
        self.payment_guard=True;self.pay["before"].set(f'{settlement:.2f}');self.payment_guard=False;self.payment_from_before()

    def payment_from_before(self):
        if self.payment_guard:return
        try:
            self.payment_guard=True;rate=float(self.pay["rate"].get() or 0) if self.pay["method"].get()=="บัตรเครดิต" else 0
            result=calculate_card_payment(self.pay["before"].get(),rate);self.pay["fee"].set(f'{result["card_fee_amount"]:.2f}');self.pay["after"].set(f'{result["amount_paid"]:.2f}')
        except ValueError:pass
        finally:self.payment_guard=False

    def payment_from_after(self):
        if self.payment_guard:return
        try:
            self.payment_guard=True;rate=float(self.pay["rate"].get() or 0) if self.pay["method"].get()=="บัตรเครดิต" else 0
            result=calculate_card_payment(rate=rate,total_with_fee=self.pay["after"].get());self.pay["before"].set(f'{result["amount_before_fee"]:.2f}');self.pay["fee"].set(f'{result["card_fee_amount"]:.2f}')
        except ValueError:pass
        finally:self.payment_guard=False

    def save_default_fee(self):
        try:rate=save_card_fee_rate(self.pay["rate"].get());messagebox.showinfo("บันทึกแล้ว",f"ค่าธรรมเนียมบัตรเริ่มต้น {rate:g}%",parent=self)
        except Exception as error:messagebox.showerror("บันทึกไม่ได้",str(error),parent=self)

    def confirm(self):
        if self.confirming:return
        try:
            totals=calculate_sale_totals(self.items)
            if not self.items:raise ValueError("กรุณาเลือกสินค้าอย่างน้อย 1 รายการ")
            before=float(self.pay["before"].get());after=float(self.pay["after"].get())
            expected_before=max(0,totals["grand_total"]-self.exchange_credit) if self.exchange_mode else totals["grand_total"]
            if abs(before-expected_before)>0.01:raise ValueError("ยอดก่อนค่าธรรมเนียมต้องตรงกับเงินส่วนต่างที่ระบบคำนวณ")
            credit_detail=f"\nเครดิตทองเก่า {self.exchange_credit:,.2f} บาท\nส่วนต่างก่อนค่าธรรมเนียม {expected_before:,.2f} บาท" if self.exchange_mode else ""
            detail=f"สินค้า {len(self.items)} ชิ้น\nยอดขาย {totals['grand_total']:,.2f} บาท\nVAT {totals['vat_amount']:,.2f} บาท{credit_detail}\nรับชำระ {after:,.2f} บาท"
            if not messagebox.askyesno("ยืนยันการขาย",detail+"\n\nเมื่อตกลงระบบจะตัดสินค้าออกจากสต็อก",parent=self):return
            self.confirming=True;self.confirm_button.configure(state="disabled",text="กำลังบันทึก...");self.update_idletasks()
            gold=get_latest_gold_price() or {}
            weight_per_baht=float(get_settings()["weight_per_baht_gram"] or 15.244)
            jewelry_buy=float(self.vars["jewelry_buy"].get() or 0)
            header={"sale_date":date.today().isoformat(),"customer_name":self.vars["customer_name"].get(),"customer_tax_id":self.vars["customer_tax_id"].get(),"customer_address":self.vars["customer_address"].get(),"payment_method":self.pay["method"].get(),"card_fee_rate":float(self.pay["rate"].get() or 0) if self.pay["method"].get()=="บัตรเครดิต" else 0,"amount_paid":after,"notes":self.vars["notes"].get(),"gold_bar_price":float(gold.get("gold_bar_sell") or 0),"gold_jewelry_price":float(self.vars["jewelry_sell"].get() or 0),"gold_jewelry_buy_per_gram":round(jewelry_buy/weight_per_baht,2) if weight_per_baht else 0,"exchange_credit":self.exchange_credit if self.exchange_mode else 0}
            result=confirm_gold_sale(header,self.items,self.user.get("id"))
            # รายการแลกทองต้องเชื่อมเอกสารให้เสร็จก่อนเปิดหน้าพิมพ์ มิฉะนั้น
            # หน้าต่างพิมพ์/ข้อความยืนยันที่ซ้อนกันอาจทำให้ผู้ใช้คิดว่าโปรแกรมค้าง
            if self.on_completed:
                self.on_completed(result);self.destroy();return
            messagebox.showinfo("ขายสำเร็จ",f"เลขที่ {result['sale_no']}\nยอดขาย {result['grand_total']:,.2f} บาท\nรับชำระ {result['amount_paid']:,.2f} บาท",parent=self)
            from modules.sale_receipt import offer_sale_print
            offer_sale_print(self,result["sale_id"])
            self.items=[];self.refresh()
            if hasattr(self.parent,"refresh_dashboard"):self.parent.refresh_dashboard()
            self.confirming=False;self.confirm_button.configure(state="normal",text="✅ ยืนยันการขาย")
        except Exception as error:
            self.confirming=False
            if self.winfo_exists():self.confirm_button.configure(state="normal",text="✅ ยืนยันการขาย")
            messagebox.showerror("ขายสินค้าไม่ได้",str(error),parent=self)
