import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime,date,timedelta

from database.database import get_connection
from modules.gold_price import update_gold_price, get_latest_gold_price
from modules.thai_datetime import format_thai_date,format_thai_datetime
from ui.theme import apply_theme, open_fullscreen


class Dashboard(tk.Tk):

    REFRESH_INTERVAL = 5 * 60 * 1000  # 5 นาที

    def __init__(self, user):

        super().__init__()

        self.user = user

        self.title(
            "Gold Shop System V1"
        )

        self.geometry(
            "1200x700"
        )

        self.minsize(
            1000,
            650
        )

        open_fullscreen(self)

        self.configure(
            bg="#f5f5f5"
        )

        self.create_style()

        apply_theme(self)

        self.create_widgets()

        self.refresh_dashboard()

        self.after(2000,self.run_daily_backup)

        # เริ่ม Auto Refresh
        self.after(
            self.REFRESH_INTERVAL,
            self.auto_refresh_gold
        )

    # =====================================
    # Style
    # =====================================

    def create_style(self):

        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except:
            pass

        style.configure(
            "Title.TLabel",
            font=("Arial", 24, "bold")
        )

        style.configure(
            "Menu.TButton",
            font=("Arial", 13),
            padding=12
        )

        style.configure(
            "Card.TLabelframe",
            padding=10
        )

        style.configure(
            "CardValue.TLabel",
            font=("Arial", 22, "bold")
        )

        style.configure(
            "Gold.TLabelframe",
            padding=15
        )

    # =====================================
    # สร้างหน้าจอ
    # =====================================

    def create_widgets(self):

        self.create_widgets_v2()
        return

        # =================================
        # Header
        # =================================

        header = ttk.Frame(
            self,
            padding=(20, 15)
        )

        header.pack(
            fill="x"
        )

        ttk.Label(
            header,
            text="🟡 GOLD SHOP SYSTEM",
            style="Title.TLabel"
        ).pack(
            side="left"
        )

        user_text = (
            f"ผู้ใช้: {self.user['full_name']} "
            f" | สิทธิ์: {self.user['role']}"
        )

        ttk.Label(
            header,
            text=user_text,
            font=("Arial", 11)
        ).pack(
            side="right"
        )

        ttk.Separator(
            self
        ).pack(
            fill="x"
        )

        try:
            with get_connection() as conn:
                mode_row=conn.execute("SELECT setting_value FROM app_settings WHERE setting_key='database_mode'").fetchone()
            if mode_row and mode_row["setting_value"]=="demo":
                demo=tk.Label(self,text="⚠ โหมดทดลอง — ข้อมูลทั้งหมดเป็นข้อมูลจำลอง ห้ามใช้ทำรายการจริง",bg="#b91c1c",fg="white",font=("Arial",15,"bold"),pady=7)
                demo.pack(fill="x")
        except Exception:pass

        # =================================
        # Main
        # =================================

        main = ttk.Frame(
            self
        )

        main.pack(
            fill="both",
            expand=True
        )

        # =================================
        # Sidebar
        # =================================

        sidebar = ttk.LabelFrame(
            main,
            text="เมนูระบบ",
            padding=12
        )

        sidebar.pack(
            side="left",
            fill="y",
            padx=(15, 8),
            pady=15
        )

        # เมนูเลื่อนได้เสมอ เมื่อความสูงจอไม่พอจะไม่มีปุ่มตกออกนอกหน้าจอ
        sidebar_canvas = tk.Canvas(sidebar, highlightthickness=0, borderwidth=0, width=210)
        sidebar_scroll = ttk.Scrollbar(sidebar, orient="vertical", command=sidebar_canvas.yview)
        menu_inner = ttk.Frame(sidebar_canvas)
        menu_window = sidebar_canvas.create_window((0, 0), window=menu_inner, anchor="nw")
        menu_inner.bind("<Configure>", lambda _e: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all")))
        sidebar_canvas.bind("<Configure>", lambda e: sidebar_canvas.itemconfigure(menu_window, width=e.width))
        sidebar_canvas.configure(yscrollcommand=sidebar_scroll.set)
        sidebar_canvas.pack(side="left", fill="both", expand=True)
        sidebar_scroll.pack(side="right", fill="y")
        sidebar_canvas.bind("<Enter>", lambda _e: sidebar_canvas.bind_all("<MouseWheel>", lambda e: sidebar_canvas.yview_scroll(-1 if e.delta>0 else 1, "units")))
        sidebar_canvas.bind("<Leave>", lambda _e: sidebar_canvas.unbind_all("<MouseWheel>"))

        buttons = [

            ("🏠 หน้าหลัก", self.refresh_dashboard),

            ("👤 ลูกค้า", self.open_customers),

            ("🏢 คู่ค้า", self.open_suppliers),

            ("📋 รับขายฝาก", self.open_pawn),

            ("💰 ไถ่ถอน", self.open_pawn_redeem),

            ("🔄 ต่อดอก", self.open_pawn_renew),

            ("⚫ ตั๋วหลุดขายฝาก", self.open_pawn_forfeit),

            ("↩ แก้รายการผิด", self.open_pawn_corrections),

            ("🛒 ขายทอง", self.open_gold_sale),

            ("🔄 แลกทองเก่าเป็นทองใหม่", self.open_gold_exchange),

            ("🧾 ประวัติการขาย", self.open_sale_history),

            ("📦 รับทองใหม่", self.open_stock_receive),

            ("♻ รับซื้อทองเก่า", self.open_old_gold_buyback),

            ("🧰 สต็อกทองเก่า", self.open_old_gold_stock),

            ("🛡 ศูนย์บริหาร", self.open_operations_center),

            ("📊 รายงาน", self.open_reports),

            ("⚙ ตั้งค่า", self.open_pawn_settings),

        ]

        for text, command in buttons:

            ttk.Button(
                menu_inner,
                text=text,
                command=command,
                style="Menu.TButton",
                width=18
            ).pack(
                fill="x",
                pady=4
            )

        ttk.Separator(
            menu_inner
        ).pack(
            fill="x",
            pady=10
        )

        ttk.Button(
            menu_inner,
            text="🚪 ออกจากระบบ",
            command=self.logout,
            style="Menu.TButton",
            width=18
        ).pack(
            fill="x",
            pady=4
        )

        # =================================
        # Content
        # =================================

        content = ttk.Frame(
            main,
            padding=10
        )

        content.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(5, 15),
            pady=15
        )

        # =================================
        # ราคาทอง
        # =================================

        gold_frame = ttk.LabelFrame(
            content,
            text="🟡 ราคาทองคำวันนี้",
            style="Gold.TLabelframe"
        )

        gold_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        # -------------------------------
        # ทองแท่ง
        # -------------------------------

        bar_frame = ttk.LabelFrame(
            gold_frame,
            text="ทองคำแท่ง 96.5%",
            padding=15
        )

        bar_frame.grid(
            row=0,
            column=0,
            padx=8,
            pady=8,
            sticky="nsew"
        )

        ttk.Label(
            bar_frame,
            text="รับซื้อ",
            font=("Arial", 12)
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.gold_bar_buy = tk.StringVar(
            value="-"
        )

        ttk.Label(
            bar_frame,
            textvariable=self.gold_bar_buy,
            font=("Arial", 24, "bold")
        ).grid(
            row=1,
            column=0,
            pady=(2, 10)
        )

        ttk.Label(
            bar_frame,
            text="ขายออก",
            font=("Arial", 12)
        ).grid(
            row=2,
            column=0,
            sticky="w"
        )

        self.gold_bar_sell = tk.StringVar(
            value="-"
        )

        ttk.Label(
            bar_frame,
            textvariable=self.gold_bar_sell,
            font=("Arial", 24, "bold")
        ).grid(
            row=3,
            column=0
        )

        # -------------------------------
        # ทองรูปพรรณ
        # -------------------------------

        jewelry_frame = ttk.LabelFrame(
            gold_frame,
            text="ทองรูปพรรณ 96.5%",
            padding=15
        )

        jewelry_frame.grid(
            row=0,
            column=1,
            padx=8,
            pady=8,
            sticky="nsew"
        )

        ttk.Label(
            jewelry_frame,
            text="รับซื้อ",
            font=("Arial", 12)
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.gold_jewelry_buy = tk.StringVar(
            value="-"
        )

        ttk.Label(
            jewelry_frame,
            textvariable=self.gold_jewelry_buy,
            font=("Arial", 24, "bold")
        ).grid(
            row=1,
            column=0,
            pady=(2, 10)
        )

        ttk.Label(
            jewelry_frame,
            text="ขายออก",
            font=("Arial", 12)
        ).grid(
            row=2,
            column=0,
            sticky="w"
        )

        self.gold_jewelry_sell = tk.StringVar(
            value="-"
        )

        ttk.Label(
            jewelry_frame,
            textvariable=self.gold_jewelry_sell,
            font=("Arial", 24, "bold")
        ).grid(
            row=3,
            column=0
        )

        gold_frame.columnconfigure(
            0,
            weight=1
        )

        gold_frame.columnconfigure(
            1,
            weight=1
        )

        # =================================
        # ข้อมูลการประกาศ
        # =================================

        info_frame = ttk.Frame(
            gold_frame
        )

        info_frame.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(5, 0)
        )

        self.gold_info = tk.StringVar(
            value="ยังไม่มีข้อมูลราคาทอง"
        )

        ttk.Label(
            info_frame,
            textvariable=self.gold_info,
            font=("Arial", 11)
        ).pack(
            side="left"
        )

        ttk.Button(
            info_frame,
            text="🔄 อัปเดตทันที",
            command=self.manual_refresh_gold
        ).pack(
            side="right"
        )

        # =================================
        # Status
        # =================================

        self.gold_status = tk.StringVar(
            value="กำลังโหลด..."
        )

        ttk.Label(
            content,
            textvariable=self.gold_status,
            font=("Arial", 10)
        ).pack(
            anchor="w",
            pady=(0, 10)
        )

        # =================================
        # Cards
        # =================================

        cards = ttk.Frame(
            content
        )

        cards.pack(
            fill="x",
            pady=5
        )

        self.customer_count = tk.StringVar(
            value="0"
        )

        self.pawn_count = tk.StringVar(
            value="0"
        )

        self.sales_count = tk.StringVar(
            value="0"
        )

        self.loan_amount = tk.StringVar(
            value="0.00 บาท"
        )

        self.create_card(
            cards,
            "👤 ลูกค้าทั้งหมด",
            self.customer_count,
            0
        )

        self.create_card(
            cards,
            "📋 ใบขายฝาก",
            self.pawn_count,
            1
        )

        self.create_card(
            cards,
            "🛒 รายการขาย",
            self.sales_count,
            2
        )

        self.create_card(
            cards,
            "💰 เงินต้นขายฝาก",
            self.loan_amount,
            3
        )

        for i in range(4):

            cards.columnconfigure(
                i,
                weight=1
            )

        # =================================
        # ข้อมูลระบบ
        # =================================

        system_frame = ttk.LabelFrame(
            content,
            text="สถานะระบบ",
            padding=15
        )

        system_frame.pack(
            fill="both",
            expand=True,
            pady=(10, 0)
        )

        ttk.Label(
            system_frame,
            text="ระบบจัดการร้านทองและรับขายฝาก",
            font=("Arial", 16, "bold")
        ).pack(
            anchor="w"
        )

        ttk.Label(
            system_frame,
            text=(
                "ราคาทองจะอัปเดตอัตโนมัติทุก 5 นาที\n"
                "ก่อนทำรายการรับขายฝาก ระบบจะตรวจสอบราคาล่าสุดอีกครั้ง"
            ),
            font=("Arial", 11)
        ).pack(
            anchor="w",
            pady=10
        )

    def create_widgets_v2(self):
        header=ttk.Frame(self,padding=(16,10));header.pack(fill="x")
        ttk.Label(header,text="🟡 GOLD SHOP SYSTEM",style="Title.TLabel").pack(side="left")
        self.clock_text=tk.StringVar();ttk.Label(header,textvariable=self.clock_text,font=("Arial",13,"bold")).pack(side="left",padx=35)
        ttk.Label(header,text=f"ผู้ใช้: {self.user['full_name']} | สิทธิ์: {self.user['role']}",font=("Arial",11)).pack(side="right")
        self.update_clock();ttk.Separator(self).pack(fill="x")
        try:
            with get_connection() as conn:mode=conn.execute("SELECT setting_value FROM app_settings WHERE setting_key='database_mode'").fetchone()
            if mode and mode[0]=="demo":tk.Label(self,text="⚠ โหมดทดลอง — ข้อมูลทั้งหมดเป็นข้อมูลจำลอง",bg="#b91c1c",fg="white",font=("Arial",14,"bold"),pady=5).pack(fill="x")
        except Exception:pass
        main=ttk.Panedwindow(self,orient="horizontal");main.pack(fill="both",expand=True,padx=8,pady=8)
        sidebar=ttk.Frame(main,width=270);content_host=ttk.Frame(main);main.add(sidebar,weight=0);main.add(content_host,weight=1)
        ttk.Label(sidebar,text="เมนูระบบ",font=("Arial",16,"bold"),padding=6).pack(fill="x")
        menu_canvas=tk.Canvas(sidebar,highlightthickness=0,width=255);menu_scroll=ttk.Scrollbar(sidebar,orient="vertical",command=menu_canvas.yview);menu=ttk.Frame(menu_canvas);window=menu_canvas.create_window((0,0),window=menu,anchor="nw");menu.bind("<Configure>",lambda _e:menu_canvas.configure(scrollregion=menu_canvas.bbox("all")));menu_canvas.bind("<Configure>",lambda e:menu_canvas.itemconfigure(window,width=e.width));menu_canvas.configure(yscrollcommand=menu_scroll.set);menu_canvas.pack(side="left",fill="both",expand=True);menu_scroll.pack(side="right",fill="y")
        groups=[
            ("🧾 ขายฝาก",[("รับขายฝาก",self.open_pawn),("ต่อสัญญา",self.open_pawn_renew),("ไถ่ถอน",self.open_pawn_redeem),("ตั๋วหลุดขายฝาก",self.open_pawn_forfeit),("แก้รายการผิด",self.open_pawn_corrections)]),
            ("🛒 ขายและแลกทอง",[("ขายทองใหม่",self.open_gold_sale),("แลกทองเก่าเป็นทองใหม่",self.open_gold_exchange),("ประวัติการขาย",self.open_sale_history)]),
            ("📦 สต็อกสินค้า",[("รับทองใหม่",self.open_stock_receive),("รับซื้อทองเก่า",self.open_old_gold_buyback),("สต็อกทองเก่า/ล็อต",self.open_old_gold_stock),("ตรวจนับ/ศูนย์บริหาร",self.open_operations_center)]),
            ("👥 ข้อมูลบุคคล",[("ลูกค้า",self.open_customers),("คู่ค้า/โรงหลอม",self.open_suppliers)]),
            ("📊 รายงานและการเงิน",[("ศูนย์รายงาน",self.open_reports),("ศูนย์บริหาร",self.open_operations_center)]),
            ("⚙ จัดการระบบ",[("สำรอง/สิทธิ์/ปิดกะ",self.open_system_control),("ตั้งค่าระบบ",self.open_pawn_settings)]),
        ]
        self.menu_panels={}
        for index,(title,items) in enumerate(groups):self.create_menu_group(menu,title,items,index==0)
        ttk.Separator(menu).pack(fill="x",pady=8);ttk.Button(menu,text="🚪 ออกจากระบบ",command=self.logout,style="Menu.TButton").pack(fill="x",pady=3)
        canvas=tk.Canvas(content_host,highlightthickness=0);scroll=ttk.Scrollbar(content_host,orient="vertical",command=canvas.yview);content=ttk.Frame(canvas,padding=6);cw=canvas.create_window((0,0),window=content,anchor="nw");content.bind("<Configure>",lambda _e:canvas.configure(scrollregion=canvas.bbox("all")));canvas.bind("<Configure>",lambda e:canvas.itemconfigure(cw,width=e.width));canvas.configure(yscrollcommand=scroll.set);canvas.pack(side="left",fill="both",expand=True);scroll.pack(side="right",fill="y")
        quick=ttk.LabelFrame(content,text="งานด่วน",padding=7);quick.pack(fill="x",pady=(0,6))
        for text,command in (("📋 รับขายฝาก",self.open_pawn),("🔄 ต่อสัญญา",self.open_pawn_renew),("💰 ไถ่ถอน",self.open_pawn_redeem),("🛒 ขายทอง",self.open_gold_sale),("♻ รับซื้อทองเก่า",self.open_old_gold_buyback),("📊 รายงาน",self.open_reports)):ttk.Button(quick,text=text,command=command).pack(side="left",fill="x",expand=True,padx=3)
        search=ttk.Frame(content);search.pack(fill="x",pady=4);self.dashboard_search_text=tk.StringVar();ttk.Label(search,text="ค้นหากลาง/สแกน QR:",font=("Arial",12,"bold")).pack(side="left");entry=ttk.Entry(search,textvariable=self.dashboard_search_text,font=("Arial",14));entry.pack(side="left",fill="x",expand=True,padx=5);entry.bind("<Return>",lambda _e:self.dashboard_search());ttk.Button(search,text="ค้นหา",command=self.dashboard_search).pack(side="left")
        gold=ttk.LabelFrame(content,text="🟡 ราคาทองคำวันนี้",padding=7);gold.pack(fill="x",pady=5);self.gold_bar_buy=tk.StringVar(value="-");self.gold_bar_sell=tk.StringVar(value="-");self.gold_jewelry_buy=tk.StringVar(value="-");self.gold_jewelry_sell=tk.StringVar(value="-");self.gold_info=tk.StringVar(value="ยังไม่มีข้อมูล");self.gold_status=tk.StringVar(value="กำลังโหลด...")
        for col,(label,var) in enumerate((("ทองแท่งรับซื้อ",self.gold_bar_buy),("ทองแท่งขายออก",self.gold_bar_sell),("รูปพรรณรับซื้อ",self.gold_jewelry_buy),("รูปพรรณขายออก",self.gold_jewelry_sell))):box=ttk.Frame(gold,padding=4);box.grid(row=0,column=col,sticky="nsew");ttk.Label(box,text=label).pack();ttk.Label(box,textvariable=var,font=("Arial",16,"bold")).pack();gold.columnconfigure(col,weight=1)
        ttk.Label(gold,textvariable=self.gold_info).grid(row=1,column=0,columnspan=3,sticky="w");ttk.Button(gold,text="อัปเดตราคา",command=self.manual_refresh_gold).grid(row=1,column=3,sticky="e")
        cards=ttk.Frame(content);cards.pack(fill="x",pady=5)
        self.customer_count=tk.StringVar(value="0");self.pawn_count=tk.StringVar(value="0");self.sales_count=tk.StringVar(value="0");self.loan_amount=tk.StringVar(value="0.00 บาท");self.today_pawn=tk.StringVar(value="0");self.today_renew=tk.StringVar(value="0");self.today_redeem=tk.StringVar(value="0");self.today_sales=tk.StringVar(value="0.00");self.today_cash=tk.StringVar(value="0.00")
        card_items=(("ขายฝากวันนี้",self.today_pawn),("ต่อสัญญาวันนี้",self.today_renew),("ไถ่ถอนวันนี้",self.today_redeem),("ยอดขายวันนี้",self.today_sales),("สัญญาคงค้าง",self.pawn_count),("เงินต้นคงค้าง",self.loan_amount),("รายการขายทั้งหมด",self.sales_count),("ลูกค้าทั้งหมด",self.customer_count))
        for i,(title,var) in enumerate(card_items):self.create_card(cards,title,var,i%4,i//4)
        alerts=ttk.LabelFrame(content,text="🔔 แจ้งเตือนและงานค้าง",padding=7);alerts.pack(fill="x",pady=5);self.alert_text=tk.StringVar(value="กำลังตรวจสอบ...");ttk.Label(alerts,textvariable=self.alert_text,font=("Arial",13,"bold"),justify="left").pack(anchor="w")
        recent=ttk.LabelFrame(content,text="ความเคลื่อนไหวล่าสุด",padding=5);recent.pack(fill="both",expand=True,pady=5);self.recent_tree=ttk.Treeview(recent,columns=("time","no","type","party","amount","user","status"),show="headings",height=7)
        for c,t,w in (("time","วันเวลา",165),("no","เลขเอกสาร",130),("type","ประเภท",150),("party","ลูกค้า/คู่ค้า",180),("amount","จำนวนเงิน",120),("user","ผู้ทำรายการ",140),("status","สถานะ",100)):self.recent_tree.heading(c,text=t);self.recent_tree.column(c,width=w,anchor="center")
        self.recent_tree.pack(fill="both",expand=True)

    def create_menu_group(self,parent,title,items,opened=False):
        holder=ttk.Frame(parent);holder.pack(fill="x",pady=2);panel=ttk.Frame(holder);state=tk.BooleanVar(value=opened)
        def toggle():state.set(not state.get());panel.pack(fill="x",padx=(12,0)) if state.get() else panel.pack_forget()
        ttk.Button(holder,text=title,command=toggle,style="Menu.TButton").pack(fill="x")
        for text,command in items:ttk.Button(panel,text="• "+text,command=command).pack(fill="x",pady=1)
        if opened:panel.pack(fill="x",padx=(12,0))

    def update_clock(self):
        if hasattr(self,"clock_text"):self.clock_text.set(format_thai_datetime(datetime.now(),include_seconds=True))
        self.after(1000,self.update_clock)

    def dashboard_search(self):
        text=self.dashboard_search_text.get().strip()
        if not text:return
        try:
            like=f"%{text}%"
            with get_connection() as conn:
                rows=[]
                rows += [("สัญญาขายฝาก",x['ticket_no'],x['name']) for x in conn.execute("SELECT p.ticket_no,c.first_name||' '||c.last_name name FROM pawn_tickets p JOIN customers c ON c.id=p.customer_id WHERE p.ticket_no LIKE ? OR c.first_name||' '||c.last_name LIKE ? OR c.citizen_id LIKE ? LIMIT 10",(like,like,like))]
                rows += [("สินค้าทองใหม่",x['item_code'],x['description']) for x in conn.execute("SELECT item_code,description FROM inventory_items WHERE item_code LIKE ? OR qr_payload LIKE ? OR description LIKE ? LIMIT 10",(like,like,like))]
                rows += [("รายการขาย",x['sale_no'],x['customer_name']) for x in conn.execute("SELECT sale_no,customer_name FROM gold_sales WHERE sale_no LIKE ? OR customer_name LIKE ? LIMIT 10",(like,like))]
            messagebox.showinfo("ผลการค้นหา","\n".join(f"{a}: {b} | {c}" for a,b,c in rows) if rows else "ไม่พบข้อมูล",parent=self)
        except Exception as e:messagebox.showerror("ค้นหาไม่ได้",str(e),parent=self)

    def run_daily_backup(self):
        try:
            from modules.system_controls import automatic_daily_backup
            automatic_daily_backup(self.user)
        except Exception as error:print("Automatic backup error:",error)

    # =====================================
    # สร้าง Card
    # =====================================

    def create_card(
        self,
        parent,
        title,
        variable,
        column,
        row=0
    ):

        frame = ttk.LabelFrame(
            parent,
            text=title,
            padding=10
        )

        frame.grid(
            row=row,
            column=column,
            padx=5,
            pady=4,
            sticky="nsew"
        )
        parent.columnconfigure(column,weight=1)

        ttk.Label(
            frame,
            textvariable=variable,
            style="CardValue.TLabel"
        ).pack()

    # =====================================
    # โหลด Dashboard
    # =====================================

    def refresh_dashboard(self):

        self.refresh_dashboard_v2()
        return

        try:

            with get_connection() as conn:

                customers = conn.execute(
                    "SELECT COUNT(*) FROM customers"
                ).fetchone()[0]

            self.customer_count.set(
                str(customers)
            )

            # V2: จำนวนตั๋วขายฝากที่ยังคงค้าง และเงินต้นคงค้าง
            try:
                pawn_row = conn.execute(
                    "SELECT COUNT(*) AS cnt, COALESCE(SUM(loan_amount), 0) AS total "
                    "FROM pawn_tickets WHERE status = 'active'"
                ).fetchone()
                self.pawn_count.set(str(pawn_row["cnt"]))
                self.loan_amount.set(
                    f"{float(pawn_row['total'] or 0):,.2f} บาท"
                )
            except Exception:
                # รองรับฐานข้อมูลก่อน V2
                self.pawn_count.set("0")
                self.loan_amount.set("0.00 บาท")

            try:
                from modules.sales import ensure_sales_schema
                ensure_sales_schema()
                sale_row = conn.execute("SELECT COUNT(*) AS cnt FROM gold_sales WHERE status='completed'").fetchone()
                self.sales_count.set(str(sale_row["cnt"]))
            except Exception:
                self.sales_count.set("0")

        except Exception as error:

            print(
                "Dashboard error:",
                error
            )

            self.customer_count.set(
                "-"
            )

        self.load_latest_gold_price()

    def refresh_dashboard_v2(self):
        try:
            from modules.operations_control import ensure_operations_schema
            from modules.system_controls import ensure_audit_triggers
            ensure_operations_schema();ensure_audit_triggers();today=date.today().isoformat();soon=(date.today()+timedelta(days=7)).isoformat()
            with get_connection() as conn:
                self.customer_count.set(str(conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]))
                pawn=conn.execute("SELECT COUNT(*) cnt,COALESCE(SUM(loan_amount),0) total FROM pawn_tickets WHERE status='active'").fetchone();self.pawn_count.set(str(pawn['cnt']));self.loan_amount.set(f"{pawn['total']:,.2f} บาท")
                self.sales_count.set(str(conn.execute("SELECT COUNT(*) FROM gold_sales WHERE status='completed'").fetchone()[0]))
                opened=conn.execute("SELECT COUNT(*) cnt,COALESCE(SUM(loan_amount),0) total FROM pawn_tickets WHERE date(opened_at)=? AND status<>'cancelled'",(today,)).fetchone();self.today_pawn.set(f"{opened['cnt']} รายการ\n{opened['total']:,.2f} บาท")
                renew=conn.execute("SELECT COUNT(*) cnt,COALESCE(SUM(amount),0) total FROM pawn_transactions WHERE date(transaction_at)=? AND transaction_type='renew' AND transaction_status='completed'",(today,)).fetchone();self.today_renew.set(f"{renew['cnt']} รายการ\n{renew['total']:,.2f} บาท")
                redeem=conn.execute("SELECT COUNT(*) cnt,COALESCE(SUM(amount),0) total FROM pawn_transactions WHERE date(transaction_at)=? AND transaction_type='redeem' AND transaction_status='completed'",(today,)).fetchone();self.today_redeem.set(f"{redeem['cnt']} รายการ\n{redeem['total']:,.2f} บาท")
                sales=conn.execute("SELECT COUNT(*) cnt,COALESCE(SUM(amount_paid),0) total FROM gold_sales WHERE sale_date=? AND status='completed'",(today,)).fetchone();self.today_sales.set(f"{sales['cnt']} รายการ\n{sales['total']:,.2f} บาท")
                due_today=conn.execute("SELECT COUNT(*) FROM pawn_tickets WHERE status='active' AND due_date=?",(today,)).fetchone()[0];overdue=conn.execute("SELECT COUNT(*) FROM pawn_tickets WHERE status='active' AND due_date<?",(today,)).fetchone()[0];due_soon=conn.execute("SELECT COUNT(*) FROM pawn_tickets WHERE status='active' AND due_date>? AND due_date<=?",(today,soon)).fetchone()[0]
                workflows=conn.execute("SELECT COUNT(*) FROM exchange_workflows WHERE status IN ('draft','pending')").fetchone()[0];batches=conn.execute("SELECT COUNT(*) FROM old_gold_batches WHERE status='sent_to_refinery'").fetchone()[0];counts=conn.execute("SELECT COUNT(*) FROM stock_counts WHERE status='open'").fetchone()[0]
                new_stock=conn.execute("SELECT COUNT(*) cnt,COALESCE(SUM(weight_grams),0) weight FROM inventory_items WHERE status='in_stock'").fetchone();old_stock=conn.execute("SELECT COUNT(*) cnt,COALESCE(SUM(net_weight),0) weight FROM old_gold_items WHERE status='old_gold_stock'").fetchone()
                self.alert_text.set(f"ครบกำหนดวันนี้ {due_today} | ใกล้ครบกำหนด 7 วัน {due_soon} | เกินกำหนด {overdue} | รายการแลกค้าง {workflows}\nล็อตอยู่โรงหลอม {batches} | รอบตรวจนับยังไม่ปิด {counts} | ทองใหม่ {new_stock['cnt']} ชิ้น/{new_stock['weight']:,.3f} กรัม | ทองเก่า {old_stock['cnt']} รายการ/{old_stock['weight']:,.3f} กรัม")
                recent=[]
                for x in conn.execute("""SELECT p.opened_at tm,p.ticket_no no,'รับขายฝาก' kind,c.first_name||' '||c.last_name party,p.loan_amount amount,u.full_name username,p.status status FROM pawn_tickets p JOIN customers c ON c.id=p.customer_id LEFT JOIN users u ON u.id=p.created_by ORDER BY p.opened_at DESC LIMIT 6"""):recent.append(dict(x))
                for x in conn.execute("""SELECT s.created_at tm,s.sale_no no,'ขายทองใหม่' kind,s.customer_name party,s.amount_paid amount,u.full_name username,s.status status FROM gold_sales s LEFT JOIN users u ON u.id=s.created_by ORDER BY s.created_at DESC LIMIT 6"""):recent.append(dict(x))
                for x in conn.execute("""SELECT r.created_at tm,r.receipt_no no,'รับซื้อทองเก่า' kind,COALESCE(c.first_name||' '||c.last_name,'ตั๋วหลุด') party,r.paid_amount amount,u.full_name username,r.status status FROM old_gold_receipts r LEFT JOIN customers c ON c.id=r.customer_id LEFT JOIN users u ON u.id=r.created_by ORDER BY r.created_at DESC LIMIT 6"""):recent.append(dict(x))
            recent.sort(key=lambda x:x['tm'] or '',reverse=True);self.recent_tree.delete(*self.recent_tree.get_children())
            for x in recent[:12]:self.recent_tree.insert("","end",values=(format_thai_datetime(x['tm']),x['no'],x['kind'],x['party'] or '-',f"{float(x['amount'] or 0):,.2f}",x['username'] or '-',x['status']))
        except Exception as error:
            print("Dashboard error:",error)
            if hasattr(self,"alert_text"):self.alert_text.set(f"ไม่สามารถโหลดข้อมูลสรุปได้: {error}")
        self.load_latest_gold_price()

    # =====================================
    # โหลดราคาทองล่าสุดจาก SQLite
    # =====================================

    def load_latest_gold_price(self):

        data = get_latest_gold_price()

        if not data:

            self.gold_status.set(
                "🟠 ยังไม่มีข้อมูลราคาทอง"
            )

            return

        self.gold_bar_buy.set(
            self.format_money(
                data["gold_bar_buy"]
            )
        )

        self.gold_bar_sell.set(
            self.format_money(
                data["gold_bar_sell"]
            )
        )

        self.gold_jewelry_buy.set(
            self.format_money(
                data["gold_jewelry_tax"]
            )
        )

        self.gold_jewelry_sell.set(
            self.format_money(
                data["gold_jewelry_sell"]
            )
        )

        self.gold_info.set(
            f"วันที่ {format_thai_date(data['price_date'])}  "
            f"เวลา {data['price_time']} น.  "
            f"ครั้งที่ {data['announcement_no']}"
        )

        self.gold_status.set(
            "🟢 ราคาทองล่าสุดจากฐานข้อมูล"
        )

    # =====================================
    # Format เงิน
    # =====================================

    def format_money(self, value):

        if value is None:
            return "-"

        return f"{value:,.2f} บาท"

    # =====================================
    # Manual Refresh
    # =====================================

    def manual_refresh_gold(self):

        self.gold_status.set(
            "🟡 กำลังอัปเดตราคาทอง..."
        )

        self.update()

        result = update_gold_price()

        if result["success"]:

            self.load_latest_gold_price()

            self.gold_status.set(
                "🟢 อัปเดตราคาทองสำเร็จ"
            )

        else:

            self.load_latest_gold_price()

            self.gold_status.set(
                "🟠 เชื่อมต่อไม่ได้ ใช้ราคาล่าสุดจาก SQLite"
            )

            messagebox.showwarning(
                "ราคาทอง",
                "ไม่สามารถดึงราคาทองล่าสุดได้\n"
                "ระบบจึงใช้ราคาล่าสุดที่บันทึกไว้"
            )

    # =====================================
    # Auto Refresh ทุก 5 นาที
    # =====================================

    def auto_refresh_gold(self):

        print(
            "กำลังอัปเดตราคาทองอัตโนมัติ..."
        )

        result = update_gold_price()

        if result["success"]:

            self.load_latest_gold_price()

            self.gold_status.set(
                "🟢 ราคาทองอัปเดตอัตโนมัติสำเร็จ"
            )

        else:

            self.load_latest_gold_price()

            self.gold_status.set(
                "🟠 ใช้ราคาล่าสุดจาก SQLite"
            )

        self.after(
            self.REFRESH_INTERVAL,
            self.auto_refresh_gold
        )

    # =====================================
    # เปิดระบบลูกค้า
    # =====================================

    def open_customers(self):

        from ui.customers import CustomerWindow

        CustomerWindow(self)

    # =====================================
    # เปิดระบบรับขายฝาก
    # =====================================

    def open_pawn(self):
        try:
            from ui.pawn import PawnWindow
            PawnWindow(self, self.user)
        except Exception as error:
            print("PawnWindow error:", error)
            messagebox.showerror(
                "ระบบรับขายฝาก",
                "ไม่สามารถเปิดระบบรับขายฝากได้\n\n"
                f"{error}"
            )

    def open_suppliers(self):
        try:
            from ui.suppliers import SupplierWindow
            SupplierWindow(self, self.user)
        except Exception as error:
            messagebox.showerror("ผู้จำหน่ายและคู่ค้า", f"ไม่สามารถเปิดทะเบียนคู่ค้าได้\n\n{error}")

    def open_stock_receive(self):
        try:
            from ui.stock_receive import NewGoldReceiveWindow
            NewGoldReceiveWindow(self, self.user)
        except Exception as error:
            messagebox.showerror("รับทองใหม่เข้าสต็อก", f"ไม่สามารถเปิดระบบรับทองใหม่ได้\n\n{error}")

    def open_old_gold_buyback(self):
        try:
            from ui.old_gold_buyback import OldGoldBuybackWindow
            OldGoldBuybackWindow(self, self.user)
        except Exception as error:
            messagebox.showerror("รับซื้อทองเก่า", f"ไม่สามารถเปิดระบบรับซื้อทองเก่าได้\n\n{error}")

    def open_old_gold_stock(self):
        try:
            from ui.old_gold_stock import OldGoldStockWindow
            OldGoldStockWindow(self, self.user)
        except Exception as error:
            messagebox.showerror("สต็อกทองเก่า", f"ไม่สามารถเปิดระบบสต็อกทองเก่าได้\n\n{error}")

    def open_operations_center(self):
        try:
            from ui.operations_center import OperationsCenterWindow
            OperationsCenterWindow(self,self.user)
        except Exception as error:
            messagebox.showerror("ศูนย์บริหาร",f"ไม่สามารถเปิดศูนย์บริหารได้\n\n{error}")

    def open_reports(self):
        try:
            from modules.system_controls import has_permission
            if not has_permission(self.user,"view_cost"):
                messagebox.showwarning("ไม่มีสิทธิ์","รายงานการเงิน ต้นทุน และกำไร ต้องใช้สิทธิ์ผู้จัดการหรือฝ่ายบัญชี",parent=self);return
            from ui.reports import ReportsWindow
            ReportsWindow(self,self.user)
        except Exception as error:
            messagebox.showerror("ศูนย์รายงาน",f"ไม่สามารถเปิดศูนย์รายงานได้\n\n{error}")

    def open_system_control(self):
        try:
            from ui.system_control import SystemControlWindow
            SystemControlWindow(self,self.user)
        except Exception as error:
            messagebox.showerror("ศูนย์ควบคุมระบบ",f"ไม่สามารถเปิดศูนย์ควบคุมระบบได้\n\n{error}")

    def open_gold_sale(self):
        try:
            from ui.gold_sale import GoldSaleWindow
            GoldSaleWindow(self, self.user)
        except Exception as error:
            messagebox.showerror("ขายทองใหม่", f"ไม่สามารถเปิดระบบขายทองใหม่ได้\n\n{error}")

    def open_gold_exchange(self):
        try:
            from ui.gold_exchange import GoldExchangeWindow
            GoldExchangeWindow(self,self.user)
        except Exception as error:
            messagebox.showerror("แลกทองเก่าเป็นทองใหม่",f"ไม่สามารถเปิดระบบแลกทองได้\n\n{error}")

    def open_sale_history(self):
        try:
            from ui.sale_history import SaleHistoryWindow
            SaleHistoryWindow(self,self.user)
        except Exception as error:
            messagebox.showerror("ประวัติการขาย",f"ไม่สามารถเปิดประวัติการขายได้\n\n{error}")

    # =====================================
    # เมนูที่ยังไม่พร้อม
    # =====================================

    def open_pawn_renew(self):
        try:
            from ui.pawn_renew import PawnRenewWindow
            PawnRenewWindow(self, self.user)
        except Exception as error:
            messagebox.showerror("ต่อดอก", f"ไม่สามารถเปิดระบบต่อดอกได้\n\n{error}")

    def open_pawn_redeem(self):
        try:
            from ui.pawn_redeem import PawnRedeemWindow
            PawnRedeemWindow(self, self.user)
        except Exception as error:
            messagebox.showerror("ไถ่ถอน", f"ไม่สามารถเปิดระบบไถ่ถอนได้\n\n{error}")

    def open_pawn_forfeit(self):
        try:
            from ui.pawn_forfeit import PawnForfeitWindow
            PawnForfeitWindow(self, self.user)
        except Exception as error:
            messagebox.showerror("ตั๋วหลุดขายฝาก", f"ไม่สามารถเปิดระบบจัดการตั๋วหลุดขายฝากได้\n\n{error}")

    def open_pawn_corrections(self):
        try:
            from ui.pawn_corrections import PawnCorrectionWindow
            PawnCorrectionWindow(self, self.user)
        except Exception as error:
            messagebox.showerror("แก้ไขรายการผิด", f"ไม่สามารถเปิดระบบแก้ไขรายการได้\n\n{error}")

    def open_pawn_settings(self):
        try:
            from modules.system_controls import has_permission
            if not has_permission(self.user,"settings"):
                messagebox.showwarning("ไม่มีสิทธิ์","การตั้งค่าระบบต้องใช้สิทธิ์ผู้ดูแล",parent=self);return
            from ui.pawn_settings import PawnSettingsWindow
            PawnSettingsWindow(self)
        except Exception as error:
            messagebox.showerror("ตั้งค่าระบบขายฝาก", str(error))

    def open_settings(self):
        try:
            from ui.settings import SettingsWindow
            SettingsWindow(self, self.user)
        except Exception as error:
            from tkinter import messagebox
            messagebox.showerror("ตั้งค่า", f"ไม่สามารถเปิดหน้าตั้งค่าได้\n\n{error}")

    def not_ready(self):

        messagebox.showinfo(
            "Gold Shop System",
            "ฟังก์ชันนี้จะเปิดใช้งานใน V2 เป็นต้นไป"
        )

    # =====================================
    # Logout
    # =====================================

    def logout(self):

        answer = messagebox.askyesno(
            "ออกจากระบบ",
            "คุณต้องการออกจากระบบหรือไม่?"
        )

        if not answer:
            return

        self.destroy()
