import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from datetime import date,timedelta

from modules.auth import login
from modules.sales import list_gold_sales,get_gold_sale,cancel_gold_sale
from modules.thai_datetime import format_thai_date,format_thai_datetime,parse_thai_date_to_iso
from ui.date_picker import open_thai_calendar
from ui.settings_access import is_admin
from ui.theme import apply_theme,open_fullscreen,back_to_dashboard


STATUS_TEXT={"completed":"ขายสำเร็จ","cancelled":"ยกเลิกแล้ว"}


class SaleHistoryWindow(tk.Toplevel):
    def __init__(self,parent,user=None):
        super().__init__(parent);self.parent=parent;self.user=user or {};self.rows={}
        self.title("ประวัติการขายทอง");self.geometry("1400x850");self.minsize(1050,650);open_fullscreen(self);apply_theme(self);self.build();self.search()

    def build(self):
        head=ttk.Frame(self,padding=12);head.pack(fill="x");ttk.Label(head,text="🧾 ประวัติการขายทอง",font=("Arial",24,"bold")).pack(side="left");ttk.Button(head,text="← กลับ Dashboard",command=lambda:back_to_dashboard(self)).pack(side="right")
        filters=ttk.LabelFrame(self,text="ค้นหารายการขาย",padding=10);filters.pack(fill="x",padx=12,pady=5)
        self.keyword=tk.StringVar();self.date_from=tk.StringVar(value=format_thai_date(date.today()-timedelta(days=30)));self.date_to=tk.StringVar(value=format_thai_date(date.today()));self.status=tk.StringVar(value="ทั้งหมด");self.payment=tk.StringVar(value="ทั้งหมด")
        ttk.Label(filters,text="เลขที่/ลูกค้า/เลขภาษี/รหัสสินค้า/รายละเอียด").grid(row=0,column=0,sticky="w");ttk.Entry(filters,textvariable=self.keyword,font=("Arial",14)).grid(row=1,column=0,sticky="ew",padx=(0,5),ipady=5)
        for col,(label,var) in enumerate((("ตั้งแต่วันที่",self.date_from),("ถึงวันที่",self.date_to)),1):
            ttk.Label(filters,text=label).grid(row=0,column=col,sticky="w");box=ttk.Frame(filters);box.grid(row=1,column=col,sticky="ew",padx=4);ttk.Entry(box,textvariable=var,state="readonly").pack(side="left",fill="x",expand=True,ipady=5);ttk.Button(box,text="📅",command=lambda v=var,t=label:open_thai_calendar(self,v,t)).pack(side="left")
        ttk.Label(filters,text="สถานะ").grid(row=0,column=3,sticky="w");ttk.Combobox(filters,textvariable=self.status,values=("ทั้งหมด","ขายสำเร็จ","ยกเลิกแล้ว"),state="readonly").grid(row=1,column=3,sticky="ew",padx=4,ipady=5)
        ttk.Label(filters,text="ชำระโดย").grid(row=0,column=4,sticky="w");ttk.Combobox(filters,textvariable=self.payment,values=("ทั้งหมด","เงินสด","โอนเงิน","บัตรเครดิต"),state="readonly").grid(row=1,column=4,sticky="ew",padx=4,ipady=5)
        ttk.Button(filters,text="🔎 ค้นหา",style="TouchPrimary.TButton",command=self.search).grid(row=1,column=5,padx=4);ttk.Button(filters,text="ล้างตัวกรอง",command=self.clear_filters).grid(row=1,column=6,padx=4)
        filters.columnconfigure(0,weight=2)
        for col in range(1,5):filters.columnconfigure(col,weight=1)

        box=ttk.LabelFrame(self,text="รายการขายย้อนหลัง",padding=8);box.pack(fill="both",expand=True,padx=12,pady=5)
        cols=("sale_no","date","customer","items","payment","sale_total","fee","paid","status")
        self.tree=ttk.Treeview(box,columns=cols,show="headings",selectmode="browse")
        for key,label,width in (("sale_no","เลขที่ขาย",115),("date","วันที่",135),("customer","ลูกค้า",170),("items","รหัสสินค้า",190),("payment","ชำระโดย",105),("sale_total","ยอดขาย",115),("fee","ค่าธรรมเนียม",100),("paid","รับชำระ",115),("status","สถานะ",110)):
            self.tree.heading(key,text=label);self.tree.column(key,width=width,anchor="center")
        self.tree.pack(side="left",fill="both",expand=True);scroll=ttk.Scrollbar(box,orient="vertical",command=self.tree.yview);scroll.pack(side="right",fill="y");self.tree.configure(yscrollcommand=scroll.set);self.tree.bind("<<TreeviewSelect>>",self.show_detail);self.tree.bind("<Double-1>",lambda _e:self.print_selected())
        self.detail=tk.StringVar(value="กรุณาเลือกรายการขาย");ttk.Label(self,textvariable=self.detail,font=("Arial",13),justify="left",padding=(14,5)).pack(fill="x")
        actions=ttk.Frame(self,padding=10);actions.pack(fill="x");ttk.Button(actions,text="🖨 พิมพ์ใบเสร็จ/ใบกำกับภาษีซ้ำ",command=self.print_selected).pack(side="left",padx=5,ipady=8);ttk.Button(actions,text="⛔ ยกเลิกการขายและคืนสต็อก",style="Danger.TButton",command=self.cancel_selected).pack(side="right",padx=5,ipady=8)

    def clear_filters(self):
        self.keyword.set("");self.date_from.set("");self.date_to.set("");self.status.set("ทั้งหมด");self.payment.set("ทั้งหมด");self.search()

    def search(self):
        try:
            date_from=parse_thai_date_to_iso(self.date_from.get()) if self.date_from.get() else "";date_to=parse_thai_date_to_iso(self.date_to.get()) if self.date_to.get() else ""
            status={"ขายสำเร็จ":"completed","ยกเลิกแล้ว":"cancelled"}.get(self.status.get(),"");payment="" if self.payment.get()=="ทั้งหมด" else self.payment.get()
            rows=list_gold_sales(self.keyword.get(),date_from,date_to,status,payment);self.rows={x["id"]:x for x in rows};self.tree.delete(*self.tree.get_children())
            for x in rows:self.tree.insert("","end",iid=str(x["id"]),values=(x["sale_no"],format_thai_date(x["sale_date"]),x["customer_name"] or "ลูกค้าทั่วไป",x.get("item_codes") or "",x["payment_method"],f'{x["grand_total"]:,.2f}',f'{x["card_fee_amount"]:,.2f}',f'{x["amount_paid"]:,.2f}',STATUS_TEXT.get(x["status"],x["status"])))
            self.detail.set(f"พบ {len(rows)} รายการ")
        except Exception as error:messagebox.showerror("ค้นหาไม่ได้",str(error),parent=self)

    def selected(self):
        selected=self.tree.selection()
        if not selected:messagebox.showwarning("ยังไม่ได้เลือก","กรุณาเลือกรายการขาย",parent=self);return None
        return get_gold_sale(int(selected[0]))

    def show_detail(self,_event=None):
        selected=self.tree.selection()
        if not selected:return
        sale=get_gold_sale(int(selected[0]));items="\n".join(f"• {x['item_code']} {x['item_type']} {x['description']} {x['weight_grams']:,.3f} กรัม" for x in sale["items"])
        cancel=(f"\nยกเลิกเมื่อ: {format_thai_datetime(sale['cancelled_at'])} โดย {sale.get('cancelled_by_name') or '-'}\nเหตุผล: {sale['cancel_reason']}" if sale["status"]=="cancelled" else "")
        self.detail.set(f"{sale['sale_no']} | ลูกค้า: {sale['customer_name'] or 'ลูกค้าทั่วไป'} | VAT {sale['vat_amount']:,.2f} บาท | ยอดขาย {sale['grand_total']:,.2f} บาท\n{items}{cancel}")

    def print_selected(self):
        sale=self.selected()
        if not sale:return
        try:
            from modules.sale_receipt import print_sale_receipt
            print_sale_receipt(sale["id"])
        except Exception as error:messagebox.showerror("พิมพ์ไม่ได้",str(error),parent=self)

    def authorize(self):
        from ui.system_control import ask_approval
        return ask_approval(self,self.user,"cancel_transaction","ยกเลิกการขาย","gold_sale")

    def cancel_selected(self):
        sale=self.selected()
        if not sale:return
        if sale["status"]=="cancelled":messagebox.showinfo("ยกเลิกแล้ว","รายการขายนี้ถูกยกเลิกแล้ว",parent=self);return
        approval=self.authorize()
        if not approval:return
        reason=approval['reason']
        if not messagebox.askyesno("ยืนยันการยกเลิก",f"ยืนยันยกเลิก {sale['sale_no']}?\nสินค้า {len(sale['items'])} ชิ้นจะถูกคืนเข้าสต็อก\nข้อมูลการขายเดิมจะไม่ถูกลบ",parent=self):return
        try:
            result=cancel_gold_sale(sale["id"],reason,self.user.get("id"));messagebox.showinfo("สำเร็จ",f"ยกเลิก {result['sale_no']} แล้ว\nคืนสินค้า {result['returned_items']} ชิ้นเข้าสต็อก",parent=self);self.search()
            from modules.system_controls import log_audit
            log_audit("cancel","sales",self.user,"gold_sale",sale['id'],f"ยกเลิก {sale['sale_no']}",reason=reason)
            iid=str(sale["id"])
            if self.tree.exists(iid):self.tree.selection_set(iid);self.tree.focus(iid);self.tree.see(iid);self.show_detail()
            if messagebox.askyesno("พิมพ์เอกสาร","ต้องการพิมพ์เอกสารรายการที่ยกเลิกหรือไม่?",parent=self):
                from modules.sale_receipt import print_sale_receipt
                print_sale_receipt(sale["id"])
            if hasattr(self.parent,"refresh_dashboard"):self.parent.refresh_dashboard()
        except Exception as error:messagebox.showerror("ยกเลิกไม่ได้",str(error),parent=self)
