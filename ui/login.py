import tkinter as tk
from tkinter import ttk, messagebox

from database.database import init_db
from modules.auth import login, login_lock_remaining
from ui.dashboard import Dashboard


class LoginWindow(tk.Tk):

    def __init__(self):
        super().__init__()

        # สร้างฐานข้อมูลก่อนเปิดโปรแกรม
        init_db()

        self.title("Gold Shop System V1")
        self.geometry("450x330")
        self.resizable(False, False)
        self.configure(bg="#0b1320")

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background="#0b1320")
        style.configure("TLabel", background="#0b1320", foreground="#e8edf5")
        style.configure("LoginTitle.TLabel", background="#0b1320", foreground="#f5c451", font=("Arial", 24, "bold"))
        style.configure("TEntry", fieldbackground="#101c2b", foreground="#ffffff", insertcolor="#ffffff", bordercolor="#b88924", padding=7)
        style.configure("Login.TButton", background="#b88924", foreground="#ffffff", font=("Arial", 14, "bold"), padding=10)
        style.map("Login.TButton", background=[("active", "#d6a936")])

        self.create_widgets()

    def create_widgets(self):

        # =========================
        # หัวโปรแกรม
        # =========================

        title = ttk.Label(
            self,
            text="GOLD SHOP SYSTEM",
            style="LoginTitle.TLabel"
        )

        title.pack(pady=(35, 5))

        subtitle = ttk.Label(
            self,
            text="ระบบจัดการร้านทองและขายฝาก"
        )

        subtitle.pack(pady=(0, 25))

        # =========================
        # Frame Login
        # =========================

        frame = ttk.Frame(self)

        frame.pack(padx=40, fill="x")

        # Username

        ttk.Label(
            frame,
            text="ชื่อผู้ใช้"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=8
        )

        self.username_entry = ttk.Entry(frame)

        self.username_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=8
        )

        # Password

        ttk.Label(
            frame,
            text="รหัสผ่าน"
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=8
        )

        self.password_entry = ttk.Entry(
            frame,
            show="*"
        )

        self.password_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=8
        )

        frame.columnconfigure(1, weight=1)

        # =========================
        # ปุ่ม Login
        # =========================

        login_button = ttk.Button(
            self,
            text="เข้าสู่ระบบ",
            command=self.do_login,
            style="Login.TButton"
        )

        login_button.pack(
            fill="x",
            padx=40,
            pady=25
        )

        # =========================
        # ข้อมูล Login เริ่มต้น
        # =========================

        ttk.Label(
            self,
            text="Username: admin   Password: admin123",
            foreground="gray"
        ).pack()

        # กด Enter เพื่อ Login

        self.bind(
            "<Return>",
            lambda event: self.do_login()
        )

        self.username_entry.focus()

    def do_login(self):

        username = self.username_entry.get()
        password = self.password_entry.get()

        # ตรวจสอบว่ากรอกครบหรือไม่

        if not username or not password:

            messagebox.showwarning(
                "ข้อมูลไม่ครบ",
                "กรุณากรอกชื่อผู้ใช้และรหัสผ่าน"
            )

            return

        # ตรวจสอบ Login

        user = login(
            username,
            password
        )

        if not user:

            remaining = login_lock_remaining(username)

            messagebox.showerror(
                "เข้าสู่ระบบไม่สำเร็จ",
                ("บัญชีถูกพักการเข้าสู่ระบบ 15 นาที เนื่องจากกรอกรหัสผิดครบ 5 ครั้ง"
                 if remaining == 0 else f"ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง\nเหลือโอกาสอีก {remaining} ครั้ง")
            )

            self.password_entry.delete(
                0,
                tk.END
            )

            self.password_entry.focus()

            return

        # Login สำเร็จ

        self.destroy()

        Dashboard(user).mainloop()
