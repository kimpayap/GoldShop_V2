import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from modules.customers import (
    add_customer,
    update_customer,
    search_customers,
    find_customer_by_citizen_id,
)
from modules.thai_id_card import ThaiIDCardReader
from modules.thai_datetime import format_thai_date, format_thai_datetime
from ui.theme import apply_theme, open_fullscreen, back_to_dashboard


BASE_DIR = Path(__file__).resolve().parent.parent


class CustomerWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.selected_customer_id = None
        self.photo_path = ""
        self.photo_image = None
        self.busy = False

        self.title("จัดการข้อมูลลูกค้า")
        self.geometry("1250x800")
        self.minsize(1050, 700)

        open_fullscreen(self)
        apply_theme(self)

        self.create_widgets()
        self.load_customers()

    # =====================================================
    # UI
    # =====================================================

    def create_widgets(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="👤 จัดการข้อมูลลูกค้า", font=("Arial", 22, "bold")).pack(side="left")
        ttk.Button(header, text="← กลับ Dashboard", command=lambda: back_to_dashboard(self)).pack(side="right")

        form = ttk.LabelFrame(main, text="ข้อมูลลูกค้า", padding=12)
        form.pack(fill="x")

        # -------------------------
        # Photo / card buttons
        # -------------------------
        photo_frame = ttk.LabelFrame(form, text="รูปลูกค้า", padding=8)
        photo_frame.grid(
            row=0,
            column=0,
            rowspan=10,
            padx=(0, 16),
            sticky="ns",
        )

        self.photo_label = ttk.Label(
            photo_frame,
            text="ยังไม่มีรูป",
            anchor="center",
            justify="center",
            width=22,
        )
        self.photo_label.pack(
            ipadx=20,
            ipady=60,
            fill="both",
            expand=True,
        )

        self.read_btn = ttk.Button(
            photo_frame,
            text="💳 อ่านบัตรประชาชน",
            command=self.read_card,
        )
        self.read_btn.pack(fill="x", pady=(8, 4))

        ttk.Button(
            photo_frame,
            text="✍️ กรอกข้อมูลเอง",
            command=self.manual,
        ).pack(fill="x", pady=4)

        self.status = tk.StringVar(value="พร้อมใช้งาน")
        ttk.Label(
            photo_frame,
            textvariable=self.status,
            wraplength=190,
            justify="center",
        ).pack(pady=8)

        # -------------------------
        # Variables
        # -------------------------
        self.v = {
            key: tk.StringVar()
            for key in [
                "prefix",
                "first",
                "last",
                "cid",
                "phone",
                "thai",
                "eng",
                "birth",
                "gender",
                "issuer",
                "issue",
                "expire",
            ]
        }

        # -------------------------
        # Document
        # -------------------------
        ttk.Label(form, text="ประเภทเอกสาร").grid(
            row=0, column=1, sticky="w", padx=6, pady=4
        )
        self.identity = tk.StringVar(value="ไม่มีเอกสาร")
        ttk.Combobox(
            form,
            textvariable=self.identity,
            state="readonly",
            values=(
                "บัตรประชาชน",
                "หนังสือเดินทาง",
                "ใบขับขี่",
                "เอกสารอื่น",
                "ไม่มีเอกสาร",
            ),
            width=30,
        ).grid(row=0, column=2, sticky="ew", padx=6, pady=4)

        ttk.Label(form, text="เลขบัตรประชาชน").grid(
            row=0, column=3, sticky="w", padx=6, pady=4
        )
        ttk.Entry(
            form,
            textvariable=self.v["cid"],
            width=30,
        ).grid(row=0, column=4, sticky="ew", padx=6, pady=4)

        # -------------------------
        # Name
        # -------------------------
        ttk.Label(form, text="คำนำหน้า").grid(
            row=1, column=1, sticky="w", padx=6, pady=4
        )
        ttk.Entry(
            form,
            textvariable=self.v["prefix"],
            width=15,
        ).grid(row=1, column=2, sticky="ew", padx=6, pady=4)

        ttk.Label(form, text="ชื่อ").grid(
            row=1, column=3, sticky="w", padx=6, pady=4
        )
        ttk.Entry(
            form,
            textvariable=self.v["first"],
        ).grid(row=1, column=4, sticky="ew", padx=6, pady=4)

        ttk.Label(form, text="นามสกุล").grid(
            row=2, column=1, sticky="w", padx=6, pady=4
        )
        ttk.Entry(
            form,
            textvariable=self.v["last"],
        ).grid(row=2, column=2, sticky="ew", padx=6, pady=4)

        ttk.Label(form, text="เบอร์โทร").grid(
            row=2, column=3, sticky="w", padx=6, pady=4
        )
        ttk.Entry(
            form,
            textvariable=self.v["phone"],
        ).grid(row=2, column=4, sticky="ew", padx=6, pady=4)

        ttk.Label(form, text="ชื่อภาษาไทยจากบัตร").grid(
            row=3, column=1, sticky="w", padx=6, pady=4
        )
        ttk.Entry(
            form,
            textvariable=self.v["thai"],
        ).grid(row=3, column=2, columnspan=3, sticky="ew", padx=6, pady=4)

        ttk.Label(form, text="English Name").grid(
            row=4, column=1, sticky="w", padx=6, pady=4
        )
        ttk.Entry(
            form,
            textvariable=self.v["eng"],
        ).grid(row=4, column=2, columnspan=3, sticky="ew", padx=6, pady=4)

        # -------------------------
        # Personal data
        # -------------------------
        ttk.Label(form, text="วันเกิด").grid(
            row=5, column=1, sticky="w", padx=6, pady=4
        )
        ttk.Entry(form, textvariable=self.v["birth"]).grid(
            row=5, column=2, sticky="ew", padx=6, pady=4
        )

        ttk.Label(form, text="เพศ").grid(
            row=5, column=3, sticky="w", padx=6, pady=4
        )
        ttk.Entry(form, textvariable=self.v["gender"]).grid(
            row=5, column=4, sticky="ew", padx=6, pady=4
        )

        ttk.Label(form, text="ผู้ออกบัตร").grid(
            row=6, column=1, sticky="w", padx=6, pady=4
        )
        ttk.Entry(form, textvariable=self.v["issuer"]).grid(
            row=6, column=2, sticky="ew", padx=6, pady=4
        )

        ttk.Label(form, text="วันออกบัตร").grid(
            row=6, column=3, sticky="w", padx=6, pady=4
        )
        ttk.Entry(form, textvariable=self.v["issue"]).grid(
            row=6, column=4, sticky="ew", padx=6, pady=4
        )

        ttk.Label(form, text="วันหมดอายุ").grid(
            row=7, column=1, sticky="w", padx=6, pady=4
        )
        ttk.Entry(form, textvariable=self.v["expire"]).grid(
            row=7, column=2, sticky="ew", padx=6, pady=4
        )

        # -------------------------
        # Address / note
        # -------------------------
        ttk.Label(form, text="ที่อยู่").grid(
            row=8, column=1, sticky="nw", padx=6, pady=4
        )
        self.address = tk.Text(form, height=3, wrap="word")
        self.address.grid(
            row=8,
            column=2,
            columnspan=3,
            sticky="ew",
            padx=6,
            pady=4,
        )

        ttk.Label(form, text="หมายเหตุ").grid(
            row=9, column=1, sticky="w", padx=6, pady=4
        )
        self.note = ttk.Entry(form)
        self.note.grid(
            row=9,
            column=2,
            columnspan=3,
            sticky="ew",
            padx=6,
            pady=4,
        )

        # -------------------------
        # Buttons
        # -------------------------
        button_frame = ttk.Frame(form)
        button_frame.grid(
            row=10,
            column=0,
            columnspan=5,
            pady=(10, 0),
        )

        self.save_btn = ttk.Button(
            button_frame,
            text="💾 บันทึกลูกค้า",
            command=self.save,
        )
        self.save_btn.pack(side="left", padx=4)

        self.update_btn = ttk.Button(
            button_frame,
            text="✏️ บันทึกการแก้ไข",
            command=self.update,
            state="disabled",
        )
        self.update_btn.pack(side="left", padx=4)

        ttk.Button(
            button_frame,
            text="🧹 ล้างข้อมูล",
            command=self.clear,
        ).pack(side="left", padx=4)

        form.columnconfigure(2, weight=1)
        form.columnconfigure(4, weight=2)

        # =================================================
        # Search
        # =================================================
        search_frame = ttk.Frame(main, padding=(0, 10, 0, 5))
        search_frame.pack(fill="x")

        ttk.Label(search_frame, text="🔎 ค้นหา").pack(side="left")

        self.search = ttk.Entry(search_frame, width=42)
        self.search.pack(side="left", padx=8)
        self.search.bind("<Return>", lambda event: self.load_customers())

        ttk.Button(
            search_frame,
            text="ค้นหา",
            command=self.load_customers,
        ).pack(side="left")

        ttk.Button(
            search_frame,
            text="แสดงทั้งหมด",
            command=self.show_all,
        ).pack(side="left", padx=5)

        # =================================================
        # Customer table
        # =================================================
        table_frame = ttk.Frame(main)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "code",
            "name",
            "cid",
            "identity",
            "phone",
            "address",
            "created",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
        )

        headings = {
            "code": "รหัสลูกค้า",
            "name": "ชื่อ-นามสกุล",
            "cid": "เลขบัตร",
            "identity": "เอกสาร",
            "phone": "เบอร์โทร",
            "address": "ที่อยู่",
            "created": "วันที่สมัคร",
        }

        widths = {
            "code": 95,
            "name": 190,
            "cid": 145,
            "identity": 110,
            "phone": 115,
            "address": 300,
            "created": 150,
        }

        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")

        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<Double-1>", self.open_selected)
        self.tree.bind("<<TreeviewSelect>>", self.select)

    # =====================================================
    # Card helpers
    # =====================================================

    @staticmethod
    def split_thai_name(full_name):
        """แยกชื่อที่อ่านจากบัตร เช่น น.ส. อริยา นรจันทร์"""
        text = " ".join((full_name or "").split())
        prefixes = (
            "นาย", "นางสาว", "นาง", "น.ส.",
            "เด็กชาย", "เด็กหญิง", "ด.ช.", "ด.ญ."
        )

        prefix = ""
        for item in sorted(prefixes, key=len, reverse=True):
            if text.startswith(item + " "):
                prefix = item
                text = text[len(item):].strip()
                break
            if text == item:
                prefix = item
                text = ""
                break

        parts = text.split()
        first = parts[0] if parts else ""
        last = " ".join(parts[1:]) if len(parts) > 1 else ""
        return prefix, first, last

    @staticmethod
    def normalize_photo_path(path):
        if not path:
            return ""

        p = Path(path).expanduser()
        if p.is_absolute():
            return str(p)

        # รองรับ path เก่าที่บันทึกเป็น data/customer_photos/...
        return str(BASE_DIR / p)

    # =====================================================
    # Read card
    # =====================================================

    def read_card(self):
        if self.busy:
            return

        self.busy = True
        self.read_btn.config(state="disabled")
        self.status.set("กำลังอ่านบัตร...\nกรุณาเสียบบัตรประชาชน")
        self.update_idletasks()

        try:
            reader = ThaiIDCardReader()
            data = reader.read_card_once()

            if not data or not data.get("success"):
                raise RuntimeError("ไม่สามารถอ่านข้อมูลจากบัตรได้")

            cid = (data.get("citizen_id") or "").strip()
            if not cid:
                raise RuntimeError("ไม่พบเลขบัตรประชาชน")

            old = find_customer_by_citizen_id(cid)
            if old:
                self.load_dict(old)
                messagebox.showwarning(
                    "พบข้อมูลซ้ำ",
                    "เลขบัตรประชาชนนี้มีอยู่ในระบบแล้ว\n"
                    f"รหัสลูกค้า: {old['customer_code']}",
                )
                return

            thai_name = (data.get("thai_name") or "").strip()
            prefix, first, last = self.split_thai_name(thai_name)

            self.v["prefix"].set(prefix)
            self.v["first"].set(first)
            self.v["last"].set(last)
            self.v["cid"].set(cid)
            self.v["thai"].set(thai_name)
            self.v["eng"].set(data.get("english_name") or "")
            self.v["birth"].set(format_thai_date(data.get("birth_date"), fallback=""))
            self.v["gender"].set(data.get("gender") or "")
            self.v["issuer"].set(data.get("issuer") or "")
            self.v["issue"].set(format_thai_date(data.get("issue_date"), fallback=""))
            self.v["expire"].set(format_thai_date(data.get("expire_date"), fallback=""))

            self.identity.set("บัตรประชาชน")

            self.address.delete("1.0", tk.END)
            self.address.insert("1.0", data.get("address") or "")

            self.photo_path = self.normalize_photo_path(
                data.get("photo_path") or ""
            )
            self.show_photo()

            self.status.set("อ่านบัตรสำเร็จ")
            messagebox.showinfo(
                "สำเร็จ",
                "อ่านข้อมูลและรูปจากบัตรสำเร็จ\n\n"
                "ตรวจสอบข้อมูลให้เรียบร้อย แล้วกด 'บันทึกลูกค้า'",
            )

        except Exception as error:
            self.status.set("อ่านบัตรไม่สำเร็จ")
            messagebox.showerror(
                "อ่านบัตรไม่สำเร็จ",
                str(error),
            )
        finally:
            self.busy = False
            self.read_btn.config(state="normal")

    # =====================================================
    # Manual entry
    # =====================================================

    def manual(self):
        self.clear()
        self.identity.set("ไม่มีเอกสาร")
        self.status.set("โหมดกรอกข้อมูลเอง")
        self.v["first"].set("")
        self.v["last"].set("")

    # =====================================================
    # Photo
    # =====================================================

    def show_photo(self):
        self.photo_image = None

        path = self.normalize_photo_path(self.photo_path)
        self.photo_path = path

        if not path or not os.path.isfile(path):
            self.photo_label.config(
                image="",
                text="ไม่มีรูป\n\nไม่พบไฟล์รูป",
            )
            return

        try:
            from PIL import Image, ImageTk

            image = Image.open(path)
            image.load()
            image.thumbnail((190, 230), Image.LANCZOS)

            self.photo_image = ImageTk.PhotoImage(image)
            self.photo_label.config(
                image=self.photo_image,
                text="",
            )

        except ImportError:
            self.photo_label.config(
                image="",
                text="กรุณาติดตั้ง Pillow\n\npip install pillow",
            )
        except Exception as error:
            self.photo_label.config(
                image="",
                text=f"เปิดรูปไม่ได้\n\n{type(error).__name__}",
            )

    # =====================================================
    # Data
    # =====================================================

    def payload(self):
        return (
            self.v["first"].get(),
            self.v["last"].get(),
            self.v["cid"].get(),
            self.v["phone"].get(),
            self.address.get("1.0", tk.END).strip(),
            self.note.get().strip(),
            self.v["thai"].get(),
            self.v["eng"].get(),
            self.v["birth"].get(),
            self.v["gender"].get(),
            self.v["issuer"].get(),
            self.v["issue"].get(),
            self.v["expire"].get(),
            self.photo_path,
            self.identity.get(),
        )

    def save(self):
        try:
            _, code = add_customer(*self.payload())
            messagebox.showinfo(
                "สำเร็จ",
                f"บันทึกลูกค้าเรียบร้อย\nรหัสลูกค้า: {code}",
            )
            self.clear()
            self.load_customers()
            if hasattr(self.parent, "refresh_dashboard"):
                self.parent.refresh_dashboard()
        except Exception as error:
            messagebox.showerror(
                "ไม่สามารถบันทึกได้",
                str(error),
            )

    def update(self):
        if not self.selected_customer_id:
            return

        try:
            update_customer(
                self.selected_customer_id,
                *self.payload(),
            )
            messagebox.showinfo(
                "สำเร็จ",
                "แก้ไขข้อมูลลูกค้าเรียบร้อย",
            )
            self.clear()
            self.load_customers()
            if hasattr(self.parent, "refresh_dashboard"):
                self.parent.refresh_dashboard()
        except Exception as error:
            messagebox.showerror(
                "ไม่สามารถแก้ไขได้",
                str(error),
            )

    # =====================================================
    # Selection
    # =====================================================

    def select(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return

        values = self.tree.item(selection[0], "values")
        if not values:
            return

        rows = search_customers(values[0])
        if rows:
            self.selected_customer_id = rows[0]["id"]
            self.update_btn.config(state="normal")

    def open_selected(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return

        values = self.tree.item(selection[0], "values")
        if not values:
            return

        rows = search_customers(values[0])
        if rows:
            self.load_dict(rows[0])

    def load_dict(self, customer):
        self.selected_customer_id = customer["id"]

        for key, column in [
            ("first", "first_name"),
            ("last", "last_name"),
            ("cid", "citizen_id"),
            ("phone", "phone"),
            ("thai", "thai_name"),
            ("eng", "english_name"),
            ("birth", "birth_date"),
            ("gender", "gender"),
            ("issuer", "card_issuer"),
            ("issue", "card_issue_date"),
            ("expire", "card_expire_date"),
        ]:
            value = customer.get(column) or ""
            if key in ("birth", "issue", "expire"):
                value = format_thai_date(value, fallback="")
            self.v[key].set(value)

        # แยกคำนำหน้าจากข้อมูลเดิมถ้ามี
        prefix, _, _ = self.split_thai_name(customer.get("thai_name") or "")
        self.v["prefix"].set(prefix)

        self.identity.set(
            customer.get("identity_type") or "ไม่มีเอกสาร"
        )

        self.address.delete("1.0", tk.END)
        self.address.insert(
            "1.0",
            customer.get("address") or "",
        )

        self.note.delete(0, tk.END)
        self.note.insert(0, customer.get("note") or "")

        self.photo_path = self.normalize_photo_path(
            customer.get("photo_path") or ""
        )
        self.show_photo()

        self.save_btn.config(state="disabled")
        self.update_btn.config(state="normal")
        self.status.set(
            f"กำลังแก้ไข {customer['customer_code']}"
        )

    # =====================================================
    # Clear / list
    # =====================================================

    def clear(self):
        self.selected_customer_id = None
        self.photo_path = ""
        self.photo_image = None

        for variable in self.v.values():
            variable.set("")

        self.identity.set("ไม่มีเอกสาร")
        self.address.delete("1.0", tk.END)
        self.note.delete(0, tk.END)
        self.photo_label.config(
            image="",
            text="ยังไม่มีรูป",
        )
        self.status.set("พร้อมใช้งาน")
        self.save_btn.config(state="normal")
        self.update_btn.config(state="disabled")

    def load_customers(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for customer in search_customers(
            self.search.get().strip()
        ):
            name = (
                f"{customer.get('first_name') or ''} "
                f"{customer.get('last_name') or ''}"
            ).strip()

            self.tree.insert(
                "",
                "end",
                values=(
                    customer.get("customer_code", ""),
                    name,
                    customer.get("citizen_id") or "",
                    customer.get("identity_type") or "ไม่มีเอกสาร",
                    customer.get("phone") or "",
                    customer.get("address") or "",
                    format_thai_datetime(customer.get("created_at")),
                ),
            )

    def show_all(self):
        self.search.delete(0, tk.END)
        self.load_customers()
