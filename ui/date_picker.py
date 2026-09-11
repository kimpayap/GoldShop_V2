import calendar
from datetime import date
import tkinter as tk
from tkinter import ttk

from modules.thai_datetime import THAI_MONTHS, format_thai_date, parse_thai_date_to_iso


class ThaiCalendarDialog(tk.Toplevel):
    def __init__(self, parent, variable, title="เลือกวันที่"):
        super().__init__(parent)
        self.variable=variable;self.title(title);self.transient(parent);self.grab_set();self.resizable(False,False)
        try:selected=date.fromisoformat(parse_thai_date_to_iso(variable.get()))
        except Exception:selected=date.today()
        self.year=selected.year;self.month=selected.month
        self.header=ttk.Frame(self,padding=8);self.header.pack(fill="x")
        ttk.Button(self.header,text="◀",command=lambda:self.change_month(-1)).pack(side="left")
        self.month_label=ttk.Label(self.header,font=("Arial",16,"bold"));self.month_label.pack(side="left",expand=True,padx=18)
        ttk.Button(self.header,text="▶",command=lambda:self.change_month(1)).pack(side="right")
        self.days=ttk.Frame(self,padding=8);self.days.pack()
        footer=ttk.Frame(self,padding=8);footer.pack(fill="x")
        ttk.Button(footer,text="วันนี้",command=lambda:self.choose(date.today().day,date.today().month,date.today().year)).pack(side="left")
        ttk.Button(footer,text="ยกเลิก",command=self.destroy).pack(side="right")
        self.render();self.bind("<Escape>",lambda e:self.destroy())

    def change_month(self,delta):
        index=self.year*12+self.month-1+delta;self.year=index//12;self.month=index%12+1;self.render()

    def render(self):
        for widget in self.days.winfo_children():widget.destroy()
        self.month_label.configure(text=f"{THAI_MONTHS[self.month]} {self.year+543}")
        for col,name in enumerate(("จ","อ","พ","พฤ","ศ","ส","อา")):
            ttk.Label(self.days,text=name,font=("Arial",12,"bold"),anchor="center",width=5).grid(row=0,column=col,padx=2,pady=2)
        for row,week in enumerate(calendar.monthcalendar(self.year,self.month),1):
            for col,day in enumerate(week):
                if day:
                    ttk.Button(self.days,text=str(day),width=5,command=lambda d=day:self.choose(d,self.month,self.year)).grid(row=row,column=col,padx=2,pady=2,ipady=5)

    def choose(self,day,month,year):
        self.variable.set(format_thai_date(date(year,month,day)));self.destroy()


def open_thai_calendar(parent,variable,title="เลือกวันที่"):
    dialog=ThaiCalendarDialog(parent,variable,title);parent.wait_window(dialog)
