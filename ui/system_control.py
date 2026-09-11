import tkinter as tk
from tkinter import ttk,messagebox,filedialog,simpledialog
from datetime import date,timedelta
from modules.system_controls import (PERMISSIONS,has_permission,verify_approver,list_users,save_user,get_role_permissions,set_role_permission,
 create_backup,verify_backup,restore_backup,list_backups,get_backup_settings,save_backup_settings,list_audit_logs,
 open_shift,get_shift,calculate_shift,close_shift,list_shifts)
from modules.control_receipts import print_shift_receipt
from modules.thai_datetime import format_thai_datetime,format_thai_date
from ui.theme import apply_theme,open_fullscreen,back_to_dashboard


def ask_approval(parent,user,permission,action,record_type="",record_id=""):
    dlg=tk.Toplevel(parent);dlg.title("ขออนุมัติ");dlg.transient(parent);dlg.grab_set();result={};username=tk.StringVar();password=tk.StringVar();reason=tk.StringVar()
    form=ttk.Frame(dlg,padding=15);form.pack()
    for row,(label,var,show) in enumerate((("ชื่อผู้อนุมัติ",username,None),("รหัสผ่าน",password,"*"),("เหตุผล",reason,None))):ttk.Label(form,text=label).grid(row=row,column=0,sticky="w",pady=5);ttk.Entry(form,textvariable=var,show=show or "",width=34).grid(row=row,column=1,pady=5,ipady=5)
    def submit():
        try:result.update(verify_approver(username.get(),password.get(),permission,user.get('id'),action,record_type,record_id,reason.get()));result['reason']=reason.get();dlg.destroy()
        except Exception as e:messagebox.showerror("อนุมัติไม่ได้",str(e),parent=dlg)
    ttk.Button(form,text="ยืนยันอนุมัติ",style="TouchPrimary.TButton",command=submit).grid(row=3,column=0,columnspan=2,pady=12);parent.wait_window(dlg);return result or None


class SystemControlWindow(tk.Toplevel):
    def __init__(self,parent,user=None):
        super().__init__(parent);self.parent=parent;self.user=user or {};self.edit_user_id=None;self.current_shift=None;self.title("ความปลอดภัย สำรองข้อมูล และปิดกะ");self.geometry("1450x900");open_fullscreen(self);apply_theme(self);self.build();self.refresh_all()

    def build(self):
        head=ttk.Frame(self,padding=10);head.pack(fill="x");ttk.Label(head,text="🔐 ศูนย์ควบคุมระบบ",font=("Arial",24,"bold")).pack(side="left");ttk.Button(head,text="← กลับ Dashboard",command=lambda:back_to_dashboard(self)).pack(side="right")
        tabs=ttk.Notebook(self);tabs.pack(fill="both",expand=True,padx=10,pady=5);self.backup=ttk.Frame(tabs);self.users=ttk.Frame(tabs);self.audit=ttk.Frame(tabs);self.shift=ttk.Frame(tabs)
        tabs.add(self.backup,text="💾 สำรอง/กู้คืน");tabs.add(self.users,text="👥 ผู้ใช้และสิทธิ์");tabs.add(self.audit,text="📜 ประวัติการใช้งาน");tabs.add(self.shift,text="💰 เปิดกะ/ปิดยอด")
        self.build_backup();self.build_users();self.build_audit();self.build_shift()

    def tree(self,parent,columns):
        box=ttk.Frame(parent);box.pack(fill="both",expand=True,padx=7,pady=5);tree=ttk.Treeview(box,columns=[x[0] for x in columns],show="headings")
        for key,title,width in columns:tree.heading(key,text=title);tree.column(key,width=width,anchor="center")
        bar=ttk.Scrollbar(box,orient="vertical",command=tree.yview);tree.configure(yscrollcommand=bar.set);tree.pack(side="left",fill="both",expand=True);bar.pack(side="right",fill="y");return tree

    def build_backup(self):
        settings=get_backup_settings();f=ttk.LabelFrame(self.backup,text="ตั้งค่าสำรองอัตโนมัติรายวัน",padding=10);f.pack(fill="x",padx=8,pady=6);self.backup_folder=tk.StringVar(value=settings['folder']);self.retention=tk.StringVar(value=str(settings['retention_days']))
        ttk.Label(f,text="โฟลเดอร์").pack(side="left");ttk.Entry(f,textvariable=self.backup_folder,width=58).pack(side="left",padx=4);ttk.Button(f,text="เลือก",command=self.choose_backup_folder).pack(side="left");ttk.Label(f,text="เก็บย้อนหลัง (วัน)").pack(side="left",padx=(15,3));ttk.Entry(f,textvariable=self.retention,width=7).pack(side="left");ttk.Button(f,text="บันทึกตั้งค่า",command=self.save_backup_config).pack(side="left",padx=5)
        actions=ttk.Frame(self.backup,padding=8);actions.pack(fill="x");ttk.Button(actions,text="สำรองข้อมูลตอนนี้",style="TouchPrimary.TButton",command=self.backup_now).pack(side="left");ttk.Button(actions,text="ตรวจสอบไฟล์",command=self.verify_file).pack(side="left",padx=5);ttk.Button(actions,text="กู้คืนจากไฟล์",style="Danger.TButton",command=self.restore_file).pack(side="left",padx=5);ttk.Label(actions,text="ก่อนกู้คืน ระบบจะสำรองฐานข้อมูลปัจจุบันให้อัตโนมัติ",foreground="#8a4b08").pack(side="left",padx=15)
        self.backup_tree=self.tree(self.backup,(("date","วันเวลา",180),("name","ชื่อไฟล์",250),("type","ประเภท",110),("size","ขนาด",100),("user","ผู้สร้าง",150),("status","สถานะ",100),("path","ตำแหน่ง",420)))

    def build_users(self):
        form=ttk.LabelFrame(self.users,text="เพิ่ม/แก้ไขผู้ใช้",padding=8);form.pack(fill="x",padx=8,pady=5);self.uv={k:tk.StringVar() for k in ('username','password','full_name')};self.uv['role']=tk.StringVar(value='staff');self.uv['active']=tk.BooleanVar(value=True)
        for col,(label,key,width) in enumerate((("ชื่อผู้ใช้","username",16),("รหัสผ่าน","password",16),("ชื่อพนักงาน","full_name",24))):ttk.Label(form,text=label).grid(row=0,column=col,padx=3);ttk.Entry(form,textvariable=self.uv[key],show='*' if key=='password' else '',width=width).grid(row=1,column=col,padx=3,ipady=5)
        ttk.Label(form,text="บทบาท").grid(row=0,column=3);ttk.Combobox(form,textvariable=self.uv['role'],values=('admin','owner','manager','accounting','staff'),state='readonly',width=15).grid(row=1,column=3,padx=3,ipady=5);ttk.Checkbutton(form,text="ใช้งาน",variable=self.uv['active']).grid(row=1,column=4,padx=5);ttk.Button(form,text="บันทึกผู้ใช้",command=self.save_user_form).grid(row=1,column=5,padx=5);ttk.Button(form,text="ล้าง",command=self.clear_user).grid(row=1,column=6)
        body=ttk.Panedwindow(self.users,orient='horizontal');body.pack(fill='both',expand=True);left=ttk.Frame(body);right=ttk.LabelFrame(body,text="สิทธิ์ของบทบาท",padding=8);body.add(left,weight=2);body.add(right,weight=1)
        self.user_tree=self.tree(left,(("username","ชื่อผู้ใช้",150),("name","ชื่อ",190),("role","บทบาท",120),("active","สถานะ",100),("created","สร้างเมื่อ",170)));self.user_tree.bind('<Double-1>',self.edit_user)
        self.permission_role=tk.StringVar(value='staff');ttk.Combobox(right,textvariable=self.permission_role,values=('admin','owner','manager','accounting','staff'),state='readonly').pack(fill='x');self.permission_role.trace_add('write',lambda *_:self.load_permissions());self.permission_vars={}
        for code,label in PERMISSIONS.items():var=tk.BooleanVar();self.permission_vars[code]=var;ttk.Checkbutton(right,text=label,variable=var,command=lambda c=code,v=var:self.change_permission(c,v)).pack(anchor='w',pady=3)

    def build_audit(self):
        f=ttk.Frame(self.audit,padding=7);f.pack(fill='x');self.audit_keyword=tk.StringVar();ttk.Label(f,text="ค้นหา").pack(side='left');ttk.Entry(f,textvariable=self.audit_keyword,width=35).pack(side='left',padx=5);ttk.Button(f,text="รีเฟรช",command=self.load_audit).pack(side='left');self.audit_tree=self.tree(self.audit,(("date","วันเวลา",180),("user","ผู้ใช้",120),("action","การกระทำ",120),("module","ระบบ",120),("record","เอกสาร/รหัส",150),("detail","รายละเอียด",350),("reason","เหตุผล",220),("computer","เครื่อง",130)))

    def build_shift(self):
        top=ttk.LabelFrame(self.shift,text="กะประจำวัน",padding=8);top.pack(fill='x',padx=8,pady=5);self.opening_cash=tk.StringVar(value='0');self.shift_note=tk.StringVar();ttk.Label(top,text="เงินสดต้นกะ").pack(side='left');ttk.Entry(top,textvariable=self.opening_cash,width=15).pack(side='left',padx=4);ttk.Label(top,text="หมายเหตุ").pack(side='left');ttk.Entry(top,textvariable=self.shift_note,width=35).pack(side='left',padx=4);ttk.Button(top,text="เปิดกะ",command=self.open_today_shift).pack(side='left',padx=5);ttk.Button(top,text="คำนวณยอดตามระบบ",command=self.load_shift).pack(side='left',padx=5)
        self.shift_info=tk.StringVar(value="ยังไม่ได้เปิดกะ");ttk.Label(self.shift,textvariable=self.shift_info,font=('Arial',16,'bold'),padding=8).pack(anchor='w')
        close=ttk.LabelFrame(self.shift,text="ยอดนับจริง",padding=8);close.pack(fill='x',padx=8,pady=5);self.actual={m:tk.StringVar(value='0') for m in ('เงินสด','โอนเงิน','บัตรเครดิต','อื่น ๆ')};self.expected_labels={}
        for col,m in enumerate(self.actual):ttk.Label(close,text=m,font=('Arial',12,'bold')).grid(row=0,column=col,padx=8);label=ttk.Label(close,text="ตามระบบ 0.00");label.grid(row=1,column=col);self.expected_labels[m]=label;ttk.Entry(close,textvariable=self.actual[m],width=16).grid(row=2,column=col,padx=8,ipady=5)
        ttk.Button(close,text="ยืนยันปิดกะ",style="TouchPrimary.TButton",command=self.close_today_shift).grid(row=2,column=4,padx=12);ttk.Button(close,text="พิมพ์ใบปิดกะ",command=self.print_shift).grid(row=2,column=5,padx=5)
        self.shift_tree=self.tree(self.shift,(("date","วันที่",130),("no","เลขกะ",140),("opening","เงินต้นกะ",120),("status","สถานะ",100),("opened","ผู้เปิด",140),("closed","ผู้ปิด",140),("approved","ผู้อนุมัติ",140),("time","เวลาปิด",180)))

    def refresh_all(self):self.load_backups();self.load_users();self.load_permissions();self.load_audit();self.load_shift();self.load_shifts()
    def choose_backup_folder(self):
        path=filedialog.askdirectory(parent=self);self.backup_folder.set(path or self.backup_folder.get())
    def save_backup_config(self):
        try:save_backup_settings(self.backup_folder.get(),self.retention.get(),self.user);messagebox.showinfo("สำเร็จ","บันทึกการตั้งค่าสำรองแล้ว",parent=self)
        except Exception as e:messagebox.showerror("บันทึกไม่ได้",str(e),parent=self)
    def backup_now(self):
        try:r=create_backup(self.user,self.backup_folder.get(),'manual');messagebox.showinfo("สำรองสำเร็จ",f"{r['path']}\nขนาด {r['size']/1024/1024:.2f} MB",parent=self);self.load_backups()
        except Exception as e:messagebox.showerror("สำรองไม่ได้",str(e),parent=self)
    def verify_file(self):
        path=filedialog.askopenfilename(parent=self,filetypes=(("ฐานข้อมูล GoldShop","*.db"),("ทุกไฟล์","*.*")))
        if path:
            try:r=verify_backup(path);messagebox.showinfo("ไฟล์สมบูรณ์",f"ขนาด {r['size']/1024/1024:.2f} MB\nSHA-256: {r['checksum']}",parent=self)
            except Exception as e:messagebox.showerror("ไฟล์ใช้ไม่ได้",str(e),parent=self)
    def restore_file(self):
        path=filedialog.askopenfilename(parent=self,filetypes=(("ฐานข้อมูล GoldShop","*.db"),("ทุกไฟล์","*.*")))
        if not path:return
        if not messagebox.askyesno("ยืนยันกู้คืน","ข้อมูลปัจจุบันจะถูกแทนที่ และต้องปิดเปิดโปรแกรมใหม่\nดำเนินการต่อหรือไม่?",parent=self):return
        approval=ask_approval(self,self.user,'restore','กู้คืนฐานข้อมูล','database')
        if not approval:return
        try:r=restore_backup(path,self.user,approval,approval['reason']);messagebox.showinfo("กู้คืนสำเร็จ",f"กู้คืนข้อมูลแล้ว\nไฟล์ก่อนกู้คืน: {r['safety']['path']}\nกรุณาปิดและเปิดโปรแกรมใหม่",parent=self)
        except Exception as e:messagebox.showerror("กู้คืนไม่ได้",str(e),parent=self)
    def load_backups(self):
        self.backup_tree.delete(*self.backup_tree.get_children())
        for x in list_backups():self.backup_tree.insert('', 'end',values=(format_thai_datetime(x['created_at']),x['file_name'],x['backup_type'],f"{x['file_size']/1024/1024:.2f} MB",x['created_name'] or '-',x['status'],x['file_path']))
    def save_user_form(self):
        try:save_user(self.edit_user_id,self.uv['username'].get(),self.uv['password'].get(),self.uv['full_name'].get(),self.uv['role'].get(),self.uv['active'].get(),self.user);self.clear_user();self.load_users()
        except Exception as e:messagebox.showerror("บันทึกไม่ได้",str(e),parent=self)
    def clear_user(self):
        self.edit_user_id=None
        for key in ('username','password','full_name'):self.uv[key].set('')
        self.uv['role'].set('staff');self.uv['active'].set(True)
    def load_users(self):
        self.user_tree.delete(*self.user_tree.get_children())
        if not has_permission(self.user,'manage_users'):return
        for x in list_users():self.user_tree.insert('', 'end',iid=str(x['id']),values=(x['username'],x['full_name'],x['role'],'ใช้งาน' if x['active'] else 'ปิด',format_thai_datetime(x['created_at'])))
    def edit_user(self,_e=None):
        selected=self.user_tree.selection()
        if not selected:return
        x=next(r for r in list_users() if r['id']==int(selected[0]));self.edit_user_id=x['id'];self.uv['username'].set(x['username']);self.uv['password'].set('');self.uv['full_name'].set(x['full_name']);self.uv['role'].set(x['role']);self.uv['active'].set(bool(x['active']))
    def load_permissions(self):
        values=get_role_permissions(self.permission_role.get())
        for code,var in self.permission_vars.items():var.set(values.get(code,False))
    def change_permission(self,code,var):
        try:set_role_permission(self.permission_role.get(),code,var.get(),self.user)
        except Exception as e:messagebox.showerror("เปลี่ยนสิทธิ์ไม่ได้",str(e),parent=self);self.load_permissions()
    def load_audit(self):
        self.audit_tree.delete(*self.audit_tree.get_children())
        if not has_permission(self.user,'view_audit'):return
        start=(date.today()-timedelta(days=90)).isoformat();end=date.today().isoformat()
        for x in list_audit_logs(start,end,self.audit_keyword.get()):self.audit_tree.insert('', 'end',values=(format_thai_datetime(x['event_at']),x['username'] or '-',x['action'],x['module'],f"{x['record_type']} {x['record_id']}",x['description'],x['reason'] or '-',x['computer_name']))
    def open_today_shift(self):
        try:self.current_shift=open_shift(self.opening_cash.get(),self.user,self.shift_note.get());self.load_shift();self.load_shifts()
        except Exception as e:messagebox.showerror("เปิดกะไม่ได้",str(e),parent=self)
    def load_shift(self):
        self.current_shift=get_shift()
        if not self.current_shift:self.shift_info.set("ยังไม่ได้เปิดกะ");return
        x=self.current_shift;self.shift_info.set(f"{x['shift_no']} | {format_thai_date(x['shift_date'])} | เงินสดต้นกะ {x['opening_cash']:,.2f} | สถานะ {x['status']}")
        expected=x.get('expected') if x['status']=='closed' else calculate_shift(x['id'])
        for m,label in self.expected_labels.items():label.configure(text=f"ตามระบบ {expected.get(m,0):,.2f}")
        if x['status']=='closed':
            for m,var in self.actual.items():var.set(f"{x['actual'].get(m,0):.2f}")
    def close_today_shift(self):
        if not self.current_shift:return
        approval=ask_approval(self,self.user,'close_shift','ปิดกะประจำวัน','cash_shift',self.current_shift['id'])
        if not approval:return
        try:self.current_shift=close_shift(self.current_shift['id'],{m:v.get() for m,v in self.actual.items()},self.user,approval,self.shift_note.get());self.load_shift();self.load_shifts();print_shift_receipt(self.current_shift['id'])
        except Exception as e:messagebox.showerror("ปิดกะไม่ได้",str(e),parent=self)
    def print_shift(self):
        if self.current_shift and self.current_shift['status']=='closed':print_shift_receipt(self.current_shift['id'])
        else:messagebox.showwarning("ยังพิมพ์ไม่ได้","กรุณาปิดกะก่อน",parent=self)
    def load_shifts(self):
        self.shift_tree.delete(*self.shift_tree.get_children());start=(date.today()-timedelta(days=90)).isoformat();end=date.today().isoformat()
        for x in list_shifts(start,end):self.shift_tree.insert('', 'end',iid=str(x['id']),values=(format_thai_date(x['shift_date']),x['shift_no'],f"{x['opening_cash']:,.2f}",x['status'],x['opened_name'] or '-',x['closed_name'] or '-',x['approved_name'] or '-',format_thai_datetime(x['closed_at'])))
