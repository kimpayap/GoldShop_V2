
import tkinter as tk
from tkinter import ttk, messagebox

ADMIN_ROLES = {"admin", "manager", "owner"}

def is_admin(user):
    try:
        from modules.system_controls import has_permission
        return has_permission(user,"settings")
    except Exception:return str((user or {}).get("role", "")).lower() in ADMIN_ROLES

def require_admin(parent, user, action="การตั้งค่านี้"):
    if not is_admin(user):
        messagebox.showwarning("ไม่มีสิทธิ์", f"{action} ต้องใช้สิทธิ์ผู้ดูแลระบบ (Admin)")
        return False
    return True

class TouchKeypad(tk.Toplevel):
    def __init__(self, parent, variable, title="แป้นตัวเลข"):
        super().__init__(parent)
        self.variable = variable
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        frame = ttk.Frame(self, padding=12)
        frame.pack()
        ttk.Entry(frame, textvariable=variable, font=("Arial",26),
                  justify="right", width=12).grid(row=0,column=0,columnspan=3,pady=8)
        keys=(("7","8","9"),("4","5","6"),("1","2","3"),(".","0","⌫"))
        for r,row in enumerate(keys,1):
            for c,key in enumerate(row):
                ttk.Button(frame,text=key,width=7,
                           command=lambda k=key:self.press(k)).grid(
                           row=r,column=c,padx=4,pady=4,ipadx=10,ipady=14)
        ttk.Button(frame,text="ล้าง",command=lambda:self.variable.set("")).grid(row=5,column=0,sticky="ew",pady=8,ipady=10)
        ttk.Button(frame,text="✓ ตกลง",command=self.destroy).grid(row=5,column=1,columnspan=2,sticky="ew",pady=8,ipady=10)
    def press(self,key):
        v=self.variable.get()
        if key=="⌫": self.variable.set(v[:-1])
        elif key=="." and "." not in v: self.variable.set(v+".")
        elif key not in (".","⌫"): self.variable.set(v+key)
