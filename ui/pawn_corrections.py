import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from modules.auth import login
from modules.pawn import (
    list_pawns, get_pawn, cancel_pawn, void_latest_renewal, void_redemption,
)
from modules.thai_datetime import format_thai_date, format_thai_datetime
from ui.settings_access import is_admin
from ui.theme import apply_theme, open_fullscreen, back_to_dashboard


STATUS_TEXT = {
    "active": "ใช้งานอยู่",
    "redeemed": "ไถ่ถอนแล้ว",
    "forfeited": "หลุดขายฝาก",
    "cancelled": "ยกเลิกแล้ว",
}


class PawnCorrectionWindow(tk.Toplevel):
    def __init__(self, parent, user=None):
        super().__init__(parent)
        self.parent = parent
        self.user = user or {}
        self.title("แก้ไขรายการผิด - Gold Shop System")
        self.geometry("1120x720")
        self.minsize(950, 620)
        open_fullscreen(self)
        apply_theme(self)
        self.create_widgets()
        self.load_tickets()

    def create_widgets(self):
        head = ttk.Frame(self, padding=12); head.pack(fill="x")
        ttk.Label(head, text="↩ แก้ไขรายการผิด", font=("Arial", 23, "bold")).pack(side="left")
        ttk.Button(head, text="← กลับ Dashboard", command=lambda: back_to_dashboard(self)).pack(side="right")
        ttk.Label(
            self,
            text="ระบบจะไม่ลบข้อมูลเดิม แต่ทำเครื่องหมายยกเลิกและบันทึกผู้ดำเนินการ วันเวลา และเหตุผล",
            font=("Arial", 12), foreground="#8a4b00"
        ).pack(anchor="w", padx=16, pady=(0, 8))

        search = ttk.Frame(self, padding=(12, 4)); search.pack(fill="x")
        self.search_var = tk.StringVar()
        ttk.Entry(search, textvariable=self.search_var, font=("Arial", 15), width=36).pack(side="left", padx=4, ipady=6)
        ttk.Button(search, text="ค้นหา", command=self.load_tickets).pack(side="left", padx=4)
        ttk.Button(search, text="แสดงทั้งหมด", command=lambda: (self.search_var.set(""), self.load_tickets())).pack(side="left", padx=4)

        box = ttk.LabelFrame(self, text="ตั๋วขายฝากทุกสถานะ", padding=8); box.pack(fill="both", expand=True, padx=12, pady=8)
        cols = ("series","ticket", "customer", "status", "loan", "opened", "due")
        self.tree = ttk.Treeview(box, columns=cols, show="headings")
        for key, title, width in (
            ("series","ระบบ",60),("ticket", "เลขที่ตั๋ว", 120), ("customer", "ลูกค้า", 250),
            ("status", "สถานะ", 130), ("loan", "เงินต้น", 130),
            ("opened", "วันที่รับ", 200), ("due", "ครบกำหนด", 170),
        ):
            self.tree.heading(key, text=title); self.tree.column(key, width=width, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.show_selected)

        self.info_var = tk.StringVar(value="กรุณาเลือกตั๋ว")
        ttk.Label(self, textvariable=self.info_var, font=("Arial", 13), justify="left").pack(fill="x", padx=16, pady=5)

        actions = ttk.Frame(self, padding=12); actions.pack(fill="x")
        ttk.Button(actions, text="ยกเลิกตั๋วขายฝาก", command=self.cancel_ticket).pack(side="left", expand=True, fill="x", padx=5, ipady=10)
        ttk.Button(actions, text="ย้อนต่อดอกครั้งล่าสุด", command=self.undo_renew).pack(side="left", expand=True, fill="x", padx=5, ipady=10)
        ttk.Button(actions, text="ย้อนการไถ่ถอน", command=self.undo_redeem).pack(side="left", expand=True, fill="x", padx=5, ipady=10)

    def load_tickets(self):
        self.tree.delete(*self.tree.get_children())
        for p in list_pawns(self.search_var.get(), status=None):
            self.tree.insert("", "end", iid=str(p["id"]), values=(
                p.get("series_code","P"),p["ticket_no"], p["customer_name"], STATUS_TEXT.get(p["status"], p["status"]),
                f'{p["loan_amount"]:,.2f}', format_thai_datetime(p["opened_at"]), format_thai_date(p["due_date"]),
            ))

    def selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("ยังไม่ได้เลือก", "กรุณาเลือกตั๋วขายฝาก", parent=self)
            return None
        return get_pawn(int(selected[0]))

    def show_selected(self, event=None):
        selected = self.tree.selection()
        if not selected: return
        p = get_pawn(int(selected[0]))
        self.info_var.set(
            f"เลขที่ตั๋ว: {p['ticket_no']}   ลูกค้า: {p['first_name']} {p['last_name']}\n"
            f"สถานะ: {STATUS_TEXT.get(p['status'], p['status'])}   เงินต้น: {p['loan_amount']:,.2f} บาท   "
            f"ครบกำหนด: {format_thai_date(p['due_date'])}"
        )

    def authorize(self, action):
        from ui.system_control import ask_approval
        return ask_approval(self,self.user,"cancel_transaction",action,"pawn_ticket")

    def finish(self, ticket_id, message):
        messagebox.showinfo("สำเร็จ", message, parent=self)
        self.load_tickets()
        iid = str(ticket_id)
        if self.tree.exists(iid):
            self.tree.selection_set(iid); self.tree.focus(iid); self.tree.see(iid); self.show_selected()
        if hasattr(self.parent, "refresh_dashboard"): self.parent.refresh_dashboard()

    def cancel_ticket(self):
        p = self.selected()
        if not p: return
        approval = self.authorize("ยกเลิกตั๋วขายฝาก")
        if not approval: return
        reason=approval['reason']
        if not messagebox.askyesno("ยืนยัน", f"ยืนยันยกเลิกตั๋ว {p['ticket_no']}?\nข้อมูลเดิมจะยังอยู่ในประวัติ", parent=self): return
        try:
            result = cancel_pawn(p["id"], reason, self.user.get("id"))
            self.offer_print(result)
            self.finish(p["id"], "ยกเลิกตั๋วขายฝากเรียบร้อย")
        except Exception as error: messagebox.showerror("ยกเลิกไม่ได้", str(error), parent=self)

    def undo_renew(self):
        p = self.selected()
        if not p: return
        approval = self.authorize("ย้อนรายการต่อสัญญาล่าสุด")
        if not approval: return
        reason=approval['reason']
        if not messagebox.askyesno("ยืนยัน", f"ยืนยันย้อนการต่อดอกล่าสุดของ {p['ticket_no']}?", parent=self): return
        try:
            result = void_latest_renewal(p["id"], reason, self.user.get("id"))
            self.offer_print(result)
            self.finish(p["id"], f"ย้อนรายการต่อดอกแล้ว\nวันครบกำหนดกลับเป็น {format_thai_date(result['restored_due_date'])}")
        except Exception as error: messagebox.showerror("ย้อนไม่ได้", str(error), parent=self)

    def undo_redeem(self):
        p = self.selected()
        if not p: return
        approval = self.authorize("ย้อนรายการไถ่ถอน")
        if not approval: return
        reason=approval['reason']
        if not messagebox.askyesno("ยืนยัน", f"ยืนยันเปิดตั๋ว {p['ticket_no']} กลับเป็นใช้งานอยู่?", parent=self): return
        try:
            result = void_redemption(p["id"], reason, self.user.get("id"))
            self.offer_print(result)
            self.finish(p["id"], "ย้อนการไถ่ถอนเรียบร้อย ตั๋วกลับเป็นใช้งานอยู่")
        except Exception as error: messagebox.showerror("ย้อนไม่ได้", str(error), parent=self)

    def offer_print(self, result):
        if messagebox.askyesno("พิมพ์เอกสาร", "ต้องการพิมพ์ใบยกเลิก/แก้ไขรายการหรือไม่?", parent=self):
            from modules.pawn_receipt import print_correction_receipt
            print_correction_receipt(result["ticket_id"], result["transaction_id"])
