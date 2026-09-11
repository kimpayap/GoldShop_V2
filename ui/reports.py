import csv
import tkinter as tk
from tkinter import ttk,messagebox,filedialog
from datetime import date
from modules.reporting import REPORT_TYPES,get_report,summarize_report,get_pawn_report_filters
from modules.report_receipt import print_report
from modules.thai_datetime import parse_thai_date_to_iso,format_thai_date
from ui.theme import apply_theme,open_fullscreen,back_to_dashboard
from ui.date_picker import open_thai_calendar


class ReportsWindow(tk.Toplevel):
    def __init__(self,parent,user=None):
        super().__init__(parent);self.parent=parent;self.user=user or {};self.rows=[];self.sort_reverse={};self.title("ศูนย์รายงาน");self.geometry("1450x900");open_fullscreen(self);apply_theme(self);self.build();self.load_report()

    def build(self):
        head=ttk.Frame(self,padding=10);head.pack(fill="x");ttk.Label(head,text="📊 ศูนย์รายงาน",font=("Arial",24,"bold")).pack(side="left");ttk.Button(head,text="← กลับ Dashboard",command=lambda:back_to_dashboard(self)).pack(side="right")
        f=ttk.LabelFrame(self,text="ตัวกรองรายงาน",padding=8);f.pack(fill="x",padx=10,pady=4)
        today=date.today();filters=get_pawn_report_filters();self.kind=tk.StringVar(value=REPORT_TYPES[0]);self.date_from=tk.StringVar(value=format_thai_date(today.replace(day=1)));self.date_to=tk.StringVar(value=format_thai_date(today));self.status=tk.StringVar(value="ทั้งหมด");self.series=tk.StringVar(value="ทั้งหมด");self.keyword=tk.StringVar();self.transaction_type=tk.StringVar(value="ทั้งหมด");self.item_type=tk.StringVar(value="ทั้งหมด");self.item_detail=tk.StringVar(value="ทั้งหมด");self.purity=tk.StringVar(value="ทั้งหมด");self.group_by=tk.StringVar(value="ประเภทและรายละเอียด")
        fields=(("ประเภทรายงาน",self.kind,REPORT_TYPES,24),("ตั้งแต่",self.date_from,None,14),("ถึง",self.date_to,None,14),("สถานะ",self.status,("ทั้งหมด","active","redeemed","forfeited","cancelled","completed","voided","in_stock","old_gold_stock","assembled","sent_to_refinery","melted","finalized","open"),18),("ระบบ",self.series,("ทั้งหมด","P","Q"),10),("ค้นหา",self.keyword,None,20))
        for col,(label,var,values,width) in enumerate(fields):
            ttk.Label(f,text=label).grid(row=0,column=col,sticky="w",padx=3)
            if var in (self.date_from,self.date_to):
                date_box=ttk.Frame(f);date_box.grid(row=1,column=col,padx=3);widget=ttk.Entry(date_box,textvariable=var,width=18);widget.pack(side="left",ipady=4);ttk.Button(date_box,text="📅",width=3,command=lambda v=var:open_thai_calendar(self,v)).pack(side="left",padx=2)
            else:
                widget=ttk.Combobox(f,textvariable=var,values=values,state="readonly",width=width) if values else ttk.Entry(f,textvariable=var,width=width);widget.grid(row=1,column=col,padx=3,ipady=4)
            widget.bind("<Return>",lambda _e:self.load_report())
        ttk.Button(f,text="แสดงรายงาน",style="TouchPrimary.TButton",command=self.load_report).grid(row=1,column=6,padx=6)
        ttk.Button(f,text="ส่งออก CSV",command=self.export_csv).grid(row=1,column=7,padx=3);ttk.Button(f,text="พิมพ์",command=self.print_current).grid(row=1,column=8,padx=3)
        advanced=(("ธุรกรรม",self.transaction_type,("ทั้งหมด","รับขายฝาก","ต่อสัญญา","ไถ่ถอน"),16),("ประเภทสินค้า",self.item_type,filters['types'],18),("รายละเอียด",self.item_detail,filters['details'],20),("%ทอง",self.purity,filters['purities'],12),("จัดกลุ่มตาม",self.group_by,("ประเภทและรายละเอียด","ประเภทสินค้า","รายละเอียดสินค้า","เปอร์เซ็นต์ทอง"),20))
        for col,(label,var,values,width) in enumerate(advanced):
            ttk.Label(f,text=label).grid(row=2,column=col,sticky="w",padx=3,pady=(8,0));ttk.Combobox(f,textvariable=var,values=values,state="readonly",width=width).grid(row=3,column=col,padx=3,ipady=4)
        ttk.Label(f,text="ตัวกรองสินค้าใช้กับทรัพย์ขายฝาก ขายทอง และสต็อกทองใหม่/ทองเก่า",foreground="#8a4b08").grid(row=3,column=5,columnspan=4,sticky="w",padx=5)
        self.summary=tk.StringVar();ttk.Label(self,textvariable=self.summary,font=("Arial",16,"bold"),padding=9).pack(fill="x",padx=10)
        columns=(("date","วันที่",145),("no","เลขเอกสาร",145),("category","ประเภท",155),("party","ลูกค้า/คู่ค้า",180),("detail","รายละเอียด",310),("qty","จำนวน",80),("weight","น้ำหนัก",100),("income","เงินเข้า/รายได้",130),("out","เงินออก/ต้นทุน",130),("vat","VAT",100),("status","สถานะ",120))
        box=ttk.Frame(self);box.pack(fill="both",expand=True,padx=10,pady=4);self.tree=ttk.Treeview(box,columns=[x[0] for x in columns],show="headings")
        for key,label,width in columns:self.tree.heading(key,text=label,command=lambda c=key:self.sort(c));self.tree.column(key,width=width,anchor="center")
        y=ttk.Scrollbar(box,orient="vertical",command=self.tree.yview);x=ttk.Scrollbar(box,orient="horizontal",command=self.tree.xview);self.tree.configure(yscrollcommand=y.set,xscrollcommand=x.set);self.tree.grid(row=0,column=0,sticky="nsew");y.grid(row=0,column=1,sticky="ns");x.grid(row=1,column=0,sticky="ew");box.rowconfigure(0,weight=1);box.columnconfigure(0,weight=1)
        self.tree.bind("<Double-1>",self.show_detail);ttk.Label(self,text="ดับเบิลคลิกรายการเพื่อดูรายละเอียด | ดับเบิลคลิก/คลิกหัวตารางเพื่อเรียงข้อมูล",padding=6).pack(anchor="w",padx=10)

    def load_report(self):
        try:
            start=parse_thai_date_to_iso(self.date_from.get());end=parse_thai_date_to_iso(self.date_to.get())
            if start>end:raise ValueError("วันที่เริ่มต้นต้องไม่เกินวันที่สิ้นสุด")
            self.rows=get_report(self.kind.get(),start,end,self.status.get(),self.series.get(),self.keyword.get(),self.transaction_type.get(),self.item_type.get(),self.item_detail.get(),self.purity.get(),self.group_by.get());self.render()
        except Exception as e:messagebox.showerror("แสดงรายงานไม่ได้",str(e),parent=self)

    def render(self):
        self.tree.delete(*self.tree.get_children())
        for n,r in enumerate(self.rows):self.tree.insert("","end",iid=str(n),values=(format_thai_date(r['report_date']),r['document_no'],r['category'],r['party'],r['detail'],f"{float(r.get('quantity') or 0):,.0f}",f"{float(r.get('weight') or 0):,.3f}",f"{float(r.get('amount_in') or 0):,.2f}",f"{float(r.get('amount_out') or 0):,.2f}",f"{float(r.get('vat') or 0):,.2f}",r['status']))
        s=summarize_report(self.rows);self.summary.set(f"{s['records']:,} รายการ | จำนวน {s['quantity']:,.0f} | น้ำหนัก {s['weight']:,.3f} กรัม | เงินเข้า/รายได้ {s['amount_in']:,.2f} | เงินออก/ต้นทุน {s['amount_out']:,.2f} | VAT {s['vat']:,.2f} | สุทธิ {s['amount_in']-s['amount_out']:,.2f} บาท")

    def sort(self,column):
        mapping={"date":"report_date","no":"document_no","category":"category","party":"party","detail":"detail","qty":"quantity","weight":"weight","income":"amount_in","out":"amount_out","vat":"vat","status":"status"};key=mapping[column];reverse=not self.sort_reverse.get(column,False);self.sort_reverse[column]=reverse
        numeric=key in {"quantity","weight","amount_in","amount_out","vat"};self.rows.sort(key=lambda r:float(r.get(key) or 0) if numeric else str(r.get(key) or ""),reverse=reverse);self.render()

    def show_detail(self,_event=None):
        selected=self.tree.selection()
        if not selected:return
        r=self.rows[int(selected[0])];text="\n".join((f"วันที่: {format_thai_date(r['report_date'])}",f"เลขเอกสาร: {r['document_no']}",f"ประเภท: {r['category']}",f"ลูกค้า/คู่ค้า: {r['party']}",f"รายละเอียด: {r['detail']}",f"จำนวน: {r['quantity']}",f"น้ำหนัก: {float(r['weight'] or 0):,.3f} กรัม",f"เงินเข้า/รายได้: {float(r['amount_in'] or 0):,.2f}",f"เงินออก/ต้นทุน: {float(r['amount_out'] or 0):,.2f}",f"VAT: {float(r['vat'] or 0):,.2f}",f"สถานะ: {r['status']}"));messagebox.showinfo("รายละเอียดรายงาน",text,parent=self)

    def export_csv(self):
        if not self.rows:messagebox.showwarning("ไม่มีข้อมูล","ไม่มีรายการสำหรับส่งออก",parent=self);return
        path=filedialog.asksaveasfilename(parent=self,defaultextension=".csv",filetypes=[("CSV","*.csv")],initialfile=f"report_{date.today().isoformat()}.csv")
        if not path:return
        headers=("วันที่","เลขเอกสาร","ประเภท","ลูกค้า/คู่ค้า","รายละเอียด","จำนวน","น้ำหนักกรัม","เงินเข้า/รายได้","เงินออก/ต้นทุน","VAT","สถานะ")
        with open(path,"w",newline="",encoding="utf-8-sig") as f:
            writer=csv.writer(f);writer.writerow(headers)
            for r in self.rows:writer.writerow((format_thai_date(r['report_date']),r['document_no'],r['category'],r['party'],r['detail'],r['quantity'],r['weight'],r['amount_in'],r['amount_out'],r['vat'],r['status']))
        messagebox.showinfo("ส่งออกสำเร็จ",path,parent=self)

    def print_current(self):
        if not self.rows:messagebox.showwarning("ไม่มีข้อมูล","ไม่มีรายการสำหรับพิมพ์",parent=self);return
        print_report(self.kind.get(),parse_thai_date_to_iso(self.date_from.get()),parse_thai_date_to_iso(self.date_to.get()),self.rows)
