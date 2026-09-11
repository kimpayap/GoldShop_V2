import tkinter as tk
from tkinter import ttk, messagebox

from modules.suppliers import list_suppliers, get_supplier, save_supplier, toggle_supplier
from modules.thai_datetime import format_thai_datetime
from ui.theme import apply_theme, open_fullscreen, back_to_dashboard


class SupplierWindow(tk.Toplevel):
    TYPES = ("ผู้จำหน่าย", "คู่ค้า", "ผู้จำหน่ายและคู่ค้า")

    def __init__(self, parent, user=None):
        super().__init__(parent)
        self.parent = parent; self.user = user or {}; self.selected_id = None
        self.title("ผู้จำหน่ายและคู่ค้า - Gold Shop System")
        self.geometry("1280x820"); self.minsize(1050, 700)
        open_fullscreen(self); apply_theme(self)
        self.create_widgets(); self.load_suppliers()

    def create_widgets(self):
        head = ttk.Frame(self, padding=12); head.pack(fill="x")
        ttk.Label(head, text="🏢 ผู้จำหน่ายและคู่ค้า", font=("Arial", 24, "bold")).pack(side="left")
        ttk.Button(head, text="← กลับ Dashboard", command=lambda: back_to_dashboard(self)).pack(side="right")

        form = ttk.LabelFrame(self, text="ข้อมูลคู่ค้า", padding=12); form.pack(fill="x", padx=12, pady=6)
        keys = ("supplier_type","business_name","tax_id","contact_name","phone","email","address","bank_account","notes")
        self.vars = {key: tk.StringVar() for key in keys}
        self.vars["supplier_type"].set(self.TYPES[0])
        fields = (
            ("ประเภท", "supplier_type"), ("ชื่อกิจการ/คู่ค้า", "business_name"), ("เลขผู้เสียภาษี", "tax_id"),
            ("ผู้ติดต่อ", "contact_name"), ("โทรศัพท์", "phone"), ("อีเมล", "email"),
            ("ที่อยู่", "address"), ("ธนาคาร/เลขบัญชี", "bank_account"), ("หมายเหตุ", "notes"),
        )
        for i,(label,key) in enumerate(fields):
            row=(i//3)*2; col=(i%3)*2
            ttk.Label(form,text=label,font=("Arial",12,"bold")).grid(row=row,column=col,sticky="w",padx=5,pady=(3,0))
            if key=="supplier_type": widget=ttk.Combobox(form,textvariable=self.vars[key],values=self.TYPES,state="readonly")
            else: widget=ttk.Entry(form,textvariable=self.vars[key])
            widget.grid(row=row+1,column=col,columnspan=2,sticky="ew",padx=5,pady=(0,5),ipady=5)
        for col in range(6): form.columnconfigure(col,weight=1)
        actions=ttk.Frame(form);actions.grid(row=6,column=0,columnspan=6,sticky="e")
        ttk.Button(actions,text="เพิ่มข้อมูลใหม่",command=self.clear_form).pack(side="left",padx=4)
        ttk.Button(actions,text="💾 บันทึก",style="TouchPrimary.TButton",command=self.save).pack(side="left",padx=4)
        ttk.Button(actions,text="เปิด/ปิดการใช้งาน",command=self.toggle).pack(side="left",padx=4)

        search=ttk.Frame(self,padding=(12,5));search.pack(fill="x")
        self.search_var=tk.StringVar()
        ttk.Entry(search,textvariable=self.search_var,font=("Arial",15),width=36).pack(side="left",padx=4,ipady=6)
        ttk.Button(search,text="🔎 ค้นหา",command=self.load_suppliers).pack(side="left",padx=4)
        ttk.Button(search,text="ทั้งหมด",command=lambda:(self.search_var.set(""),self.load_suppliers())).pack(side="left",padx=4)

        box=ttk.LabelFrame(self,text="ทะเบียนผู้จำหน่ายและคู่ค้า",padding=8);box.pack(fill="both",expand=True,padx=12,pady=(0,12))
        cols=("code","type","name","tax","contact","phone","status","updated")
        self.tree=ttk.Treeview(box,columns=cols,show="headings")
        for key,title,width in (("code","รหัส",100),("type","ประเภท",150),("name","ชื่อกิจการ",230),("tax","เลขผู้เสียภาษี",150),("contact","ผู้ติดต่อ",140),("phone","โทรศัพท์",130),("status","สถานะ",90),("updated","แก้ไขล่าสุด",190)):
            self.tree.heading(key,text=title);self.tree.column(key,width=width,anchor="center")
        self.tree.pack(fill="both",expand=True);self.tree.bind("<<TreeviewSelect>>",self.select_supplier)

    def load_suppliers(self):
        self.tree.delete(*self.tree.get_children())
        for row in list_suppliers(self.search_var.get()):
            self.tree.insert("","end",iid=str(row["id"]),values=(row["supplier_code"],row["supplier_type"],row["business_name"],row["tax_id"],row["contact_name"],row["phone"],"ใช้งาน" if row["active"] else "ปิด",format_thai_datetime(row["updated_at"])))

    def select_supplier(self,event=None):
        selected=self.tree.selection()
        if not selected:return
        self.selected_id=int(selected[0]);row=get_supplier(self.selected_id)
        for key,var in self.vars.items():var.set(row.get(key) or "")

    def clear_form(self):
        self.selected_id=None
        for var in self.vars.values():var.set("")
        self.vars["supplier_type"].set(self.TYPES[0]);self.tree.selection_remove(*self.tree.selection())

    def save(self):
        try:
            data={key:var.get() for key,var in self.vars.items()};data["active"]=True if self.selected_id is None else bool(get_supplier(self.selected_id)["active"])
            saved=save_supplier(data,self.selected_id);self.selected_id=saved["id"]
            messagebox.showinfo("สำเร็จ",f"บันทึกคู่ค้า {saved['supplier_code']} แล้ว",parent=self);self.load_suppliers()
            iid=str(saved["id"]);self.tree.selection_set(iid);self.tree.focus(iid);self.tree.see(iid)
        except Exception as error:messagebox.showerror("บันทึกไม่ได้",str(error),parent=self)

    def toggle(self):
        if not self.selected_id:
            messagebox.showwarning("คู่ค้า","กรุณาเลือกคู่ค้า",parent=self);return
        try:
            row=toggle_supplier(self.selected_id);messagebox.showinfo("สถานะ",f"{row['supplier_code']} {'เปิดใช้งาน' if row['active'] else 'ปิดใช้งาน'}แล้ว",parent=self);self.load_suppliers()
        except Exception as error:messagebox.showerror("เปลี่ยนสถานะไม่ได้",str(error),parent=self)
