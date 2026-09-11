
import tkinter as tk
from tkinter import ttk, messagebox
from database.database import get_connection


class Dashboard(tk.Tk):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.title("Gold Shop System V2 - Dashboard")
        self.geometry("1050x700")
        self.create_widgets()
        self.refresh_dashboard()

    def create_widgets(self):
        header = ttk.Frame(self, padding=20)
        header.pack(fill="x")
        ttk.Label(
            header, text="GOLD SHOP SYSTEM V2",
            font=("Arial", 26, "bold")
        ).pack(side="left")
        ttk.Label(
            header,
            text=f"ผู้ใช้: {self.user['full_name']} ({self.user['role']})"
        ).pack(side="right")
        ttk.Separator(self).pack(fill="x")

        cards = ttk.Frame(self, padding=20)
        cards.pack(fill="x")

        self.customer_count = tk.StringVar(value="0")
        self.pawn_count = tk.StringVar(value="0")
        self.pawn_total = tk.StringVar(value="0.00")
        self.gold_buy = tk.StringVar(value="-")
        self.gold_sell = tk.StringVar(value="-")

        card_data = [
            ("ลูกค้าทั้งหมด", self.customer_count),
            ("ตั๋วขายฝากคงค้าง", self.pawn_count),
            ("เงินต้นคงค้าง", self.pawn_total),
            ("ทองแท่งรับซื้อ", self.gold_buy),
            ("ทองแท่งขายออก", self.gold_sell),
        ]
        for i, (title, var) in enumerate(card_data):
            box = ttk.LabelFrame(cards, text=title, padding=18)
            box.grid(row=0, column=i, padx=6, sticky="nsew")
            ttk.Label(box, textvariable=var, font=("Arial", 20, "bold")).pack()
            cards.columnconfigure(i, weight=1)

        menu = ttk.LabelFrame(self, text="เมนูระบบ", padding=25)
        menu.pack(fill="both", expand=True, padx=20, pady=10)

        buttons = [
            ("👤 ลูกค้า", self.open_customers),
            ("📋 รับขายฝาก", self.open_pawn),
            ("💰 ไถ่ถอน", self.open_pawn),
            ("🔄 ต่อดอก", self.open_pawn),
            ("🛒 ขายทอง", self.not_ready),
            ("📦 สต็อก", self.not_ready),
            ("📊 รายงาน", self.not_ready),
            ("⚙ ตั้งค่า", self.not_ready),
        ]
        for index, (text, command) in enumerate(buttons):
            row, col = divmod(index, 4)
            ttk.Button(
                menu, text=text, command=command
            ).grid(
                row=row, column=col, padx=10, pady=15,
                ipadx=25, ipady=18, sticky="nsew"
            )
        for i in range(4):
            menu.columnconfigure(i, weight=1)

    def refresh_dashboard(self):
        with get_connection() as conn:
            customers = conn.execute(
                "SELECT COUNT(*) FROM customers"
            ).fetchone()[0]

            pawn_count = 0
            pawn_total = 0.0
            try:
                pawn_count = conn.execute(
                    "SELECT COUNT(*) FROM pawn_tickets WHERE status='active'"
                ).fetchone()[0]
                pawn_total = conn.execute(
                    "SELECT COALESCE(SUM(loan_amount),0) FROM pawn_tickets WHERE status='active'"
                ).fetchone()[0]
            except Exception:
                pass

            gold = None
            try:
                gold = conn.execute(
                    "SELECT gold_bar_buy, gold_bar_sell FROM gold_prices ORDER BY id DESC LIMIT 1"
                ).fetchone()
            except Exception:
                pass

        self.customer_count.set(str(customers))
        self.pawn_count.set(str(pawn_count))
        self.pawn_total.set(f"{float(pawn_total):,.2f}")
        if gold:
            self.gold_buy.set(f"{float(gold['gold_bar_buy'] or 0):,.2f}")
            self.gold_sell.set(f"{float(gold['gold_bar_sell'] or 0):,.2f}")
        else:
            self.gold_buy.set("-")
            self.gold_sell.set("-")

    def open_customers(self):
        from ui.customers import CustomerWindow
        CustomerWindow(self)

    def open_pawn(self):
        from ui.pawn import PawnWindow
        PawnWindow(self, self.user)

    def not_ready(self):
        messagebox.showinfo(
            "Gold Shop System",
            "ฟังก์ชันนี้จะเปิดใช้งานในขั้นตอนถัดไป"
        )
