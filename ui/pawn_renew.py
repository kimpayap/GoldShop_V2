import tkinter as tk
from tkinter import ttk, messagebox
from modules.pawn import (
    list_pawns_for_renew, get_pawn, list_renewal_options,
    calculate_renewal_interest, calculate_renewal_payment, renew_pawn, get_pawn_renewals,
    get_pawn_display_status,
)
from modules.thai_datetime import format_thai_date, format_thai_datetime
from ui.theme import apply_theme, open_fullscreen, back_to_dashboard
from ui.settings_access import TouchKeypad


STATUS_TEXT = {
    "active": "🟢 ยังไม่ครบกำหนด",
    "due": "🟡 ครบกำหนดวันนี้",
    "overdue": "🔴 เกินกำหนด",
}


class PawnRenewWindow(tk.Toplevel):
    def __init__(self, parent, user=None):
        super().__init__(parent)
        self.parent = parent
        self.user = user or {}
        self.selected_ticket_id = None
        self.selected_months = None
        self.title("ต่อดอก - Gold Shop System")
        self.geometry("1180x760")
        self.minsize(1000, 680)
        open_fullscreen(self)
        self.create_style()
        apply_theme(self)
        self.create_widgets()
        self.load_tickets()

    def create_style(self):
        st = ttk.Style(self)
        try: st.theme_use("clam")
        except Exception: pass
        st.configure("Renew.TButton", font=("Arial", 14, "bold"), padding=(14, 11))
        st.configure("RenewPrimary.TButton", font=("Arial", 16, "bold"), padding=(18, 13))
        st.configure("Treeview", font=("Arial", 12), rowheight=34)
        st.configure("Treeview.Heading", font=("Arial", 12, "bold"))

    def create_widgets(self):
        head = ttk.Frame(self, padding=12); head.pack(fill="x")
        ttk.Label(head, text="🔄 ต่อดอก", font=("Arial", 24, "bold")).pack(side="left")
        ttk.Button(head, text="← กลับ Dashboard", style="Renew.TButton", command=lambda: back_to_dashboard(self)).pack(side="right")

        search = ttk.LabelFrame(self, text="1. ค้นหาตั๋วขายฝาก", padding=10); search.pack(fill="x", padx=12, pady=6)
        self.search_var = tk.StringVar()
        ttk.Entry(search, textvariable=self.search_var, font=("Arial", 15), width=35).pack(side="left", padx=5, ipady=7)
        ttk.Button(search, text="🔎 ค้นหา", style="Renew.TButton", command=self.load_tickets).pack(side="left", padx=5)
        ttk.Button(search, text="ทั้งหมด", style="Renew.TButton", command=self.show_all).pack(side="left", padx=5)
        ttk.Label(search, text="ค้นหาได้จากเลขตั๋ว / รหัสลูกค้า / ชื่อ / เลขบัตร", font=("Arial", 11)).pack(side="left", padx=14)

        upper = ttk.Frame(self); upper.pack(fill="both", expand=True, padx=12)
        left = ttk.LabelFrame(upper, text="ตั๋วที่ยังไม่ปิด", padding=8); left.pack(side="left", fill="both", expand=True, padx=(0,6))
        cols=("series","ticket","customer","loan","status","due")
        self.tree=ttk.Treeview(left,columns=cols,show="headings",height=11)
        for c,h,w in [("series","ระบบ",60),("ticket","เลขที่ตั๋ว",105),("customer","ลูกค้า",220),("loan","เงินต้น",110),("status","สถานะ",145),("due","ครบกำหนด",115)]:
            self.tree.heading(c,text=h); self.tree.column(c,width=w,anchor="center")
        self.tree.pack(fill="both",expand=True)
        self.tree.bind("<<TreeviewSelect>>",self.select_ticket)

        right=ttk.LabelFrame(upper,text="2. ข้อมูลต่อดอก",padding=12); right.pack(side="left",fill="both",expand=True,padx=(6,0))
        self.info_var=tk.StringVar(value="กรุณาเลือกตั๋วขายฝาก")
        ttk.Label(right,textvariable=self.info_var,font=("Arial",13),justify="left").pack(anchor="w",fill="x")

        ttk.Separator(right).pack(fill="x",pady=10)
        ttk.Label(right,text="เลือกระยะเวลาต่อดอก",font=("Arial",15,"bold")).pack(anchor="w")
        self.month_frame=ttk.Frame(right); self.month_frame.pack(fill="x",pady=6)
        self.load_month_buttons()

        custom_months=ttk.Frame(right);custom_months.pack(fill="x",pady=(0,6))
        ttk.Label(custom_months,text="จำนวนเดือนอื่น",font=("Arial",13,"bold")).pack(side="left")
        self.custom_months_var=tk.StringVar()
        self.custom_months_entry=ttk.Entry(custom_months,textvariable=self.custom_months_var,font=("Arial",16),width=8,justify="center")
        self.custom_months_entry.pack(side="left",padx=7,ipady=6)
        ttk.Button(custom_months,text="⌨ ระบุเดือน",style="Renew.TButton",command=self.open_month_keypad).pack(side="left",padx=3)
        ttk.Button(custom_months,text="✓ ใช้จำนวนนี้",style="Renew.TButton",command=self.use_custom_months).pack(side="left",padx=3)

        self.calc_var=tk.StringVar(value="ยังไม่ได้เลือกระยะเวลา")
        ttk.Label(right,textvariable=self.calc_var,font=("Arial",14,"bold"),justify="left").pack(anchor="w",pady=8)

        pay=ttk.Frame(right); pay.pack(fill="x",pady=5)
        ttk.Label(pay,text="ยอดรับจริง",font=("Arial",14,"bold")).pack(side="left")
        self.paid_var=tk.StringVar()
        self.paid_entry=ttk.Entry(pay,textvariable=self.paid_var,font=("Arial",16),width=14)
        self.paid_entry.pack(side="left",padx=7,ipady=7)
        ttk.Button(pay,text="💰 ระบุยอด",style="Renew.TButton",command=self.open_keypad).pack(side="left")

        ttk.Label(right,text="หมายเหตุ",font=("Arial",13,"bold")).pack(anchor="w",pady=(8,2))
        self.note=tk.Entry(right,font=("Arial",14)); self.note.pack(fill="x",ipady=6)
        ttk.Button(right,text="✅ ยืนยันต่อดอก",style="RenewPrimary.TButton",command=self.confirm_renew).pack(fill="x",pady=12)

        history=ttk.LabelFrame(self,text="ประวัติการต่อดอกของตั๋วที่เลือก",padding=8); history.pack(fill="x",padx=12,pady=(4,12))
        self.history=ttk.Treeview(history,columns=("at","months","interest","paid","old","new","status"),show="headings",height=4)
        for c,h,w in [("at","วันที่",150),("months","เดือน",80),("interest","ดอกคำนวณ",110),("paid","รับจริง",110),("old","ครบกำหนดเดิม",120),("new","ครบกำหนดใหม่",120),("status","สถานะ",90)]:
            self.history.heading(c,text=h);self.history.column(c,width=w,anchor="center")
        self.history.pack(fill="x")

    def load_month_buttons(self):
        for w in self.month_frame.winfo_children(): w.destroy()
        options=list_renewal_options(True)
        for i,opt in enumerate(options):
            ttk.Button(self.month_frame,text=opt["label"],style="Renew.TButton",
                       command=lambda m=opt["months"]:self.choose_months(m)).grid(row=i//4,column=i%4,padx=4,pady=4,sticky="ew")
        for c in range(4): self.month_frame.columnconfigure(c,weight=1)

    def show_all(self):
        self.search_var.set(""); self.load_tickets()

    def load_tickets(self):
        for x in self.tree.get_children(): self.tree.delete(x)
        for p in list_pawns_for_renew(self.search_var.get().strip()):
            self.tree.insert("","end",iid=str(p["id"]),values=(
                p.get("series_code","P"),p["ticket_no"],p["customer_name"],f'{p["loan_amount"]:,.2f}',
                STATUS_TEXT.get(p["display_status"],p["display_status"]),format_thai_date(p["due_date"])
            ))

    def select_ticket(self,event=None):
        sel=self.tree.selection()
        if not sel:return
        self.selected_ticket_id=int(sel[0]); self.selected_months=None
        pawn=get_pawn(self.selected_ticket_id)
        status=get_pawn_display_status(pawn)
        self.info_var.set(
            f"เลขที่ตั๋ว: {pawn['ticket_no']}\nลูกค้า: {pawn['first_name']} {pawn['last_name']}\n"
            f"เงินต้น: {pawn['loan_amount']:,.2f} บาท\nผลตอบแทน: {pawn['monthly_interest_rate']:.2f}% / เดือน\n"
            f"ครบกำหนดเดิม: {format_thai_date(pawn['due_date'])}\nสถานะ: {STATUS_TEXT.get(status,status)}"
        )
        self.calc_var.set("กรุณาเลือกระยะเวลาต่อดอก"); self.paid_var.set("")
        self.custom_months_var.set("")
        self.load_history()

    def choose_months(self,months):
        if not self.selected_ticket_id:
            messagebox.showwarning("ต่อดอก","กรุณาเลือกตั๋วขายฝากก่อน",parent=self);return
        self.selected_months=int(months)
        pawn=get_pawn(self.selected_ticket_id)
        payment=calculate_renewal_payment(self.selected_ticket_id, months)
        interest=payment["interest_amount"]
        from modules.pawn import _add_months
        new_due=_add_months(pawn["due_date"],months).isoformat()
        self.paid_var.set(f"{payment['total']:.2f}")
        vat_text = (f"\nฐานภาษี: {payment['vat_base']:,.2f} บาท"
                    f"\nVAT {payment['vat_rate']:.0f}% (ถอดจากผลตอบแทน): {payment['vat_amount']:,.2f} บาท"
                    f"\nผลตอบแทนรวม VAT: {payment['total']:,.2f} บาท") if payment["series_code"] == "Q" else ""
        self.calc_var.set(
            f"ต่อดอก {months} เดือน\nผลตอบแทนที่คำนวณ: {interest:,.2f} บาท\n"
            f"{vat_text}\n"
            f"ครบกำหนดใหม่: {format_thai_date(new_due)} (นับต่อจากวันครบกำหนดเดิม)"
        )

    def open_month_keypad(self):
        keypad=TouchKeypad(self,self.custom_months_var,"จำนวนเดือนต่อดอก");self.wait_window(keypad)

    def use_custom_months(self):
        try:
            text=self.custom_months_var.get().strip()
            months=int(text)
            if str(months)!=text or months<=0 or months>120:
                raise ValueError
        except Exception:
            messagebox.showwarning("จำนวนเดือนไม่ถูกต้อง","กรุณากรอกจำนวนเดือนเป็นเลขจำนวนเต็ม 1–120",parent=self);return
        self.choose_months(months)

    def open_keypad(self):
        keypad=TouchKeypad(self,self.paid_var,"ยอดรับจริง");self.wait_window(keypad)

    def confirm_renew(self):
        if not self.selected_ticket_id or not self.selected_months:
            messagebox.showwarning("ต่อดอก","กรุณาเลือกตั๋วและระยะเวลาต่อดอก",parent=self);return
        try: paid=float(self.paid_var.get())
        except Exception:
            messagebox.showwarning("ต่อดอก","ยอดรับจริงไม่ถูกต้อง",parent=self);return
        pawn=get_pawn(self.selected_ticket_id)
        payment=calculate_renewal_payment(self.selected_ticket_id, self.selected_months)
        expected=payment["interest_amount"]
        vat_confirm = (f"ฐานภาษี {payment['vat_base']:,.2f} บาท\n"
                       f"VAT ที่ถอดออก {payment['vat_amount']:,.2f} บาท\n"
                       f"ผลตอบแทนรวม VAT {payment['total']:,.2f} บาท\n") if payment["series_code"] == "Q" else ""
        if not messagebox.askyesno(
            "ยืนยันต่อดอก",
            f"ตั๋ว {pawn['ticket_no']}\nต่อ {self.selected_months} เดือน\n"
            f"ผลตอบแทนคำนวณ {expected:,.2f} บาท\n{vat_confirm}"
            f"ยอดรับจริง {paid:,.2f} บาท\n\nยืนยันการต่อดอก?",
            parent=self
        ): return
        try:
            result=renew_pawn(
                self.selected_ticket_id,paid,note=self.note.get().strip(),
                created_by=self.user.get("id"),renew_months=self.selected_months
            )
            messagebox.showinfo("สำเร็จ",f"ต่อดอกเรียบร้อย\nครบกำหนดใหม่: {format_thai_date(result['new_due_date'])}",parent=self)
            if messagebox.askyesno("พิมพ์ใบรับเงิน", "ต้องการพิมพ์ใบรับเงินต่อดอกหรือไม่?", parent=self):
                from modules.pawn_receipt import print_renewal_receipt
                print_renewal_receipt(self.selected_ticket_id, result["renewal_id"])
            # โหลดข้อมูลใหม่และเลือกตั๋วเดิมซ้ำ เพื่อไม่ให้รายละเอียดเก่าค้างบนหน้าจอ
            ticket_iid=str(self.selected_ticket_id)
            self.load_tickets()
            if self.tree.exists(ticket_iid):
                self.tree.selection_set(ticket_iid)
                self.tree.focus(ticket_iid)
                self.tree.see(ticket_iid)
                self.select_ticket()
            else:
                self.load_history()
            if hasattr(self.parent,"refresh_dashboard"):self.parent.refresh_dashboard()
        except Exception as e: messagebox.showerror("ต่อดอกไม่ได้",str(e),parent=self)

    def load_history(self):
        for x in self.history.get_children():self.history.delete(x)
        if not self.selected_ticket_id:return
        for r in get_pawn_renewals(self.selected_ticket_id):
            status = "ยกเลิกแล้ว" if r.get("renewal_status") == "voided" else "สำเร็จ"
            self.history.insert("","end",values=(format_thai_datetime(r["renewed_at"]),r["renew_months"],f'{r["interest_amount"]:,.2f}',f'{r["paid_amount"]:,.2f}',format_thai_date(r["previous_due_date"]),format_thai_date(r["new_due_date"]),status))
