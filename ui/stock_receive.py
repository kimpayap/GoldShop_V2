import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from pathlib import Path
from PIL import Image, ImageTk

from modules.suppliers import list_suppliers
from modules.stock import calculate_stock_line, calculate_gold_cost, apply_invoice_vat, confirm_new_gold_receipt
from modules.pawn import get_latest_gold_price, list_gold_types, list_gold_details, list_gold_purities, list_weight_options, get_settings
from modules.thai_datetime import format_thai_date, parse_thai_date_to_iso
from ui.theme import apply_theme, open_fullscreen, back_to_dashboard
from ui.date_picker import open_thai_calendar


class NewGoldReceiveWindow(tk.Toplevel):
    def __init__(self, parent, user=None):
        super().__init__(parent)
        self.parent=parent;self.user=user or {};self.lines=[];self.supplier_map={};self.selected_presets={"item_type":None,"description":None,"purity":None,"weight_grams":None};self.pattern_photo=None
        self.title("รับทองใหม่เข้าสต็อก - Gold Shop System");self.geometry("1400x900");self.minsize(1150,760)
        open_fullscreen(self);apply_theme(self);self.create_widgets();self.load_reference_data()

    def create_widgets(self):
        outer=ttk.Frame(self);outer.pack(fill="both",expand=True)
        canvas=tk.Canvas(outer,highlightthickness=0);scroll=ttk.Scrollbar(outer,orient="vertical",command=canvas.yview)
        canvas.pack(side="left",fill="both",expand=True);scroll.pack(side="right",fill="y");canvas.configure(yscrollcommand=scroll.set)
        self.body=ttk.Frame(canvas);window_id=canvas.create_window((0,0),window=self.body,anchor="nw")
        self.body.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda e:canvas.itemconfigure(window_id,width=e.width))

        head=ttk.Frame(self.body,padding=12);head.pack(fill="x")
        ttk.Label(head,text="📥 รับทองใหม่เข้าสต็อก",font=("Arial",24,"bold")).pack(side="left")
        ttk.Button(head,text="← กลับ Dashboard",command=lambda:back_to_dashboard(self)).pack(side="right")

        doc=ttk.LabelFrame(self.body,text="1. ผู้จำหน่ายและเอกสาร",padding=10);doc.pack(fill="x",padx=12,pady=5)
        self.header_vars={key:tk.StringVar() for key in ("supplier","received_date","supplier_document_no","tax_invoice_no","document_date","reference_gold_price","invoice_vat_amount","payment_type","payment_due_date","notes")}
        today=format_thai_date(date.today());self.header_vars["received_date"].set(today);self.header_vars["document_date"].set(today);self.header_vars["payment_type"].set("เงินสด")
        self.header_vars["invoice_vat_amount"].set("0")
        fields=(("ผู้จำหน่าย","supplier"),("วันที่รับ","received_date"),("เลขใบส่งสินค้า","supplier_document_no"),("เลขใบกำกับภาษี","tax_invoice_no"),("วันที่เอกสาร","document_date"),("ราคาทองอ้างอิง (96.5%/บาททอง)","reference_gold_price"),("VAT ตามใบกำกับภาษี","invoice_vat_amount"),("ชำระเงิน","payment_type"),("ครบกำหนดชำระ","payment_due_date"),("หมายเหตุ","notes"))
        for i,(label,key) in enumerate(fields):
            row=(i//3)*2;col=(i%3)*2;ttk.Label(doc,text=label,font=("Arial",12,"bold")).grid(row=row,column=col,sticky="w",padx=5)
            if key=="supplier":widget=ttk.Combobox(doc,textvariable=self.header_vars[key],state="readonly")
            elif key=="payment_type":widget=ttk.Combobox(doc,textvariable=self.header_vars[key],values=("เงินสด","เครดิต","โอนเงิน"),state="readonly")
            elif key in {"received_date","document_date","payment_due_date"}:
                wrapper=ttk.Frame(doc);wrapper.grid(row=row+1,column=col,columnspan=2,sticky="ew",padx=5,pady=(0,5))
                widget=ttk.Entry(wrapper,textvariable=self.header_vars[key],state="readonly");widget.pack(side="left",fill="x",expand=True,ipady=5)
                ttk.Button(wrapper,text="📅 เลือกวัน",command=lambda v=self.header_vars[key],t=label:open_thai_calendar(self,v,t)).pack(side="left",padx=(4,0))
            else:widget=ttk.Entry(doc,textvariable=self.header_vars[key])
            if key not in {"received_date","document_date","payment_due_date"}:widget.grid(row=row+1,column=col,columnspan=2,sticky="ew",padx=5,pady=(0,5),ipady=5)
            if key=="supplier":self.supplier_combo=widget
        for col in range(6):doc.columnconfigure(col,weight=1)

        item=ttk.LabelFrame(self.body,text="2. เพิ่มรายการทอง",padding=10);item.pack(fill="x",padx=12,pady=5)
        keys=("item_type","description","purity","weight_grams","quantity","gold_cost","workmanship_cost","discount","suggested_sale_price","storage_location","notes")
        self.item_vars={key:tk.StringVar() for key in keys};self.item_vars["quantity"].set("1");self.item_vars["workmanship_cost"].set("0");self.item_vars["discount"].set("0");self.item_vars["suggested_sale_price"].set("0")
        fields=(("ประเภท","item_type"),("รายละเอียด/ลาย","description"),("%ทอง","purity"),("น้ำหนักทองสุทธิ (กรัม)","weight_grams"),("จำนวนชิ้น","quantity"),("ต้นทุนทอง/ชิ้น (คำนวณอัตโนมัติ)","gold_cost"),("ค่ากำเหน็จซื้อ/ชิ้น","workmanship_cost"),("ส่วนลด/ชิ้น","discount"),("ราคาขายแนะนำ","suggested_sale_price"),("ตำแหน่งจัดเก็บ","storage_location"),("หมายเหตุรายการ","notes"))
        self.item_widgets={}
        for i,(label,key) in enumerate(fields):
            row=(i//4)*2;col=(i%4)*2;ttk.Label(item,text=label,font=("Arial",12,"bold")).grid(row=row,column=col,sticky="w",padx=4)
            widget=ttk.Entry(item,textvariable=self.item_vars[key],state="readonly") if key in {"item_type","description","purity","weight_grams","gold_cost"} else ttk.Entry(item,textvariable=self.item_vars[key])
            widget.grid(row=row+1,column=col,columnspan=2,sticky="ew",padx=4,pady=(0,5),ipady=5);self.item_widgets[key]=widget
        for col in range(8):item.columnconfigure(col,weight=1)
        self.header_vars["reference_gold_price"].trace_add("write",lambda *_:self.update_gold_cost())
        presets=ttk.Frame(item);presets.grid(row=6,column=0,columnspan=8,sticky="ew",pady=5)
        self.preset_frames={}
        for col,(key,title) in enumerate((("item_type","ประเภท"),("description","รายละเอียด"),("purity","%ทอง"),("weight_grams","น้ำหนัก"))):
            box=ttk.LabelFrame(presets,text=title,padding=5);box.grid(row=0,column=col,sticky="nsew",padx=3);presets.columnconfigure(col,weight=1);self.preset_frames[key]=box
        preview=ttk.LabelFrame(item,text="รูปตัวอย่างลายที่เลือก",padding=5);preview.grid(row=7,column=0,columnspan=6,sticky="ew",padx=4,pady=6)
        self.pattern_preview=ttk.Label(preview,text="กรุณาเลือกรายละเอียด/ลายทอง",anchor="center");self.pattern_preview.pack(fill="x")
        ttk.Button(item,text="➕ เพิ่มรายการ",style="TouchPrimary.TButton",command=self.add_line).grid(row=7,column=6,columnspan=2,sticky="nsew",padx=4,pady=6)

        listing=ttk.LabelFrame(self.body,text="3. รายการที่จะรับเข้า",padding=8);listing.pack(fill="both",expand=True,padx=12,pady=5)
        cols=("no","type","desc","purity","weight","qty","cost","vat","total","location")
        self.tree=ttk.Treeview(listing,columns=cols,show="headings",height=8)
        for key,title,width in (("no","#",45),("type","ประเภท",110),("desc","รายละเอียด",170),("purity","%ทอง",75),("weight","กรัม/ชิ้น",90),("qty","จำนวน",65),("cost","ก่อนภาษี",110),("vat","VAT",90),("total","รวม",120),("location","จัดเก็บ",100)):
            self.tree.heading(key,text=title);self.tree.column(key,width=width,anchor="center")
        self.tree.pack(fill="both",expand=True)
        self.header_vars["invoice_vat_amount"].trace_add("write",lambda *_:self.refresh_lines())
        actions=ttk.Frame(listing);actions.pack(fill="x",pady=6)
        ttk.Button(actions,text="ลบรายการที่เลือก",command=self.remove_line).pack(side="left")
        self.summary_var=tk.StringVar(value="0 รายการ | 0 ชิ้น | ยอดรวม 0.00 บาท")
        ttk.Label(actions,textvariable=self.summary_var,font=("Arial",16,"bold")).pack(side="left",padx=20)
        ttk.Button(actions,text="✅ ยืนยันรับเข้าสต็อก",style="TouchPrimary.TButton",command=self.confirm).pack(side="right",ipadx=18,ipady=8)

    def load_reference_data(self):
        suppliers=list_suppliers(active_only=True);labels=[]
        for row in suppliers:
            label=f"{row['supplier_code']} | {row['business_name']}";labels.append(label);self.supplier_map[label]=row['id']
        self.supplier_combo["values"]=labels
        self.preset_data={"item_type":list_gold_types(True),"description":list_gold_details(True),"purity":list_gold_purities(True),"weight_grams":list_weight_options("baht",True)+list_weight_options("gram",True)}
        self.render_preset_buttons()
        gold=get_latest_gold_price()
        if gold:self.header_vars["reference_gold_price"].set(f'{float(gold["gold_bar_buy"] or 0):.2f}')

    def render_preset_buttons(self):
        for key,frame in self.preset_frames.items():
            for widget in frame.winfo_children():widget.destroy()
            for i,row in enumerate(self.preset_data.get(key,[])):
                selected=self.selected_presets.get(key)==(row.get("id"),row.get("unit"))
                if key=="purity":label=row["name"]
                elif key=="weight_grams":label=row["label"]
                else:label=row["name"]
                ttk.Button(frame,text=(f"✓ {label}" if selected else label),style=("Selected.TButton" if selected else "Touch.TButton"),command=lambda k=key,r=row:self.select_preset(k,r)).grid(row=i//3,column=i%3,sticky="ew",padx=2,pady=2)
            for col in range(3):frame.columnconfigure(col,weight=1)

    def select_preset(self,key,row):
        self.selected_presets[key]=(row.get("id"),row.get("unit"))
        if key=="purity":self.item_vars[key].set(f'{float(row["percent"]):g}')
        elif key=="weight_grams":
            grams=float(row["value"])*float(get_settings()["weight_per_baht_gram"]) if row["unit"]=="baht" else float(row["value"])
            self.item_vars[key].set(f"{grams:g}")
        else:self.item_vars[key].set(row["name"])
        if key=="description":self.show_pattern_image(row)
        if key in {"purity","weight_grams"}:self.update_gold_cost()
        self.render_preset_buttons()

    def show_pattern_image(self,row=None):
        self.pattern_photo=None;path=(row or {}).get("image_path")
        if path and Path(path).is_file():
            try:
                image=Image.open(path);image.thumbnail((180,110));self.pattern_photo=ImageTk.PhotoImage(image)
                self.pattern_preview.configure(image=self.pattern_photo,text=f"{row['name']}",compound="left");return
            except Exception:pass
        name=(row or {}).get("name")
        self.pattern_preview.configure(image="",text=(f"{name} — ยังไม่มีรูปตัวอย่าง" if name else "กรุณาเลือกรายละเอียด/ลายทอง"),compound="none")

    def update_gold_cost(self):
        try:
            settings=get_settings()
            cost=calculate_gold_cost(self.item_vars["weight_grams"].get(),self.item_vars["purity"].get(),self.header_vars["reference_gold_price"].get(),settings["weight_per_baht_gram"])
            self.item_vars["gold_cost"].set(f"{cost:.2f}" if cost else "")
        except (TypeError,ValueError,tk.TclError):
            self.item_vars["gold_cost"].set("")

    def add_line(self):
        try:
            raw={key:var.get().strip() for key,var in self.item_vars.items()}
            selected_detail=self.selected_presets.get("description")
            raw["gold_detail_id"]=selected_detail[0] if selected_detail else None
            required=(("item_type","กรุณาเลือกประเภททอง"),("description","กรุณาเลือกรายละเอียด"),("purity","กรุณาเลือกเปอร์เซ็นต์ทอง"),("weight_grams","กรุณาเลือกน้ำหนัก"),("quantity","กรุณาระบุจำนวนชิ้น"),("gold_cost","กรุณาระบุต้นทุนทอง"))
            for key,message in required:
                if not raw[key]:self.invalid_field(key,message);return
            numeric=(("purity","เปอร์เซ็นต์ทอง"),("weight_grams","น้ำหนักทองสุทธิ"),("quantity","จำนวนชิ้น"),("gold_cost","ต้นทุนทอง"),("workmanship_cost","ค่ากำเหน็จ"),("discount","ส่วนลด"),("suggested_sale_price","ราคาขายแนะนำ"))
            for key,label in numeric:
                try:float(raw[key] or 0)
                except ValueError:self.invalid_field(key,f"{label}ต้องเป็นตัวเลข");return
            try:
                if int(raw["quantity"])!=float(raw["quantity"]):raise ValueError
            except ValueError:self.invalid_field("quantity","จำนวนชิ้นต้องเป็นเลขจำนวนเต็ม");return
            line=calculate_stock_line(raw)
            line["suggested_sale_price"]=float(raw["suggested_sale_price"] or 0);self.lines.append(line);self.refresh_lines()
            for key in self.item_vars:
                if key not in {"item_type","purity"}:self.item_vars[key].set("")
            self.item_vars["quantity"].set("1");self.item_vars["workmanship_cost"].set("0");self.item_vars["discount"].set("0");self.item_vars["suggested_sale_price"].set("0")
            self.selected_presets["description"]=None;self.selected_presets["weight_grams"]=None;self.render_preset_buttons()
            self.show_pattern_image()
        except Exception as error:
            message=str(error)
            field_map=(("จำนวนชิ้น","quantity"),("น้ำหนัก","weight_grams"),("เปอร์เซ็นต์","purity"),("ต้นทุนทอง","gold_cost"),("ค่ากำเหน็จ","workmanship_cost"),("ส่วนลด","discount"),("ราคาขาย","suggested_sale_price"))
            key=next((field for text,field in field_map if text in message),None)
            self.invalid_field(key,message)

    def invalid_field(self,key,message):
        messagebox.showwarning("ข้อมูลไม่ถูกต้อง",message,parent=self)
        try:
            if key in self.preset_frames:
                buttons=self.preset_frames[key].winfo_children()
                (buttons[0] if buttons else self.preset_frames[key]).focus_set()
            elif key in self.item_widgets:
                widget=self.item_widgets[key];widget.focus_set();widget.selection_range(0,"end")
        except Exception:pass

    def refresh_lines(self):
        try:display_lines=apply_invoice_vat(self.lines,self.header_vars["invoice_vat_amount"].get())
        except ValueError:display_lines=self.lines
        self.tree.delete(*self.tree.get_children())
        for i,line in enumerate(display_lines,1):
            self.tree.insert("","end",iid=str(i-1),values=(i,line["item_type"],line["description"],f'{line["purity"]:g}',f'{line["weight_grams"]:,.3f}',line["quantity"],f'{line["unit_subtotal"]*line["quantity"]:,.2f}',f'{line["unit_vat"]*line["quantity"]:,.2f}',f'{line["unit_total"]*line["quantity"]:,.2f}',line.get("storage_location","")))
        qty=sum(x["quantity"] for x in display_lines);total=sum(x["unit_total"]*x["quantity"] for x in display_lines)
        self.summary_var.set(f"{len(self.lines)} รายการ | {qty} ชิ้น | ยอดรวม {total:,.2f} บาท")

    def remove_line(self):
        selected=self.tree.selection()
        if not selected:return
        for index in sorted((int(x) for x in selected),reverse=True):self.lines.pop(index)
        self.refresh_lines()

    def confirm(self):
        supplier_id=self.supplier_map.get(self.header_vars["supplier"].get())
        try:
            header={key:var.get().strip() for key,var in self.header_vars.items()};header["supplier_id"]=supplier_id
            for key in ("received_date","document_date","payment_due_date"):
                header[key]=parse_thai_date_to_iso(header[key]) if header[key] else ""
            try:header["invoice_vat_amount"]=float(header["invoice_vat_amount"] or 0)
            except ValueError:raise ValueError("VAT ตามใบกำกับภาษีต้องเป็นตัวเลข")
            calculated=apply_invoice_vat(self.lines,header["invoice_vat_amount"])
            result_preview=f"จำนวน {sum(x['quantity'] for x in calculated)} ชิ้น\nVAT ตามใบกำกับภาษี {header['invoice_vat_amount']:,.2f} บาท\nยอดรวม {sum(x['unit_total']*x['quantity'] for x in calculated):,.2f} บาท"
            if not messagebox.askyesno("ยืนยันรับทองใหม่",result_preview+"\n\nยืนยันรับสินค้าเข้าสต็อก?",parent=self):return
            result=confirm_new_gold_receipt(header,self.lines,self.user.get("id"))
            messagebox.showinfo("สำเร็จ",f"สร้างใบรับ {result['receipt_no']}\nสินค้า {result['total_quantity']} ชิ้น\nยอดรวม {result['grand_total']:,.2f} บาท",parent=self)
            from modules.stock_receipt import offer_stock_prints
            offer_stock_prints(self,result["receipt_id"])
            self.lines=[];self.refresh_lines();self.header_vars["supplier_document_no"].set("");self.header_vars["tax_invoice_no"].set("")
            if hasattr(self.parent,"refresh_dashboard"):self.parent.refresh_dashboard()
        except Exception as error:messagebox.showerror("รับเข้าไม่ได้",str(error),parent=self)
