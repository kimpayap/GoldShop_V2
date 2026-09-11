import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from modules.pawn import list_overdue_pawns, get_pawn, forfeit_pawns_with_batch, get_pawn_display_status
from modules.forfeit_receipt import print_forfeit_batch_document
from modules.thai_datetime import format_thai_date
from ui.theme import apply_theme, open_fullscreen, back_to_dashboard

ALLOWED_ROLES={"admin","manager","owner"}

class PawnForfeitWindow(tk.Toplevel):
    def __init__(self,parent,user=None):
        super().__init__(parent)
        self.parent=parent;self.user=user or {};self.selected_ticket_ids=set()
        self.title("จัดการตั๋วหลุดขายฝาก")
        self.geometry("1050x700");self.minsize(900,620)
        open_fullscreen(self);self.create_style();apply_theme(self);self.create_widgets();self.load_tickets()

    def create_style(self):
        st=ttk.Style(self)
        try:st.theme_use("clam")
        except Exception:pass
        st.configure("Forfeit.TButton",font=("Arial",14,"bold"),padding=(14,11))
        st.configure("Danger.TButton",font=("Arial",16,"bold"),padding=(18,13))
        st.configure("Treeview",font=("Arial",12),rowheight=34)
        st.configure("Treeview.Heading",font=("Arial",12,"bold"))

    def create_widgets(self):
        head=ttk.Frame(self,padding=12);head.pack(fill="x")
        ttk.Label(head,text="⚫ จัดการตั๋วหลุดขายฝาก",font=("Arial",23,"bold")).pack(side="left")
        ttk.Button(head,text="← กลับ Dashboard",style="Forfeit.TButton",command=lambda:back_to_dashboard(self)).pack(side="right")

        notice=ttk.LabelFrame(self,text="หลักการทำงาน",padding=10);notice.pack(fill="x",padx=12,pady=4)
        ttk.Label(notice,text="ระบบจะแสดงเฉพาะตั๋วที่เกินกำหนด (overdue) และจะไม่เปลี่ยนเป็นหลุดขายฝากอัตโนมัติ ผู้มีสิทธิ์ต้องยืนยันเอง",font=("Arial",12)).pack(anchor="w")

        search=ttk.Frame(self,padding=(12,6));search.pack(fill="x")
        self.search_var=tk.StringVar()
        ttk.Entry(search,textvariable=self.search_var,font=("Arial",15),width=35).pack(side="left",ipady=7,padx=4)
        ttk.Button(search,text="🔎 ค้นหา",style="Forfeit.TButton",command=self.load_tickets).pack(side="left",padx=4)
        ttk.Button(search,text="ทั้งหมด",style="Forfeit.TButton",command=self.show_all).pack(side="left",padx=4)

        box=ttk.LabelFrame(self,text="ตั๋วเกินกำหนด",padding=8);box.pack(fill="both",expand=True,padx=12,pady=6)
        cols=("series","ticket","customer","loan","due","days")
        self.tree=ttk.Treeview(box,columns=cols,show="headings",selectmode="extended")
        for c,h,w in [("series","ระบบ",60),("ticket","เลขที่ตั๋ว",120),("customer","ลูกค้า",260),("loan","เงินต้น",130),("due","ครบกำหนด",130),("days","เกินกำหนด",110)]:
            self.tree.heading(c,text=h);self.tree.column(c,width=w,anchor="center")
        self.tree.pack(fill="both",expand=True)
        self.tree.bind("<Button-1>",self.toggle_ticket)

        action=ttk.LabelFrame(self,text="รายละเอียดและการยืนยัน",padding=12);action.pack(fill="x",padx=12,pady=(4,12))
        self.info_var=tk.StringVar(value="กรุณาเลือกตั๋ว")
        ttk.Label(action,textvariable=self.info_var,font=("Arial",13),justify="left").grid(row=0,column=0,columnspan=2,sticky="w")
        ttk.Label(action,text="หมายเหตุ/เหตุผล",font=("Arial",13,"bold")).grid(row=1,column=0,sticky="w",pady=(10,3))
        self.note=tk.Entry(action,font=("Arial",14));self.note.grid(row=2,column=0,sticky="ew",ipady=7,padx=(0,10))
        ttk.Button(action,text="⚫ ยืนยันรายการที่เลือก",style="Danger.TButton",command=self.confirm_forfeit).grid(row=2,column=1,sticky="ew")
        action.columnconfigure(0,weight=1)

    def show_all(self):self.search_var.set("");self.load_tickets()

    def load_tickets(self):
        self.selected_ticket_ids.clear()
        for x in self.tree.get_children():self.tree.delete(x)
        today=date.today()
        for p in list_overdue_pawns(self.search_var.get().strip()):
            due=date.fromisoformat(p["due_date"])
            self.tree.insert("","end",iid=str(p["id"]),values=(p.get("series_code","P"),p["ticket_no"],p["customer_name"],f'{p["loan_amount"]:,.2f}',format_thai_date(p["due_date"]),f"{(today-due).days} วัน"))

    def toggle_ticket(self,event):
        if self.tree.identify_region(event.x,event.y)!="cell":return
        iid=self.tree.identify_row(event.y)
        if not iid:return "break"
        ticket_id=int(iid)
        if ticket_id in self.selected_ticket_ids:self.selected_ticket_ids.remove(ticket_id)
        else:self.selected_ticket_ids.add(ticket_id)
        self.tree.selection_set(*(str(x) for x in self.selected_ticket_ids))
        self.show_selection_summary()
        return "break"

    def show_selection_summary(self):
        count=len(self.selected_ticket_ids)
        if not count:
            self.info_var.set("กรุณาแตะแถวเพื่อเลือกตั๋ว สามารถเลือกได้หลายรายการ");return
        pawns=[get_pawn(x) for x in sorted(self.selected_ticket_ids)]
        total=sum(float(p["loan_amount"]) for p in pawns)
        tickets=", ".join(p["ticket_no"] for p in pawns[:8])
        if count>8:tickets+=f" และอีก {count-8} รายการ"
        self.info_var.set(f"เลือกแล้ว {count} รายการ   เงินต้นรวม {total:,.2f} บาท\nตั๋ว: {tickets}")

    def confirm_forfeit(self):
        role=str(self.user.get("role","")).lower()
        if role not in ALLOWED_ROLES:
            messagebox.showwarning("ไม่มีสิทธิ์","การยืนยันหลุดขายฝากต้องใช้สิทธิ์ Admin / Manager / Owner",parent=self);return
        if not self.selected_ticket_ids:
            messagebox.showwarning("ตั๋วหลุดขายฝาก","กรุณาเลือกอย่างน้อย 1 รายการ",parent=self);return
        pawns=[get_pawn(x) for x in sorted(self.selected_ticket_ids)]
        invalid=[p["ticket_no"] for p in pawns if get_pawn_display_status(p)!="overdue"]
        if invalid:
            messagebox.showwarning("ตั๋วหลุดขายฝาก",f"มีตั๋วที่ไม่อยู่ในสถานะเกินกำหนด: {', '.join(invalid)}",parent=self);return
        total=sum(float(p["loan_amount"]) for p in pawns)
        if not messagebox.askyesno("ยืนยันหลุดขายฝาก",f"เลือก {len(pawns)} รายการ\nเงินต้นรวม {total:,.2f} บาท\n\nยืนยันเปลี่ยนทั้งหมดเป็นหลุดขายฝาก?",parent=self):return
        try:
            result=forfeit_pawns_with_batch(self.selected_ticket_ids,self.note.get().strip(),self.user.get("id"))
            messagebox.showinfo("สำเร็จ",f"เปลี่ยนสถานะเป็นหลุดขายฝากแล้ว {result['ticket_count']} รายการ\nเลขที่ชุด {result['batch_no']}",parent=self)
            if messagebox.askyesno("เอกสารตั๋วหลุดขายฝาก","เปิดเอกสารรายการสินค้าที่หลุดขายฝากชุดนี้เพื่อพิมพ์หรือไม่?",parent=self):
                print_forfeit_batch_document(result["batch_id"])
            self.selected_ticket_ids.clear();self.note.delete(0,"end");self.info_var.set("กรุณาแตะแถวเพื่อเลือกตั๋ว");self.load_tickets()
            if hasattr(self.parent,"refresh_dashboard"):self.parent.refresh_dashboard()
        except Exception as e:messagebox.showerror("ทำรายการไม่ได้",str(e),parent=self)
