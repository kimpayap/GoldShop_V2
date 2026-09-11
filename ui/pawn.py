from ui.settings_access import TouchKeypad, require_admin
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path

from modules.pawn import (
    search_pawn_customers, get_latest_gold_price, get_settings,
    list_gold_types, list_gold_details, list_gold_purities, list_weight_options,
    calculate_gold_value_baht, calculate_gold_value, calculate_interest, calculate_renewal_interest, create_pawn, list_pawns,
    get_pawn, renew_pawn, redeem_pawn, get_customer_by_citizen_id,get_series_settings,
    create_customer_from_id_card, _add_months,
)
from modules.thai_datetime import format_thai_date, format_thai_datetime
from ui.theme import apply_theme, open_fullscreen, back_to_dashboard
from ui.date_picker import open_thai_calendar
from modules.thai_datetime import parse_thai_date_to_iso

STATUS_FILTERS={"ตั๋วยังไม่ปิด":"open","ทั้งหมด":"","ปกติ":"active","ครบกำหนดวันนี้":"due","เกินกำหนด":"overdue","ไถ่ถอนแล้ว":"redeemed","หลุดขายฝาก":"forfeited","ยกเลิกแล้ว":"cancelled"}
STATUS_LABELS={"active":"ปกติ","due":"ครบกำหนดวันนี้","overdue":"เกินกำหนด","redeemed":"ไถ่ถอนแล้ว","forfeited":"หลุดขายฝาก","cancelled":"ยกเลิกแล้ว"}


class PawnWindow(tk.Toplevel):
    def __init__(self, parent, user=None):
        super().__init__(parent)
        self.parent = parent; self.user = user or {}; self.items=[]; self.customer_map={}; self.selected_ticket_id=None; self.card_customer=None;self.series_code=tk.StringVar(value="P");self.contract_term_days=tk.IntVar(value=120)
        self.title("รับขายฝาก - Gold Shop System V2.3"); self.geometry("1400x900"); self.minsize(1150,760)
        open_fullscreen(self); self.create_style(); apply_theme(self); self.create_widgets(); self.refresh_gold(); self.load_pawns()

    def create_style(self):
        st=ttk.Style(self)
        try: st.theme_use("clam")
        except Exception: pass
        st.configure("Touch.TButton",font=("Arial",13,"bold"),padding=(12,9))
        st.configure("TouchPrimary.TButton",font=("Arial",14,"bold"),padding=(15,11))
        st.configure("Touch.TLabel",font=("Arial",14))
        st.configure("TouchValue.TLabel",font=("Arial",18,"bold"))
        st.configure("Treeview",font=("Arial",12),rowheight=32)
        st.configure("Treeview.Heading",font=("Arial",12,"bold"))

    def create_widgets(self):
        # พื้นที่หลักแบบ Scroll สำหรับหน้าจอ Touch ที่มีความสูงไม่มาก
        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)

        self.main_canvas = tk.Canvas(
            outer,
            highlightthickness=0,
            borderwidth=0
        )
        scroll_y = ttk.Scrollbar(
            outer,
            orient="vertical",
            command=self.main_canvas.yview
        )
        self.main_canvas.configure(yscrollcommand=scroll_y.set)

        scroll_y.pack(side="right", fill="y")
        self.main_canvas.pack(side="left", fill="both", expand=True)

        self.body = ttk.Frame(self.main_canvas)
        self.body_window = self.main_canvas.create_window(
            (0, 0),
            window=self.body,
            anchor="nw"
        )

        def _resize_body(event):
            self.main_canvas.itemconfigure(
                self.body_window,
                width=event.width
            )

        def _update_scrollregion(event=None):
            self.main_canvas.configure(
                scrollregion=self.main_canvas.bbox("all")
            )

        self.main_canvas.bind("<Configure>", _resize_body)
        self.body.bind("<Configure>", _update_scrollregion)

        # Mouse wheel / trackpad
        self.main_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.main_canvas.yview_scroll(
                -1 if e.delta > 0 else 1, "units"
            )
        )

        header=ttk.Frame(self.body,padding=10); header.pack(fill="x")
        ttk.Label(header,text="📋 รับขายฝาก",font=("Arial",25,"bold")).pack(side="left")
        ttk.Button(header,text="⚙ ตั้งค่าระบบขายฝาก",style="Touch.TButton",command=self.open_settings).pack(side="right",padx=5)
        ttk.Button(header,text="← กลับ Dashboard",style="Touch.TButton",command=lambda:back_to_dashboard(self)).pack(side="right",padx=5)

        series=ttk.LabelFrame(self.body,text="เลือกระบบและระยะเวลาของสัญญานี้",padding=8);series.pack(fill="x",padx=14,pady=4)
        self.series_buttons={};self.term_buttons={}
        for code in ("P","Q"):
            button=ttk.Button(series,text=f"ระบบขายฝาก {code}",command=lambda c=code:self.select_series(c));button.pack(side="left",padx=4,ipadx=14);self.series_buttons[code]=button
        ttk.Separator(series,orient="vertical").pack(side="left",fill="y",padx=12)
        ttk.Label(series,text="กำหนดระยะเวลา",font=("Arial",14,"bold")).pack(side="left",padx=5)
        for days in (30,60,90,120):
            button=ttk.Button(series,text=f"{days} วัน",command=lambda d=days:self.select_term(d));button.pack(side="left",padx=3);self.term_buttons[days]=button
        self.next_ticket_var=tk.StringVar();ttk.Label(series,textvariable=self.next_ticket_var,font=("Arial",14,"bold")).pack(side="right",padx=10)
        self.render_contract_controls()

        customer=ttk.LabelFrame(self.body,text="1. ข้อมูลลูกค้า",padding=10); customer.pack(fill="x",padx=14,pady=6)
        left=ttk.Frame(customer); left.pack(side="left",fill="x",expand=True)
        ttk.Label(left,text="ลูกค้า",style="Touch.TLabel").grid(row=0,column=0,sticky="w",padx=5)
        self.customer_var=tk.StringVar(); self.customer_combo=ttk.Combobox(left,textvariable=self.customer_var,font=("Arial",16),width=44)
        self.customer_combo.grid(row=1,column=0,padx=5,pady=6,sticky="ew"); self.customer_combo.bind("<KeyRelease>",self.on_customer_search)
        ttk.Button(left,text="🔎 ค้นหาลูกค้า",style="Touch.TButton",command=self.search_customer_dialog).grid(row=1,column=1,padx=5)
        ttk.Button(left,text="💳 อ่านบัตรประชาชน",style="TouchPrimary.TButton",command=self.read_id_card_for_pawn).grid(row=1,column=2,padx=5)
        self.card_status_var=tk.StringVar(value="ยังไม่ได้อ่านบัตร"); ttk.Label(left,textvariable=self.card_status_var,style="Touch.TLabel").grid(row=2,column=0,columnspan=3,sticky="w",padx=5)
        for i in range(3): left.columnconfigure(i,weight=1)

        self.photo_label=ttk.Label(customer,text="ไม่มีรูป",anchor="center",width=20); self.photo_label.pack(side="right",padx=15)
        self.customer_info=tk.StringVar(value="ยังไม่ได้เลือกลูกค้า"); ttk.Label(customer,textvariable=self.customer_info,style="Touch.TLabel",justify="left").pack(side="right",fill="x",expand=True,padx=15)

        gold=ttk.Frame(self.body,padding=(10,3)); gold.pack(fill="x")
        self.gold_var=tk.StringVar(value="ราคาทอง: -"); self.rate_var=tk.StringVar(value="ผลตอบแทน: -")
        ttk.Label(gold,textvariable=self.gold_var,style="TouchValue.TLabel").pack(side="left")
        ttk.Label(gold,textvariable=self.rate_var,style="TouchValue.TLabel").pack(side="right")

        item=ttk.LabelFrame(self.body,text="2. ทรัพย์ขายฝาก — เลือกปุ่มแยกอิสระ",padding=10); item.pack(fill="x",padx=14,pady=6)
        self.item_type=tk.StringVar(value=""); self.description=tk.StringVar(value=""); self.purity=tk.StringVar(value=""); self.weight=tk.StringVar(value="1.00"); self.weight_unit=tk.StringVar(value="baht"); self.loan_value=tk.StringVar(value="")
        self.selected_gold_ids={"type":None,"detail":None,"purity":None}; self.selected_weight_id=None
        self.gold_button_rows={}
        for row,(title,key) in enumerate((("ประเภททอง","type"),("รายละเอียด","detail"),("%ทอง","purity"))):
            ttk.Label(item,text=title,font=("Arial",15,"bold")).grid(row=row*2,column=0,sticky="nw",padx=5,pady=5)
            frame=ttk.Frame(item); frame.grid(row=row*2,column=1,columnspan=6,sticky="ew",padx=5,pady=3)
            self.gold_button_rows[key]=frame
        ttk.Label(item,text="น้ำหนัก",font=("Arial",15,"bold")).grid(row=6,column=0,sticky="nw",padx=5,pady=5)
        weight_top=ttk.Frame(item); weight_top.grid(row=6,column=1,columnspan=6,sticky="ew",padx=5,pady=3)
        ttk.Button(weight_top,text="⚖ บาททอง",style="Touch.TButton",command=lambda:self.set_weight_unit("baht")).pack(side="left",padx=4)
        ttk.Button(weight_top,text="⚖ กรัม",style="Touch.TButton",command=lambda:self.set_weight_unit("gram")).pack(side="left",padx=4)
        self.weight_unit_label=tk.StringVar(value="กำลังเลือก: บาททอง")
        ttk.Label(weight_top,textvariable=self.weight_unit_label,font=("Arial",14,"bold")).pack(side="left",padx=12)
        ttk.Label(weight_top,text="กำหนดเอง",font=("Arial",14)).pack(side="left",padx=(16,4))
        self.weight_entry=ttk.Entry(weight_top,textvariable=self.weight,font=("Arial",16),width=10); self.weight_entry.pack(side="left",padx=4,ipady=8); self.weight_entry.bind("<Button-1>",lambda e:self.open_touch_keypad(self.weight,"ระบุน้ำหนัก"))
        ttk.Button(weight_top,text="✏ น้ำหนักเอง",style="Touch.TButton",command=lambda:self.open_touch_keypad(self.weight,"ระบุน้ำหนัก")).pack(side="left",padx=4)
        self.weight_button_frame=ttk.Frame(item); self.weight_button_frame.grid(row=7,column=1,columnspan=6,sticky="ew",padx=5,pady=(0,6))

        ttk.Label(item,text="วงเงินรายการ",font=("Arial",15,"bold")).grid(row=8,column=0,sticky="w",padx=5)
        self.loan_entry=ttk.Entry(item,textvariable=self.loan_value,font=("Arial",16),width=16); self.loan_entry.grid(row=8,column=1,padx=5,pady=5,sticky="w"); self.loan_entry.bind("<Button-1>",lambda e:self.open_touch_keypad(self.loan_value,"ระบุวงเงิน"))
        ttk.Button(item,text="💰 วงเงินเอง",style="Touch.TButton",command=lambda:self.open_touch_keypad(self.loan_value,"ระบุวงเงิน")).grid(row=8,column=2,padx=5)
        ttk.Button(item,text="🧮 คำนวณ",style="Touch.TButton",command=self.calculate_item).grid(row=8,column=3,padx=5,ipadx=10,ipady=10)
        ttk.Button(item,text="➕ เพิ่มรายการ",style="TouchPrimary.TButton",command=self.add_item).grid(row=8,column=4,padx=5,ipadx=12,ipady=10)
        ttk.Label(item,text="เลือกแล้ว:",font=("Arial",14,"bold")).grid(row=9,column=0,sticky="w",padx=5,pady=5)
        self.selection_summary=tk.StringVar(value="ประเภททอง: -   |   รายละเอียด: -   |   %ทอง: -   |   น้ำหนัก: -")
        ttk.Label(item,textvariable=self.selection_summary,font=("Arial",14,"bold")).grid(row=9,column=1,columnspan=6,sticky="w",padx=5)
        self.item_tree=ttk.Treeview(item,columns=("no","type","desc","purity","weight","value","loan"),show="headings",height=4)
        for c,h,w in [("no","#",55),("type","ประเภท",160),("desc","รายละเอียด",240),("purity","%ทอง",100),("weight","น้ำหนัก",145),("value","ประเมิน",150),("loan","วงเงิน",150)]: self.item_tree.heading(c,text=h); self.item_tree.column(c,width=w,anchor="center")
        self.item_tree.grid(row=10,column=0,columnspan=7,sticky="ew",pady=8)
        for i in range(7): item.columnconfigure(i,weight=1)
        self.load_gold_setting_buttons()
        self.load_weight_buttons()

        action=ttk.Frame(self.body,padding=8); action.pack(fill="x")
        self.loan_total_var=tk.StringVar(value="0.00 บาท")
        total_box=tk.Frame(action,bg="#facc15",highlightbackground="#b45309",highlightthickness=3,padx=14,pady=8)
        total_box.pack(side="left",padx=(0,12))
        tk.Label(total_box,text="วงเงินขายฝากรวม",bg="#facc15",fg="#422006",font=("Arial",18,"bold")).pack(side="left",padx=(0,14))
        tk.Label(total_box,textvariable=self.loan_total_var,bg="#facc15",fg="#b91c1c",font=("Arial",30,"bold"),width=15,anchor="e").pack(side="left")
        ttk.Label(action,text="หมายเหตุ",style="Touch.TLabel").pack(side="left",padx=(30,5)); self.notes=tk.Entry(action,font=("Arial",16),width=35); self.notes.pack(side="left")
        ttk.Button(action,text="🧹 ล้าง",style="Touch.TButton",command=self.clear_form).pack(side="right",padx=5)
        ttk.Button(action,text="💾 บันทึกใบรับขายฝาก",style="TouchPrimary.TButton",command=self.save_pawn).pack(side="right",padx=5)

        listbox=ttk.LabelFrame(self.body,text="3. ค้นหาสัญญาขายฝาก",padding=8); listbox.pack(fill="both",expand=True,padx=14,pady=6)
        sf=ttk.Frame(listbox); sf.pack(fill="x",pady=(0,6)); self.search_var=tk.StringVar()
        ttk.Entry(sf,textvariable=self.search_var,font=("Arial",15),width=32).pack(side="left",padx=5); ttk.Button(sf,text="ค้นหา",style="Touch.TButton",command=self.load_pawns).pack(side="left",padx=4); ttk.Button(sf,text="ทั้งหมด",style="Touch.TButton",command=lambda:(self.search_var.set(""),self.load_pawns())).pack(side="left",padx=4)
        ttk.Button(sf,text="🖨 พิมพ์",style="Touch.TButton",command=self.print_selected).pack(side="right",padx=4); ttk.Button(sf,text="ดูรายละเอียด",style="Touch.TButton",command=self.open_ticket).pack(side="right",padx=4); ttk.Button(sf,text="ต่อดอก",style="Touch.TButton",command=self.do_renew).pack(side="right",padx=4); ttk.Button(sf,text="ไถ่ถอน",style="Touch.TButton",command=self.do_redeem).pack(side="right",padx=4)
        filters=ttk.Frame(listbox);filters.pack(fill="x",pady=(0,6));self.date_from_var=tk.StringVar();self.date_to_var=tk.StringVar();self.status_filter_var=tk.StringVar(value="ตั๋วยังไม่ปิด")
        ttk.Label(filters,text="วันที่ทำสัญญา ตั้งแต่").pack(side="left",padx=(4,2));ttk.Entry(filters,textvariable=self.date_from_var,state="readonly",width=18).pack(side="left");ttk.Button(filters,text="📅",command=lambda:open_thai_calendar(self,self.date_from_var,"วันที่เริ่มต้น")).pack(side="left",padx=2)
        ttk.Label(filters,text="ถึง").pack(side="left",padx=(8,2));ttk.Entry(filters,textvariable=self.date_to_var,state="readonly",width=18).pack(side="left");ttk.Button(filters,text="📅",command=lambda:open_thai_calendar(self,self.date_to_var,"วันที่สิ้นสุด")).pack(side="left",padx=2)
        ttk.Label(filters,text="สถานะ").pack(side="left",padx=(12,3));ttk.Combobox(filters,textvariable=self.status_filter_var,values=list(STATUS_FILTERS),state="readonly",width=18).pack(side="left")
        ttk.Button(filters,text="ใช้ตัวกรอง",style="Touch.TButton",command=self.load_pawns).pack(side="left",padx=4);ttk.Button(filters,text="ล้างตัวกรอง",style="Touch.TButton",command=self.clear_search_filters).pack(side="left",padx=4)
        self.tree=ttk.Treeview(listbox,columns=("series","ticket","customer","status","loan","rate","term","opened","due"),show="headings")
        for c,h,w in [("series","ระบบ",60),("ticket","เลขที่ตั๋ว",115),("customer","ลูกค้า",220),("status","สถานะ",125),("loan","เงินต้น",120),("rate","ผลตอบแทน/เดือน",120),("term","ระยะเวลา",85),("opened","วันที่รับ",150),("due","ครบกำหนด",150)]: self.tree.heading(c,text=h); self.tree.column(c,width=w,anchor="center")
        self.tree.pack(side="left",fill="both",expand=True); sb=ttk.Scrollbar(listbox,orient="vertical",command=self.tree.yview); sb.pack(side="right",fill="y"); self.tree.configure(yscrollcommand=sb.set); self.tree.bind("<Double-1>",self.open_ticket)

    def open_touch_keypad(self, variable, title="แป้นตัวเลข"):
        """เปิดแป้นตัวเลขสำหรับ Touch Screen"""
        try:
            from ui.settings_access import TouchKeypad
            keypad = TouchKeypad(self, variable, title)
            keypad.update_idletasks()

            # จัด keypad ให้อยู่กลางหน้าต่างรับขายฝาก
            x = self.winfo_rootx() + max(0, (self.winfo_width() - keypad.winfo_width()) // 2)
            y = self.winfo_rooty() + max(0, (self.winfo_height() - keypad.winfo_height()) // 2)
            keypad.geometry(f"+{x}+{y}")

            self.wait_window(keypad)
            if variable is self.weight:
                self.selected_weight_id = None
                self.load_weight_buttons()
            self.update_selection_summary()
        except Exception as error:
            messagebox.showerror(
                "แป้นตัวเลข",
                f"ไม่สามารถเปิดแป้นตัวเลขได้\n\n{error}",
                parent=self
            )

    def refresh_gold(self):
        gold=get_latest_gold_price(); settings=get_settings(self.series_code.get()); self.rate_var.set(f"ระบบ {self.series_code.get()} | ผลตอบแทน {settings['monthly_interest_rate']:.2f}%/เดือน | สัญญานี้ {self.contract_term_days.get()} วัน")
        self.gold_var.set((f"ราคาทองแท่งรับซื้อ {float(gold['gold_bar_buy'] or 0):,.2f} บาท/บาททอง" if gold else "ราคาทอง: ยังไม่มีข้อมูล")); self.load_gold_setting_buttons(); self.load_weight_buttons()

    def render_contract_controls(self):
        code=self.series_code.get();days=self.contract_term_days.get()
        for value,button in self.series_buttons.items():button.configure(style="Selected.TButton" if value==code else "Touch.TButton")
        for value,button in self.term_buttons.items():button.configure(style="Selected.TButton" if value==days else "Touch.TButton")
        try:s=get_series_settings(code);self.next_ticket_var.set(f"เลขถัดไปประมาณ {code}{int(s['next_number']):06d}")
        except Exception:self.next_ticket_var.set("")

    def select_series(self,code):
        if self.items and not messagebox.askyesno("เปลี่ยนระบบ",f"มีรายการทรัพย์แล้ว ต้องการเปลี่ยนเป็นระบบ {code} หรือไม่?",parent=self):return
        self.series_code.set(code);settings=get_settings(code);default=int(settings["loan_term_days"]);self.contract_term_days.set(default if default in {30,60,90,120} else 120);self.render_contract_controls();self.refresh_gold()

    def select_term(self,days):
        self.contract_term_days.set(int(days));self.render_contract_controls();self.refresh_gold()

    def load_gold_setting_buttons(self):
        data={"type":list_gold_types(True),"detail":list_gold_details(True),"purity":list_gold_purities(True)}
        labels={"type":"ประเภททอง","detail":"รายละเอียด","purity":"%ทอง"}
        for key,frame in self.gold_button_rows.items():
            for w in frame.winfo_children(): w.destroy()
            max_columns=5 if self.winfo_screenwidth()<1700 else 7
            for i,r in enumerate(data[key]):
                text=r['name']
                selected = self.selected_gold_ids.get(key) == r['id']
                ttk.Button(frame,text=(f"✓ {text}" if selected else text),style=("Selected.TButton" if selected else "Touch.TButton"),command=lambda r=r,k=key:self.select_gold_setting(k,r)).grid(row=i//max_columns,column=i%max_columns,padx=3,pady=3,ipadx=6,ipady=5,sticky="ew")
            for column in range(max_columns):frame.columnconfigure(column,weight=1)

    def select_gold_setting(self,key,row):
        self.selected_gold_ids[key]=row['id']
        if key=="type": self.item_type.set(row['name'])
        elif key=="detail": self.description.set(row['name'])
        else: self.purity.set(str(row['percent']))
        self.load_gold_setting_buttons()
        self.update_selection_summary()

    def update_selection_summary(self):
        unit_text = "บาททอง" if self.weight_unit.get()=="baht" else "กรัม"
        self.selection_summary.set(
            f"ประเภททอง: {self.item_type.get() or '-'}   |   รายละเอียด: {self.description.get() or '-'}   |   "
            f"%ทอง: {self.purity.get() or '-'}   |   น้ำหนัก: {self.weight.get() or '-'} {unit_text}"
        )

    def set_weight_unit(self,unit):
        self.weight_unit.set(unit)
        self.weight_unit_label.set("กำลังเลือก: บาททอง" if unit=="baht" else "กำลังเลือก: กรัม")
        self.weight.set("")
        self.selected_weight_id=None
        self.load_weight_buttons()
        self.update_selection_summary()

    def load_weight_buttons(self):
        if not hasattr(self,"weight_button_frame"): return
        for w in self.weight_button_frame.winfo_children(): w.destroy()
        rows=list_weight_options(self.weight_unit.get(),True)
        for i,r in enumerate(rows):
            ttk.Button(
                self.weight_button_frame,text=(f"✓ {r['label']}" if self.selected_weight_id==r['id'] else r['label']),style=("Selected.TButton" if self.selected_weight_id==r['id'] else "Touch.TButton"),
                command=lambda r=r:self.select_weight(r)
            ).grid(row=i//6,column=i%6,padx=4,pady=4,ipadx=10,ipady=8,sticky="ew")
        for c in range(6): self.weight_button_frame.columnconfigure(c,weight=1)

    def select_weight(self,row):
        self.selected_weight_id=row['id']
        self.weight.set(f"{float(row['value']):g}")
        self.load_weight_buttons()
        self.update_selection_summary()

    def open_settings(self):
        from ui.pawn_settings import PawnSettingsWindow
        win=PawnSettingsWindow(self); self.wait_window(win); self.refresh_gold()

    def read_id_card_for_pawn(self):
        self.card_status_var.set("🟡 กำลังอ่านบัตรประชาชน..."); self.update_idletasks()
        try:
            from modules.thai_id_card import ThaiIDCardReader
            card=ThaiIDCardReader().read_card_once(); cid=(card.get("citizen_id") or "").strip()
            if not cid: raise ValueError("ไม่พบเลขบัตรประชาชน")
            customer=get_customer_by_citizen_id(cid); created=False
            if not customer: customer,created=create_customer_from_id_card(card)
            self.card_customer=customer
            label=f"{customer['customer_code']} | {customer.get('first_name','')} {customer.get('last_name','')} | {customer.get('citizen_id','-')}"
            self.customer_map[label]=customer["id"]; self.customer_combo["values"]=[label]; self.customer_var.set(label); self.show_customer(customer)
            self.card_status_var.set("🟢 เพิ่มลูกค้าใหม่และเลือกให้ใบขายฝากแล้ว" if created else "🟢 พบลูกค้าเดิมและดึงข้อมูลแล้ว")
            if created: messagebox.showinfo("ลูกค้าใหม่","ไม่พบข้อมูลเดิม\nระบบสร้างลูกค้าใหม่และนำเข้าใบขายฝากให้แล้ว",parent=self)
        except Exception as e: self.card_status_var.set("🔴 อ่านบัตรไม่สำเร็จ"); messagebox.showerror("อ่านบัตรประชาชน",str(e),parent=self)

    def show_customer(self,c):
        name=c.get("thai_name") or f"{c.get('first_name','')} {c.get('last_name','')}"
        info=f"รหัสลูกค้า: {c.get('customer_code','-')}\nชื่อ: {name}\nเลขบัตร: {c.get('citizen_id','-')}\nโทร: {c.get('phone') or '-'}\nที่อยู่: {c.get('address') or '-'}"
        self.customer_info.set(info); self.show_photo(c.get("photo_path"))

    def show_photo(self,path):
        try:
            if not path or not Path(path).exists(): self.photo_label.configure(text="ไม่มีรูป",image=""); return
            from PIL import Image,ImageTk
            img=Image.open(path); img.thumbnail((150,150)); self.photo_image=ImageTk.PhotoImage(img); self.photo_label.configure(image=self.photo_image,text="")
        except Exception: self.photo_label.configure(text="ไม่มีรูป",image="")

    def on_customer_search(self,event=None):
        rows=search_pawn_customers(self.customer_var.get().strip()); self.customer_map={}; vals=[]
        for c in rows[:30]:
            label=f"{c['customer_code']} | {c['first_name']} {c['last_name']} | {c['citizen_id'] or '-'}"; self.customer_map[label]=c["id"]; vals.append(label)
        self.customer_combo["values"]=vals
    def search_customer_dialog(self): self.on_customer_search(); self.customer_combo.event_generate("<Down>") if self.customer_combo["values"] else messagebox.showinfo("ลูกค้า","ไม่พบลูกค้า",parent=self)
    def get_customer_id(self):
        v=self.customer_var.get().strip()
        if v in self.customer_map: return self.customer_map[v]
        rows=search_pawn_customers(v.split("|")[0].strip()) if v else []
        return rows[0]["id"] if rows else None

    def calculate_item(self):
        try:
            gold=get_latest_gold_price()
            if not gold: raise ValueError("ยังไม่มีราคาทองในฐานข้อมูล")
            purity=float(self.purity.get())
            weight=float(self.weight.get())
            if self.weight_unit.get()=="baht":
                value=calculate_gold_value_baht(weight,purity,gold["gold_bar_buy"])
            else:
                value=calculate_gold_value(weight,purity,gold["gold_bar_buy"],get_settings()["weight_per_baht_gram"])
            self.loan_value.set(f"{value:.2f}")
            self.update_selection_summary()
        except Exception as e: messagebox.showwarning("คำนวณไม่ได้",str(e),parent=self)

    def add_item(self):
        try:
            gold=get_latest_gold_price(); typ=self.item_type.get().strip(); desc=self.description.get().strip(); purity=float(self.purity.get()); weight=float(self.weight.get()); loan=float(self.loan_value.get())
            if not self.selected_gold_ids["type"]: raise ValueError("กรุณาเลือกประเภททอง")
            if not self.selected_gold_ids["detail"]: raise ValueError("กรุณาเลือกรายละเอียด")
            if not self.selected_gold_ids["purity"]: raise ValueError("กรุณาเลือกเปอร์เซ็นต์ทอง")
            if weight<=0 or loan<=0: raise ValueError("น้ำหนักและวงเงินต้องมากกว่า 0")
            settings=get_settings(self.series_code.get())
            if self.weight_unit.get()=="baht":
                weight_baht=weight; grams=weight*float(settings["weight_per_baht_gram"]); estimated=calculate_gold_value_baht(weight_baht,purity,gold["gold_bar_buy"]); weight_display=f"{weight:g} บาท"
            else:
                grams=weight; weight_baht=grams/float(settings["weight_per_baht_gram"]); estimated=calculate_gold_value(grams,purity,gold["gold_bar_buy"],settings["weight_per_baht_gram"]); weight_display=f"{weight:g} กรัม"
            item={"item_type":typ,"description":desc,"purity":purity,"weight_grams":grams,"weight_baht":weight_baht,"weight_unit":self.weight_unit.get(),"weight_input":weight,"gold_price_per_baht":float(gold["gold_bar_buy"] or 0),"estimated_value":estimated,"loan_value":loan}
            self.items.append(item)
            self.item_tree.insert("","end",values=(len(self.items),typ,desc,f"{purity:.2f}",weight_display,f"{estimated:,.2f}",f"{loan:,.2f}"))
            self.update_total(); self.loan_value.set(""); self.update_selection_summary()
        except Exception as e: messagebox.showwarning("เพิ่มรายการไม่ได้",str(e),parent=self)

    def update_total(self): self.loan_total_var.set(f"{sum(float(x['loan_value']) for x in self.items):,.2f} บาท")
    def save_pawn(self):
        cid=self.get_customer_id()
        if not cid: messagebox.showwarning("ข้อมูลไม่ครบ","กรุณาอ่านบัตรหรือเลือกลูกค้า",parent=self); return
        if not self.items: messagebox.showwarning("ข้อมูลไม่ครบ","กรุณาเพิ่มทรัพย์ขายฝาก",parent=self); return
        total=sum(float(x["loan_value"]) for x in self.items)
        try:
            tid,ticket=create_pawn(cid,total,self.items,self.notes.get().strip(),self.user.get("id"),self.series_code.get(),self.contract_term_days.get()); messagebox.showinfo("สำเร็จ",f"สร้างสัญญาขายฝากระบบ {self.series_code.get()} เรียบร้อย\n\nเลขที่สัญญา: {ticket}\nระยะเวลา: {self.contract_term_days.get()} วัน\nวงเงิน: {total:,.2f} บาท",parent=self)
            if messagebox.askyesno("พิมพ์ใบรับขายฝาก","ต้องการพิมพ์ใบรับขายฝากหรือไม่?",parent=self):
                from modules.pawn_receipt import print_pawn_receipt
                print_pawn_receipt(tid)
            self.clear_form(); self.load_pawns()
            if hasattr(self.parent,"refresh_dashboard"): self.parent.refresh_dashboard()
        except Exception as e: messagebox.showerror("บันทึกไม่ได้",str(e),parent=self)

    def load_pawns(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        try:
            start=parse_thai_date_to_iso(self.date_from_var.get()) if self.date_from_var.get() else "";end=parse_thai_date_to_iso(self.date_to_var.get()) if self.date_to_var.get() else ""
            if start and end and start>end:raise ValueError("วันที่เริ่มต้นต้องไม่เกินวันที่สิ้นสุด")
            selected=STATUS_FILTERS.get(self.status_filter_var.get(),"open");stored="active" if selected=="open" else None;display="" if selected=="open" else selected
            rows=list_pawns(self.search_var.get(),stored,start,end,display)
        except Exception as error:messagebox.showwarning("ตัวกรองไม่ถูกต้อง",str(error),parent=self);return
        for p in rows:self.tree.insert("","end",iid=str(p["id"]),values=(p.get("series_code","P"),p["ticket_no"],p["customer_name"],STATUS_LABELS.get(p.get("display_status"),p.get("status")),f"{p['loan_amount']:,.2f}",f"{p['monthly_interest_rate']:.2f}%",f"{p.get('contract_term_days',120)} วัน",format_thai_datetime(p["opened_at"]),format_thai_date(p["due_date"])))

    def clear_search_filters(self):
        self.search_var.set("");self.date_from_var.set("");self.date_to_var.set("");self.status_filter_var.set("ตั๋วยังไม่ปิด");self.load_pawns()
    def get_selected(self):
        sel=self.tree.selection()
        if not sel: messagebox.showwarning("ยังไม่ได้เลือก","กรุณาเลือกตั๋วขายฝาก",parent=self); return None
        return get_pawn(int(sel[0]))
    def open_ticket(self,event=None):
        p=self.get_selected();
        if not p:return
        i=calculate_interest(p["loan_amount"],p["opened_at"],monthly_rate=p["monthly_interest_rate"]); messagebox.showinfo(f"ตั๋วขายฝาก {p['ticket_no']}",f"ลูกค้า: {p['first_name']} {p['last_name']}\nวันที่รับขายฝาก: {format_thai_datetime(p['opened_at'])}\nเงินต้น: {p['loan_amount']:,.2f} บาท\nผลตอบแทนประมาณ: {i['interest']:,.2f} บาท\nยอดไถ่โดยประมาณ: {i['total']:,.2f} บาท\nครบกำหนด: {format_thai_date(p['due_date'])}",parent=self)
    def print_selected(self):
        p=self.get_selected();
        if not p:return
        try:
            from modules.pawn_receipt import print_pawn_receipt
            print_pawn_receipt(p["id"])
        except Exception as e: messagebox.showerror("พิมพ์ไม่ได้",str(e),parent=self)
    def do_renew(self):
        p=self.get_selected();
        if not p:return
        if p.get("status")!="active":messagebox.showwarning("ต่อสัญญาไม่ได้","รายการที่ปิดหรือยกเลิกแล้วไม่สามารถต่อสัญญาได้",parent=self);return
        months=simpledialog.askinteger("ต่อดอก","กรอกจำนวนเดือนที่ต้องการต่อ:",parent=self,minvalue=1,maxvalue=120)
        if months is None:return
        interest=calculate_renewal_interest(p["loan_amount"],months,p["monthly_interest_rate"])
        new_due=_add_months(p["due_date"],months).isoformat()
        paid=simpledialog.askfloat("ต่อดอก",f"ต่อดอก {months} เดือน\nครบกำหนดเดิม: {format_thai_date(p['due_date'])}\nครบกำหนดใหม่: {format_thai_date(new_due)}\nผลตอบแทน {interest:,.2f} บาท\nกรอกจำนวนรับชำระ:",parent=self,minvalue=0)
        if paid is None:return
        try:
            result=renew_pawn(p["id"],paid,note="ต่อดอก",created_by=self.user.get("id"),renew_months=months)
            messagebox.showinfo("สำเร็จ",f"ต่อดอกเรียบร้อย\nครบกำหนดใหม่: {format_thai_date(result['new_due_date'])}",parent=self)
            self.load_pawns()
            ticket_iid=str(p["id"])
            if self.tree.exists(ticket_iid):
                self.tree.selection_set(ticket_iid);self.tree.focus(ticket_iid);self.tree.see(ticket_iid)
        except Exception as e: messagebox.showerror("ต่อดอกไม่ได้",str(e),parent=self)
    def do_redeem(self):
        p=self.get_selected();
        if not p:return
        if p.get("status")!="active":messagebox.showwarning("ไถ่ถอนไม่ได้","รายการที่ปิดหรือยกเลิกแล้วไม่สามารถไถ่ถอนได้",parent=self);return
        dashboard=self.parent; ticket_id=p["id"]; user=self.user
        back_to_dashboard(self)
        def open_redeem():
            from ui.pawn_redeem import PawnRedeemWindow
            PawnRedeemWindow(dashboard,user,initial_ticket_id=ticket_id)
        dashboard.after(160,open_redeem)
    def clear_form(self):
        self.items=[]; self.selected_gold_ids={"type":None,"detail":None,"purity":None}; self.selected_weight_id=None; self.item_type.set(""); self.description.set(""); self.purity.set(""); self.selection_summary.set("ประเภททอง: -   |   รายละเอียด: -   |   %ทอง: -   |   น้ำหนัก: -"); self.customer_var.set(""); self.customer_combo["values"]=[]; self.customer_map={}; self.card_customer=None; self.card_status_var.set("ยังไม่ได้อ่านบัตร"); self.customer_info.set("ยังไม่ได้เลือกลูกค้า"); self.photo_label.configure(text="ไม่มีรูป",image=""); self.description.set(""); self.weight_unit.set("baht"); self.weight_unit_label.set("กำลังเลือก: บาททอง"); self.weight.set(""); self.loan_value.set(""); self.load_weight_buttons(); self.notes.delete(0,tk.END); self.item_tree.delete(*self.item_tree.get_children()); self.loan_total_var.set("0.00 บาท"); self.refresh_gold()
