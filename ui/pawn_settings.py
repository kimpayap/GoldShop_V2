import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from PIL import Image, ImageTk

from modules.pawn import (
    get_settings, save_settings,
    list_gold_types, list_gold_details, list_gold_purities,
    save_gold_setting, toggle_gold_setting, move_gold_setting_v2,
    set_gold_setting_order,
    list_weight_options, save_weight_option, toggle_weight_option,
    move_weight_option_v2, set_weight_option_order,
)
from ui.theme import THEMES, get_theme_key, save_theme, apply_theme, open_fullscreen, back_to_dashboard
from modules.business_settings import get_business_settings, save_business_settings
from modules.pattern_images import save_pattern_image, remove_pattern_image


class ScrollRows(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.window_id, width=e.width))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")


class GoldSettingTab(ttk.Frame):
    """ตั้งค่ารายการทองแบบ Touch: ทุกแถวมีปุ่มสถานะ/ขึ้น/ลงของตัวเอง"""
    def __init__(self, parent, table, title, with_percent=False):
        super().__init__(parent, padding=12)
        self.table = table
        self.title_text = title
        self.with_percent = with_percent
        self.editing_id = None
        self.name_var = tk.StringVar()
        self.percent_var = tk.StringVar()
        self.pending_image = None
        self.preview_photo = None
        self.build()
        self.refresh()

    def rows(self):
        if self.table == "gold_types":
            return list_gold_types(False)
        if self.table == "gold_details":
            return list_gold_details(False)
        return list_gold_purities(False)

    def build(self):
        ttk.Label(self, text=self.title_text, font=("Arial", 20, "bold")).pack(anchor="w", pady=(0, 8))

        form = ttk.LabelFrame(self, text="เพิ่ม / แก้ไข", padding=10)
        form.pack(fill="x", pady=(0, 10))
        ttk.Label(form, text="ชื่อ", font=("Arial", 14, "bold")).pack(side="left", padx=5)
        ttk.Entry(form, textvariable=self.name_var, font=("Arial", 16), width=24).pack(side="left", padx=5, ipady=8)
        if self.with_percent:
            ttk.Label(form, text="เปอร์เซ็นต์", font=("Arial", 14, "bold")).pack(side="left", padx=(10, 5))
            ttk.Entry(form, textvariable=self.percent_var, font=("Arial", 16), width=8).pack(side="left", padx=5, ipady=8)
        ttk.Button(form, text="💾 บันทึก", style="Touch.TButton", command=self.save).pack(side="left", padx=6)
        ttk.Button(form, text="🧹 ยกเลิกแก้ไข", style="Touch.TButton", command=self.clear).pack(side="left", padx=6)
        if self.table == "gold_details":
            ttk.Button(form,text="🖼 เลือกรูปตัวอย่าง",style="Touch.TButton",command=self.choose_image).pack(side="left",padx=6)
            ttk.Button(form,text="ลบรูป",style="Touch.TButton",command=self.remove_image).pack(side="left",padx=4)
            self.image_preview=ttk.Label(form,text="ยังไม่มีรูป",width=14,anchor="center");self.image_preview.pack(side="left",padx=8)

        ttk.Label(
            self,
            text="แตะปุ่มในแถวได้โดยตรง ไม่ต้องเลือกแถวก่อน",
            font=("Arial", 13)
        ).pack(anchor="w", pady=(0, 6))

        head = ttk.Frame(self)
        head.pack(fill="x", padx=(4, 20))
        for text, width in (("ลำดับ", 8), ("รายการ", 28), ("สถานะ", 13), ("จัดลำดับ", 20), ("แก้ไข", 10)):
            ttk.Label(head, text=text, font=("Arial", 13, "bold"), width=width, anchor="center").pack(side="left", padx=3)

        self.rows_box = ScrollRows(self)
        self.rows_box.pack(fill="both", expand=True)

    def refresh(self):
        for child in self.rows_box.inner.winfo_children():
            child.destroy()
        rows = self.rows()
        for index, row in enumerate(rows, 1):
            line = ttk.Frame(self.rows_box.inner, padding=(4, 5))
            line.pack(fill="x")
            ttk.Label(line, text=str(index), font=("Arial", 14, "bold"), width=8, anchor="center").pack(side="left", padx=3)
            label = row["name"]
            if self.with_percent:
                label = f'{row["name"]}  ({float(row["percent"]):g}%)'
            ttk.Label(line, text=label, font=("Arial", 15), width=28, anchor="w").pack(side="left", padx=3)

            if int(row["active"] or 0):
                status_text = "🟢 ใช้งาน"
            else:
                status_text = "🔴 ปิด"
            ttk.Button(
                line, text=status_text, style="Touch.TButton",
                command=lambda rid=row["id"]: self.toggle_direct(rid)
            ).pack(side="left", padx=3, ipadx=3)

            move_box = ttk.Frame(line)
            move_box.pack(side="left", padx=4)
            ttk.Button(
                move_box, text="⬆", style="Touch.TButton",
                command=lambda rid=row["id"]: self.move_direct(rid, -1)
            ).pack(side="left", padx=2)
            ttk.Button(
                move_box, text="⬇", style="Touch.TButton",
                command=lambda rid=row["id"]: self.move_direct(rid, 1)
            ).pack(side="left", padx=2)

            ttk.Button(
                line, text="✏ แก้ไข", style="Touch.TButton",
                command=lambda r=dict(row): self.edit(r)
            ).pack(side="left", padx=4)
            if self.table == "gold_details":
                ttk.Label(line,text="🖼 มีรูป" if row.get("image_path") and Path(row["image_path"]).is_file() else "ไม่มีรูป",width=10,anchor="center").pack(side="left",padx=3)

    def toggle_direct(self, item_id):
        try:
            toggle_gold_setting(self.table, item_id)
            self.refresh()
        except Exception as error:
            messagebox.showerror("เปลี่ยนสถานะไม่ได้", str(error), parent=self)

    def move_direct(self, item_id, direction):
        try:
            move_gold_setting_v2(self.table, item_id, direction)
            self.refresh()
        except Exception as error:
            messagebox.showerror("เปลี่ยนลำดับไม่ได้", str(error), parent=self)

    def edit(self, row):
        self.editing_id = int(row["id"])
        self.name_var.set(row["name"])
        if self.with_percent:
            self.percent_var.set(str(row["percent"]))
        if self.table == "gold_details":self.show_preview(row.get("image_path"))

    def clear(self):
        self.editing_id = None
        self.name_var.set("")
        self.percent_var.set("")
        self.pending_image=None
        if self.table == "gold_details":self.show_preview(None)

    def show_preview(self,path):
        self.preview_photo=None
        if path and Path(path).is_file():
            try:
                image=Image.open(path);image.thumbnail((90,70));self.preview_photo=ImageTk.PhotoImage(image);self.image_preview.configure(image=self.preview_photo,text="")
                return
            except Exception:pass
        self.image_preview.configure(image="",text="ยังไม่มีรูป")

    def choose_image(self):
        path=filedialog.askopenfilename(parent=self,title="เลือกรูปตัวอย่างลายทอง",filetypes=(("ไฟล์รูป","*.jpg *.jpeg *.png *.webp *.gif *.bmp"),("ทุกไฟล์","*.*")))
        if path:self.pending_image=path;self.show_preview(path)

    def remove_image(self):
        if not self.editing_id:
            self.pending_image=None;self.show_preview(None);return
        if messagebox.askyesno("ลบรูปตัวอย่าง","ต้องการลบรูปของลายทองนี้หรือไม่?",parent=self):
            try:remove_pattern_image(self.editing_id);self.pending_image=None;self.show_preview(None);self.refresh()
            except Exception as error:messagebox.showerror("ลบรูปไม่ได้",str(error),parent=self)

    def save(self):
        try:
            active = 1
            if self.editing_id:
                old = next((r for r in self.rows() if int(r["id"]) == self.editing_id), None)
                if old:
                    active = int(old["active"] or 0)
            saved_id=save_gold_setting(
                self.table,
                self.editing_id,
                self.name_var.get(),
                self.percent_var.get() if self.with_percent else None,
                active,
            )
            if self.table == "gold_details" and self.pending_image:save_pattern_image(saved_id,self.pending_image)
            self.clear()
            self.refresh()
        except Exception as error:
            messagebox.showerror("บันทึกไม่ได้", str(error), parent=self)


class WeightSettingTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=12)
        self.editing_id = None
        self.unit = tk.StringVar(value="baht")
        self.label = tk.StringVar()
        self.value = tk.StringVar()
        self.build()
        self.refresh()

    def build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="⚖ ปุ่มน้ำหนัก", font=("Arial", 20, "bold")).pack(side="left")
        ttk.Radiobutton(top, text="บาททอง", variable=self.unit, value="baht", command=self.unit_changed).pack(side="left", padx=(25, 6))
        ttk.Radiobutton(top, text="กรัม", variable=self.unit, value="gram", command=self.unit_changed).pack(side="left", padx=6)

        form = ttk.LabelFrame(self, text="เพิ่ม / แก้ไขปุ่มน้ำหนัก", padding=10)
        form.pack(fill="x", pady=(0, 10))
        ttk.Label(form, text="ชื่อปุ่ม", font=("Arial", 14, "bold")).pack(side="left", padx=5)
        ttk.Entry(form, textvariable=self.label, font=("Arial", 16), width=18).pack(side="left", padx=5, ipady=8)
        ttk.Label(form, text="ค่า", font=("Arial", 14, "bold")).pack(side="left", padx=(10, 5))
        ttk.Entry(form, textvariable=self.value, font=("Arial", 16), width=10).pack(side="left", padx=5, ipady=8)
        ttk.Button(form, text="💾 บันทึก", style="Touch.TButton", command=self.save).pack(side="left", padx=6)
        ttk.Button(form, text="🧹 ยกเลิกแก้ไข", style="Touch.TButton", command=self.clear).pack(side="left", padx=6)

        self.rows_box = ScrollRows(self)
        self.rows_box.pack(fill="both", expand=True)

    def unit_changed(self):
        self.clear(keep_unit=True)
        self.refresh()

    def refresh(self):
        for child in self.rows_box.inner.winfo_children():
            child.destroy()
        rows = list_weight_options(self.unit.get(), False)
        for index, row in enumerate(rows, 1):
            line = ttk.Frame(self.rows_box.inner, padding=(4, 5))
            line.pack(fill="x")
            ttk.Label(line, text=str(index), font=("Arial", 14, "bold"), width=7, anchor="center").pack(side="left")
            ttk.Label(line, text=row["label"], font=("Arial", 15), width=22, anchor="w").pack(side="left", padx=4)
            unit_label = "บาททอง" if row["unit"] == "baht" else "กรัม"
            ttk.Label(line, text=f'{float(row["value"]):g} {unit_label}', font=("Arial", 14), width=16).pack(side="left", padx=4)
            status = "🟢 ใช้งาน" if int(row["active"] or 0) else "🔴 ปิด"
            ttk.Button(
                line, text=status, style="Touch.TButton",
                command=lambda rid=row["id"]: self.toggle_direct(rid)
            ).pack(side="left", padx=4)
            ttk.Button(
                line, text="⬆", style="Touch.TButton",
                command=lambda rid=row["id"]: self.move_direct(rid, -1)
            ).pack(side="left", padx=2)
            ttk.Button(
                line, text="⬇", style="Touch.TButton",
                command=lambda rid=row["id"]: self.move_direct(rid, 1)
            ).pack(side="left", padx=2)
            ttk.Button(
                line, text="✏ แก้ไข", style="Touch.TButton",
                command=lambda r=dict(row): self.edit(r)
            ).pack(side="left", padx=4)

    def toggle_direct(self, item_id):
        try:
            toggle_weight_option(item_id)
            self.refresh()
        except Exception as error:
            messagebox.showerror("เปลี่ยนสถานะไม่ได้", str(error), parent=self)

    def move_direct(self, item_id, direction):
        try:
            move_weight_option_v2(item_id, direction)
            self.refresh()
        except Exception as error:
            messagebox.showerror("เปลี่ยนลำดับไม่ได้", str(error), parent=self)

    def edit(self, row):
        self.editing_id = int(row["id"])
        self.unit.set(row["unit"])
        self.label.set(row["label"])
        self.value.set(str(row["value"]))

    def clear(self, keep_unit=True):
        current = self.unit.get()
        self.editing_id = None
        self.label.set("")
        self.value.set("")
        if keep_unit:
            self.unit.set(current)

    def save(self):
        try:
            active = 1
            if self.editing_id:
                old = next((r for r in list_weight_options(None, False) if int(r["id"]) == self.editing_id), None)
                if old:
                    active = int(old["active"] or 0)
            save_weight_option(
                self.editing_id, self.unit.get(), self.label.get(), self.value.get(), active
            )
            self.clear()
            self.refresh()
        except Exception as error:
            messagebox.showerror("บันทึกไม่ได้", str(error), parent=self)


class RenewalOptionTab(ttk.Frame):
    def __init__(self,parent):
        super().__init__(parent,padding=12)
        self.selected_id=None
        self.label_var=tk.StringVar();self.months_var=tk.StringVar()
        self.build();self.refresh()

    def build(self):
        top=ttk.Frame(self);top.pack(fill="x",pady=(0,8))
        ttk.Label(top,text="ชื่อปุ่ม",font=("Arial",14,"bold")).pack(side="left")
        ttk.Entry(top,textvariable=self.label_var,font=("Arial",15),width=16).pack(side="left",padx=5,ipady=6)
        ttk.Label(top,text="จำนวนเดือน",font=("Arial",14,"bold")).pack(side="left",padx=(12,0))
        ttk.Entry(top,textvariable=self.months_var,font=("Arial",15),width=8).pack(side="left",padx=5,ipady=6)
        ttk.Button(top,text="➕ เพิ่ม/บันทึก",style="Touch.TButton",command=self.save).pack(side="left",padx=5)
        ttk.Button(top,text="ล้าง",style="Touch.TButton",command=self.clear).pack(side="left",padx=5)
        self.tree=ttk.Treeview(self,columns=("id","label","months","active","order"),show="headings",height=11)
        for c,h,w in [("id","ID",60),("label","ปุ่ม",240),("months","เดือน",100),("active","สถานะ",120),("order","ลำดับ",90)]:
            self.tree.heading(c,text=h);self.tree.column(c,width=w,anchor="center")
        self.tree.pack(fill="both",expand=True);self.tree.bind("<<TreeviewSelect>>",self.select)
        buttons=ttk.Frame(self);buttons.pack(fill="x",pady=8)
        ttk.Button(buttons,text="🟢 ใช้งาน",style="Touch.TButton",command=lambda:self.set_active(1)).pack(side="left",padx=4)
        ttk.Button(buttons,text="🔴 ปิด",style="Touch.TButton",command=lambda:self.set_active(0)).pack(side="left",padx=4)
        ttk.Button(buttons,text="⬆ เลื่อนขึ้น",style="Touch.TButton",command=lambda:self.move(-1)).pack(side="left",padx=4)
        ttk.Button(buttons,text="⬇ เลื่อนลง",style="Touch.TButton",command=lambda:self.move(1)).pack(side="left",padx=4)

    def refresh(self):
        for x in self.tree.get_children():self.tree.delete(x)
        for r in list_renewal_options(False):
            self.tree.insert("","end",iid=str(r["id"]),values=(r["id"],r["label"],r["months"],"ใช้งาน" if r["active"] else "ปิด",r["sort_order"]))

    def select(self,event=None):
        s=self.tree.selection()
        if not s:return
        v=self.tree.item(s[0],"values");self.selected_id=int(v[0]);self.label_var.set(v[1]);self.months_var.set(v[2])

    def save(self):
        try:save_renewal_option(self.selected_id,self.label_var.get(),self.months_var.get());self.refresh();self.clear()
        except Exception as e:messagebox.showerror("บันทึกไม่ได้",str(e),parent=self)

    def set_active(self,active):
        if not self.selected_id:return
        set_renewal_option_active(self.selected_id,active);self.refresh()

    def move(self,direction):
        if not self.selected_id:return
        move_renewal_option(self.selected_id,direction);self.refresh();self.tree.selection_set(str(self.selected_id));self.tree.see(str(self.selected_id))

    def clear(self):
        self.selected_id=None;self.label_var.set("");self.months_var.set("")


class PawnSettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("ตั้งค่าระบบขายฝาก")
        self.geometry("1280x820")
        self.minsize(1050, 700)
        open_fullscreen(self)
        self.transient(parent)
        self.grab_set()
        self.create_style()
        apply_theme(self)
        self.create_widgets()
        self.load_settings()

    def create_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Touch.TButton", font=("Arial", 14, "bold"), padding=(13, 10))
        style.configure("TNotebook.Tab", font=("Arial", 14, "bold"), padding=(16, 10))

    def create_widgets(self):
        header = ttk.Frame(self, padding=14)
        header.pack(fill="x")
        ttk.Label(header, text="⚙ ตั้งค่าระบบขายฝาก", font=("Arial", 24, "bold")).pack(side="left")
        ttk.Button(header, text="← กลับ Dashboard", style="Touch.TButton", command=lambda: back_to_dashboard(self)).pack(side="right")

        general = ttk.LabelFrame(self, text="อัตราผลตอบแทนและระยะเวลาขายฝาก", padding=12)
        general.pack(fill="x", padx=14, pady=(0, 8))
        self.series_vars={code:{"rate":tk.StringVar(),"days":tk.StringVar()} for code in ("P","Q")}
        self.gram = tk.StringVar()
        ttk.Label(general,text="ระบบ",font=("Arial",14,"bold")).grid(row=0,column=0,padx=8)
        ttk.Label(general,text="ผลตอบแทน / เดือน",font=("Arial",14,"bold")).grid(row=0,column=1,padx=8)
        ttk.Label(general,text="ระยะเวลาตั้งต้น",font=("Arial",14,"bold")).grid(row=0,column=2,padx=8)
        for row,code in enumerate(("P","Q"),1):
            ttk.Label(general,text=f"ระบบขายฝาก {code}",font=("Arial",15,"bold")).grid(row=row,column=0,padx=8,pady=4,sticky="w")
            ttk.Entry(general,textvariable=self.series_vars[code]["rate"],font=("Arial",16),width=12).grid(row=row,column=1,padx=8,ipady=6)
            ttk.Combobox(general,textvariable=self.series_vars[code]["days"],values=("30","60","90","120"),state="readonly",font=("Arial",15),width=10).grid(row=row,column=2,padx=8,ipady=5)
        ttk.Label(general,text="ทอง 1 บาท",font=("Arial",14,"bold")).grid(row=0,column=3,padx=8)
        ttk.Entry(general,textvariable=self.gram,font=("Arial",16),width=12).grid(row=1,column=3,padx=8,ipady=6)
        ttk.Button(general,text="💾 บันทึกค่า P และ Q",style="Touch.TButton",command=self.save_general).grid(row=2,column=3,padx=12)

        theme_box = ttk.LabelFrame(self, text="Theme ของโปรแกรม", padding=12)
        theme_box.pack(fill="x", padx=14, pady=(0, 8))
        self.theme_var = tk.StringVar()
        self.theme_labels = {data["label"]: key for key, data in THEMES.items()}
        ttk.Label(theme_box, text="เลือกรูปแบบสีและตัวอักษร", font=("Arial", 14, "bold")).pack(side="left", padx=6)
        self.theme_combo = ttk.Combobox(
            theme_box, textvariable=self.theme_var, values=list(self.theme_labels),
            state="readonly", font=("Arial", 14), width=22
        )
        self.theme_combo.pack(side="left", padx=10, ipady=5)
        ttk.Button(theme_box, text="🎨 ใช้ Theme", style="Touch.TButton", command=self.save_selected_theme).pack(side="left", padx=6)
        ttk.Label(theme_box, text="สีและแบบอักษรจะเปลี่ยนทันทีและถูกจดจำเมื่อเปิดโปรแกรมครั้งถัดไป").pack(side="left", padx=12)

        business = ttk.LabelFrame(self, text="ข้อมูลกิจการและการพิมพ์", padding=10)
        business.pack(fill="x", padx=14, pady=(0, 8))
        self.business_vars = {key: tk.StringVar() for key in (
            "business_name", "business_address", "business_phone", "business_tax_id", "receipt_footer", "receipt_paper"
        )}
        fields = (
            ("ชื่อกิจการ", "business_name", 24), ("โทรศัพท์", "business_phone", 18),
            ("เลขผู้เสียภาษี", "business_tax_id", 18), ("ที่อยู่", "business_address", 42),
            ("ข้อความท้ายใบ", "receipt_footer", 28),
        )
        for i, (label, key, width) in enumerate(fields):
            ttk.Label(business, text=label, font=("Arial", 12, "bold")).grid(row=(i//3)*2, column=(i%3)*2, sticky="w", padx=(4,2))
            ttk.Entry(business, textvariable=self.business_vars[key], width=width).grid(row=(i//3)*2+1, column=(i%3)*2, columnspan=2, sticky="ew", padx=4, pady=3, ipady=4)
        ttk.Label(business, text="ขนาดกระดาษ", font=("Arial", 12, "bold")).grid(row=2, column=4, sticky="w", padx=4)
        ttk.Combobox(business, textvariable=self.business_vars["receipt_paper"], values=("A4", "80mm", "9x5.5"), state="readonly", width=12).grid(row=3,column=4,sticky="w",padx=4,ipady=4)
        ttk.Button(business, text="💾 บันทึกข้อมูลกิจการ", style="Touch.TButton", command=self.save_business).grid(row=3,column=5,sticky="e",padx=6)
        for col in range(6): business.columnconfigure(col, weight=1)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=14, pady=8)
        notebook.add(GoldSettingTab(notebook, "gold_types", "ประเภททอง"), text="🥇 ประเภททอง")
        notebook.add(GoldSettingTab(notebook, "gold_details", "รายละเอียด"), text="📋 รายละเอียด")
        notebook.add(GoldSettingTab(notebook, "gold_purities", "%ทอง", True), text="% ทอง")
        notebook.add(WeightSettingTab(notebook), text="⚖ น้ำหนัก")

    def load_settings(self):
        settings = get_settings("P")
        self.gram.set(str(settings["weight_per_baht_gram"]))
        for code in ("P","Q"):
            data=get_settings(code);self.series_vars[code]["rate"].set(str(data["monthly_interest_rate"]));self.series_vars[code]["days"].set(str(data["loan_term_days"]))
        key = get_theme_key()
        self.theme_var.set(THEMES[key]["label"])
        business = get_business_settings()
        for setting_key, variable in self.business_vars.items(): variable.set(business[setting_key])

    def save_business(self):
        try:
            values = {key: variable.get() for key, variable in self.business_vars.items()}
            save_business_settings(values)
            messagebox.showinfo("ข้อมูลกิจการ", "บันทึกข้อมูลกิจการและการพิมพ์แล้ว", parent=self)
        except Exception as error:
            messagebox.showerror("บันทึกไม่ได้", str(error), parent=self)

    def save_selected_theme(self):
        try:
            key = self.theme_labels[self.theme_var.get()]
            save_theme(key)
            apply_theme(self, key)
            apply_theme(self.parent, key)
            messagebox.showinfo("Theme", f"เปลี่ยนเป็น {THEMES[key]['label']} แล้ว", parent=self)
        except Exception as error:
            messagebox.showerror("เปลี่ยน Theme ไม่ได้", str(error), parent=self)

    def save_general(self):
        try:
            for code in ("P","Q"):save_settings(self.series_vars[code]["rate"].get(),self.series_vars[code]["days"].get(),self.gram.get(),code)
            messagebox.showinfo("สำเร็จ", "บันทึกค่าระบบ P และ Q แล้ว", parent=self)
        except Exception as error:
            messagebox.showerror("บันทึกไม่ได้", str(error), parent=self)
