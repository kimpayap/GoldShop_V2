import tkinter as tk
from tkinter import ttk, messagebox

from modules.pawn import list_pawns, get_pawn, calculate_redemption_amount, redeem_pawn
from modules.thai_datetime import format_thai_date, format_thai_datetime
from ui.settings_access import TouchKeypad
from ui.theme import apply_theme, open_fullscreen, back_to_dashboard


class PawnRedeemWindow(tk.Toplevel):
    def __init__(self, parent, user=None, initial_ticket_id=None):
        super().__init__(parent)
        self.parent = parent
        self.user = user or {}
        self.selected_ticket_id = None
        self.title("ไถ่ถอน - Gold Shop System")
        self.geometry("1180x760")
        self.minsize(1000, 680)
        open_fullscreen(self)
        apply_theme(self)
        self.create_widgets()
        self.load_tickets()
        if initial_ticket_id is not None:
            self.select_initial_ticket(initial_ticket_id)

    def create_widgets(self):
        head = ttk.Frame(self, padding=12); head.pack(fill="x")
        ttk.Label(head, text="💰 ไถ่ถอน", font=("Arial", 24, "bold")).pack(side="left")
        ttk.Button(head, text="← กลับ Dashboard", command=lambda: back_to_dashboard(self)).pack(side="right")

        search = ttk.LabelFrame(self, text="1. ค้นหาตั๋วขายฝาก", padding=10); search.pack(fill="x", padx=12, pady=6)
        self.search_var = tk.StringVar()
        ttk.Entry(search, textvariable=self.search_var, font=("Arial", 15), width=36).pack(side="left", padx=5, ipady=7)
        ttk.Button(search, text="🔎 ค้นหา", command=self.load_tickets).pack(side="left", padx=5)
        ttk.Button(search, text="แสดงทั้งหมด", command=lambda: (self.search_var.set(""), self.load_tickets())).pack(side="left", padx=5)
        ttk.Label(search, text="ค้นหาได้จากเลขตั๋ว รหัสลูกค้า ชื่อ หรือเลขบัตรประชาชน").pack(side="left", padx=14)

        body = ttk.Frame(self); body.pack(fill="both", expand=True, padx=12, pady=6)
        left = ttk.LabelFrame(body, text="ตั๋วที่ยังใช้งานอยู่", padding=8); left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        cols = ("series","ticket", "customer", "loan", "opened", "due")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=15)
        for key, title, width in (
            ("series","ระบบ",60),("ticket", "เลขที่ตั๋ว", 110), ("customer", "ลูกค้า", 230),
            ("loan", "เงินต้น", 120), ("opened", "วันที่รับ", 190), ("due", "ครบกำหนด", 170),
        ):
            self.tree.heading(key, text=title); self.tree.column(key, width=width, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.select_ticket)

        right = ttk.LabelFrame(body, text="2. รายละเอียดการไถ่ถอน", padding=14); right.pack(side="left", fill="both", expand=True, padx=(6, 0))
        self.info_var = tk.StringVar(value="กรุณาเลือกตั๋วขายฝาก")
        ttk.Label(right, textvariable=self.info_var, font=("Arial", 14), justify="left").pack(anchor="w", fill="x")
        ttk.Separator(right).pack(fill="x", pady=14)
        self.total_var = tk.StringVar(value="ยอดไถ่โดยประมาณ: -")
        ttk.Label(right, textvariable=self.total_var, font=("Arial", 20, "bold")).pack(anchor="w", pady=8)

        pay = ttk.Frame(right); pay.pack(fill="x", pady=12)
        ttk.Label(pay, text="ยอดรับจริง", font=("Arial", 15, "bold")).pack(side="left")
        self.paid_var = tk.StringVar()
        ttk.Entry(pay, textvariable=self.paid_var, font=("Arial", 18), width=14, justify="right").pack(side="left", padx=8, ipady=7)
        ttk.Button(pay, text="⌨ ระบุยอด", command=self.open_keypad).pack(side="left")

        ttk.Label(right, text="หมายเหตุ", font=("Arial", 14, "bold")).pack(anchor="w", pady=(10, 3))
        self.note_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.note_var, font=("Arial", 15)).pack(fill="x", ipady=7)
        ttk.Button(right, text="✅ ยืนยันไถ่ถอน", style="TouchPrimary.TButton", command=self.confirm_redeem).pack(fill="x", pady=18, ipady=10)

    def load_tickets(self):
        self.tree.delete(*self.tree.get_children())
        for p in list_pawns(self.search_var.get().strip(), "active"):
            self.tree.insert("", "end", iid=str(p["id"]), values=(
                p.get("series_code","P"),p["ticket_no"], p["customer_name"], f'{p["loan_amount"]:,.2f}',
                format_thai_datetime(p["opened_at"]), format_thai_date(p["due_date"]),
            ))

    def select_initial_ticket(self, ticket_id):
        iid = str(ticket_id)
        if self.tree.exists(iid):
            self.tree.selection_set(iid); self.tree.focus(iid); self.tree.see(iid); self.select_ticket()

    def select_ticket(self, event=None):
        selected = self.tree.selection()
        if not selected: return
        self.selected_ticket_id = int(selected[0])
        p = get_pawn(self.selected_ticket_id)
        interest = calculate_redemption_amount(p["id"])
        self.info_var.set(
            f"เลขที่ตั๋ว: {p['ticket_no']}\nลูกค้า: {p['first_name']} {p['last_name']}\n"
            f"วันที่รับขายฝาก: {format_thai_datetime(p['opened_at'])}\nครบกำหนด: {format_thai_date(p['due_date'])}\n"
            f"เงินต้น: {p['loan_amount']:,.2f} บาท\nจำนวนวันที่คิดดอก: {interest['days']} วัน\n"
            f"ผลตอบแทน: {interest['interest']:,.2f} บาท\n"
            + (f"ฐานภาษี: {interest['vat_base']:,.2f} บาท\n"
               f"VAT {interest['vat_rate']:.0f}% (ถอดจากผลตอบแทน): {interest['vat_amount']:,.2f} บาท\n"
               if interest["series_code"] == "Q" else "")
            + f"หลักการ: {interest['reason']}"
        )
        self.total_var.set(f"ยอดไถ่โดยประมาณ: {interest['total']:,.2f} บาท")
        self.paid_var.set(f"{interest['total']:.2f}")

    def open_keypad(self):
        keypad = TouchKeypad(self, self.paid_var, "ยอดรับจริง"); self.wait_window(keypad)

    def confirm_redeem(self):
        if not self.selected_ticket_id:
            messagebox.showwarning("ไถ่ถอน", "กรุณาเลือกตั๋วขายฝาก", parent=self); return
        try:
            paid = float(self.paid_var.get())
            if paid < 0: raise ValueError
        except Exception:
            messagebox.showwarning("ไถ่ถอน", "ยอดรับจริงไม่ถูกต้อง", parent=self); return
        p = get_pawn(self.selected_ticket_id)
        if not p or p["status"] != "active":
            messagebox.showwarning("ไถ่ถอน", "ตั๋วนี้ไม่ได้อยู่ในสถานะใช้งาน", parent=self); self.load_tickets(); return
        if not messagebox.askyesno(
            "ยืนยันไถ่ถอน",
            f"ตั๋ว {p['ticket_no']}\nลูกค้า: {p['first_name']} {p['last_name']}\n"
            + (f"VAT ที่ถอดจากผลตอบแทน: {calculate_redemption_amount(p['id'])['vat_amount']:,.2f} บาท\n"
               if str(p.get('series_code') or 'P').upper() == 'Q' else "")
            + f"ยอดรับจริง: {paid:,.2f} บาท\n\nยืนยันการไถ่ถอน?",
            parent=self,
        ): return
        try:
            calculation = calculate_redemption_amount(p["id"])
            calculation_note = (
                f"{calculation['reason']} | เงินต้น {calculation['principal']:.2f} | "
                f"ผลตอบแทน {calculation['interest']:.2f} | ยอดคำนวณ {calculation['total']:.2f}"
            )
            user_note = self.note_var.get().strip()
            result = redeem_pawn(p["id"], paid, self.user.get("id"), note=calculation_note + (f" | {user_note}" if user_note else ""))
            messagebox.showinfo("สำเร็จ", f"ไถ่ถอนตั๋ว {p['ticket_no']} เรียบร้อย", parent=self)
            if messagebox.askyesno("พิมพ์ใบรับเงิน", "ต้องการพิมพ์ใบรับเงินไถ่ถอนหรือไม่?", parent=self):
                from modules.pawn_receipt import print_redemption_receipt
                print_redemption_receipt(p["id"], result["transaction_id"])
            self.selected_ticket_id = None; self.paid_var.set(""); self.note_var.set("")
            self.info_var.set("กรุณาเลือกตั๋วขายฝาก"); self.total_var.set("ยอดไถ่โดยประมาณ: -")
            self.load_tickets()
            if hasattr(self.parent, "refresh_dashboard"): self.parent.refresh_dashboard()
        except Exception as error:
            messagebox.showerror("ไถ่ถอนไม่ได้", str(error), parent=self)
