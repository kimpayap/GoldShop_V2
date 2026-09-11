import tkinter as tk
from tkinter import ttk,messagebox

from modules.old_gold import get_old_gold_receipt
from modules.gold_exchange import get_or_create_gold_exchange
from modules.sales import get_gold_sale
from modules.operations_control import start_exchange_workflow,update_exchange_workflow,get_exchange_workflow
from modules.gold_exchange_receipt import print_exchange_receipt
from ui.theme import apply_theme,open_fullscreen,back_to_dashboard


class GoldExchangeWindow(tk.Toplevel):
    def __init__(self,parent,user=None):
        super().__init__(parent);self.parent=parent;self.user=user or {};self.old_result=None;self.sale_result=None;self.workflow=start_exchange_workflow(self.user.get("id"))
        self.title("แลกทองเก่าเป็นทองใหม่");self.geometry("1200x760");open_fullscreen(self);apply_theme(self);self.build();self.restore_workflow();self.bind("<FocusIn>",lambda _e:self.restore_workflow())

    def build(self):
        head=ttk.Frame(self,padding=14);head.pack(fill="x")
        ttk.Label(head,text="🔄 แลกทองเก่าเป็นทองใหม่",font=("Arial",25,"bold")).pack(side="left")
        ttk.Button(head,text="← กลับ Dashboard",command=lambda:back_to_dashboard(self)).pack(side="right")
        ttk.Label(self,text="ทำตามลำดับ 1 → 2 ระบบจะเชื่อมเอกสารและคำนวณส่วนต่างให้อัตโนมัติ",font=("Arial",15),padding=12).pack(anchor="w")
        steps=ttk.Frame(self,padding=14);steps.pack(fill="x")
        old=ttk.LabelFrame(steps,text="1. รับซื้อทองเก่าจากลูกค้า",padding=18);old.pack(side="left",fill="both",expand=True,padx=8)
        self.old_text=tk.StringVar(value="ยังไม่ได้รับซื้อทองเก่า")
        ttk.Label(old,textvariable=self.old_text,font=("Arial",16,"bold"),justify="left").pack(anchor="w",pady=12)
        ttk.Button(old,text="เปิดหน้ารับซื้อทองเก่า",style="TouchPrimary.TButton",command=self.open_old_buyback).pack(fill="x",ipady=12)
        new=ttk.LabelFrame(steps,text="2. เลือกและขายทองใหม่",padding=18);new.pack(side="left",fill="both",expand=True,padx=8)
        self.new_text=tk.StringVar(value="กรุณาทำขั้นตอนรับซื้อทองเก่าก่อน")
        ttk.Label(new,textvariable=self.new_text,font=("Arial",16,"bold"),justify="left").pack(anchor="w",pady=12)
        ttk.Button(new,text="เปิดหน้าเลือกและขายทองใหม่",style="TouchPrimary.TButton",command=self.open_new_sale).pack(fill="x",ipady=12)
        settle=ttk.LabelFrame(self,text="การชำระเงินส่วนต่าง",padding=14);settle.pack(fill="x",padx=22,pady=10)
        self.method=tk.StringVar(value="เงินสด")
        ttk.Label(settle,text="วิธีชำระ/คืนส่วนต่าง",font=("Arial",14,"bold")).pack(side="left",padx=5)
        ttk.Combobox(settle,textvariable=self.method,values=("เงินสด","โอนเงิน","บัตรเครดิต"),state="readonly",width=20).pack(side="left",padx=8,ipady=5)
        self.summary=tk.StringVar(value="มูลค่าทองเก่า: -\nยอดทองใหม่: -\nเงินส่วนต่าง: -")
        ttk.Label(self,textvariable=self.summary,font=("Arial",23,"bold"),padding=22,anchor="center",justify="center",relief="solid").pack(fill="x",padx=22,pady=12)
        ttk.Label(self,text="เอกสารที่ได้: ใบรับซื้อทองเก่า/ใบสำคัญจ่ายเงิน + ใบกำกับภาษีขายทองใหม่ + ใบสรุปการแลกทอง",font=("Arial",13),padding=10).pack()

    def open_old_buyback(self):
        if self.old_result:
            messagebox.showwarning("ดำเนินการแล้ว","รายการนี้มีใบรับซื้อทองเก่าแล้ว กรุณาทำขั้นตอนขายทองใหม่",parent=self);return
        from ui.old_gold_buyback import OldGoldBuybackWindow
        OldGoldBuybackWindow(self,self.user,on_completed=self.old_completed,exchange_mode=True,exchange_workflow_id=self.workflow["workflow_id"])

    def old_completed(self,result):
        self.old_result=result
        self.old_text.set(f"เลขที่ {result['receipt_no']}\nมูลค่าที่ให้ลูกค้า {result['paid_amount']:,.2f} บาท")
        self.update_summary()

    def restore_workflow(self):
        workflow=get_exchange_workflow(self.workflow["workflow_id"])
        if not workflow:return
        if workflow.get("old_gold_receipt_id") and not self.old_result:
            receipt=get_old_gold_receipt(workflow["old_gold_receipt_id"])
        else:receipt=None
        if receipt and receipt.get("status")=="completed":
            self.old_result={"receipt_id":receipt["id"],"receipt_no":receipt["receipt_no"],"paid_amount":receipt["paid_amount"],"customer_id":receipt.get("customer_id")}
            self.old_text.set(f"เลขที่ {receipt['receipt_no']}\nมูลค่าที่ให้ลูกค้า {receipt['paid_amount']:,.2f} บาท")
            self.update_summary()
        # กู้รายการที่ขายและตัดสต็อกสำเร็จแล้ว แต่หน้าจอถูกปิดก่อนเชื่อมเอกสาร
        if workflow.get("gold_sale_id") and not self.sale_result and self.old_result:
            sale=get_gold_sale(workflow["gold_sale_id"])
            if sale and sale.get("status")=="completed":
                self.sale_result={"sale_id":sale["id"],"sale_no":sale["sale_no"],"grand_total":sale["grand_total"]}
                exchange=get_or_create_gold_exchange(self.old_result["receipt_id"],sale["id"],self.method.get(),created_by=self.user.get("id"))
                update_exchange_workflow(self.workflow["workflow_id"],exchange_id=exchange["exchange_id"])
                self.new_text.set(f"เลขที่ขาย {sale['sale_no']}\nยอดขายรวม VAT {sale['grand_total']:,.2f} บาท")
                self.update_summary()

    def open_new_sale(self):
        self.restore_workflow()
        if not self.old_result:
            messagebox.showwarning("ยังทำไม่ได้","กรุณารับซื้อทองเก่าก่อน",parent=self);return
        if self.sale_result:
            messagebox.showwarning("ดำเนินการแล้ว","รายการนี้ขายทองใหม่และเชื่อมเอกสารแล้ว",parent=self);return
        receipt=get_old_gold_receipt(self.old_result["receipt_id"])
        initial={"customer_name":f"{receipt.get('first_name') or ''} {receipt.get('last_name') or ''}".strip(),
                 "customer_tax_id":receipt.get("citizen_id") or "","customer_address":receipt.get("address") or ""}
        from ui.gold_sale import GoldSaleWindow
        GoldSaleWindow(self,self.user,on_completed=self.sale_completed,initial_customer=initial,exchange_mode=True,exchange_credit=self.old_result["paid_amount"])

    def sale_completed(self,result):
        try:
            self.sale_result=result
            update_exchange_workflow(self.workflow["workflow_id"],sale_id=result["sale_id"])
            exchange=get_or_create_gold_exchange(self.old_result["receipt_id"],result["sale_id"],self.method.get(),created_by=self.user.get("id"))
            update_exchange_workflow(self.workflow["workflow_id"],exchange_id=exchange["exchange_id"])
            self.new_text.set(f"เลขที่ขาย {result['sale_no']}\nยอดขายรวม VAT {result['grand_total']:,.2f} บาท")
            self.update_summary()
            diff=exchange["difference_amount"]
            text=f"ลูกค้าชำระเพิ่ม {diff:,.2f} บาท" if diff>0 else (f"ร้านคืนลูกค้า {abs(diff):,.2f} บาท" if diff<0 else "ไม่มีเงินส่วนต่าง")
            # รอให้หน้าขายปิดก่อน จึงแสดงข้อความและถามพิมพ์เอกสาร
            self.after_idle(lambda:self.finish_completed(exchange,result,text))
            if hasattr(self.parent,"refresh_dashboard"):self.parent.refresh_dashboard()
        except Exception as error:
            messagebox.showerror("เชื่อมรายการไม่ได้",f"ขายทองสำเร็จแล้ว แต่เชื่อมรายการแลกทองไม่ได้\n\n{error}",parent=self)

    def finish_completed(self,exchange,result,text):
        messagebox.showinfo("แลกทองสำเร็จ",f"เลขที่ {exchange['exchange_no']}\n{text}",parent=self)
        if messagebox.askyesno("พิมพ์เอกสาร","ต้องการพิมพ์ใบกำกับภาษีขายทองใหม่และใบสรุปการแลกทองหรือไม่?",parent=self):
            from modules.sale_receipt import print_sale_receipt
            print_sale_receipt(result["sale_id"]);print_exchange_receipt(exchange["exchange_id"])

    def update_summary(self):
        old=float(self.old_result["paid_amount"]) if self.old_result else 0
        new=float(self.sale_result["grand_total"]) if self.sale_result else 0
        if not self.sale_result:result="รอเลือกทองใหม่"
        elif new>old:result=f"ลูกค้าชำระเพิ่ม {new-old:,.2f} บาท"
        elif old>new:result=f"ร้านคืนลูกค้า {old-new:,.2f} บาท"
        else:result="ไม่มีเงินส่วนต่าง"
        self.summary.set(f"มูลค่าทองเก่า (ยอดจ่ายจริง): {old:,.2f} บาท\nยอดทองใหม่รวม VAT: {new:,.2f} บาท\n{result}")
