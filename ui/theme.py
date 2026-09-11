from tkinter import ttk
import re
from datetime import datetime

from database.database import get_connection


THEMES = {
    "modern": {
        "label": "แนวทันสมัย", "font": "Helvetica", "bg": "#eef2f7",
        "surface": "#ffffff", "primary": "#2563eb", "accent": "#0f766e",
        "text": "#172033", "muted": "#526070", "button_text": "#ffffff",
    },
    "bright": {
        "label": "แนวสดใส", "font": "Arial", "bg": "#fff8dc",
        "surface": "#ffffff", "primary": "#ff7a00", "accent": "#00a6a6",
        "text": "#3d2b1f", "muted": "#6f5a49", "button_text": "#ffffff",
    },
    "traditional": {
        "label": "แนวดั้งเดิม", "font": "Tahoma", "bg": "#f4ead5",
        "surface": "#fffaf0", "primary": "#8b4513", "accent": "#b8860b",
        "text": "#352419", "muted": "#6d5748", "button_text": "#ffffff",
    },
    "luxury": {
        "label": "แนวหรูหรา", "font": "Georgia", "bg": "#171717",
        "surface": "#242424", "primary": "#b88924", "accent": "#d6a936",
        "text": "#f5ead1", "muted": "#c9b98f", "button_text": "#111111",
    },
}


def ensure_theme_schema():
    with get_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS app_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("INSERT OR IGNORE INTO app_settings(setting_key,setting_value) VALUES ('theme','modern')")
        conn.commit()


def get_theme_key():
    ensure_theme_schema()
    with get_connection() as conn:
        row = conn.execute("SELECT setting_value FROM app_settings WHERE setting_key='theme'").fetchone()
    key = row["setting_value"] if row else "modern"
    return key if key in THEMES else "modern"


def save_theme(key):
    if key not in THEMES:
        raise ValueError("Theme ที่เลือกไม่ถูกต้อง")
    ensure_theme_schema()
    with get_connection() as conn:
        conn.execute("""INSERT INTO app_settings(setting_key,setting_value,updated_at)
            VALUES ('theme',?,CURRENT_TIMESTAMP)
            ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value,
            updated_at=CURRENT_TIMESTAMP""", (key,))
        conn.commit()


def apply_theme(window, key=None):
    key = key or get_theme_key()
    palette = THEMES.get(key, THEMES["modern"])
    style = ttk.Style(window)
    try: style.theme_use("clam")
    except Exception: pass
    density = responsive_factor(window)
    font = (palette["font"], 12)
    bold = (palette["font"], 12, "bold")
    style.configure(".", background=palette["bg"], foreground=palette["text"], font=font)
    style.configure("TFrame", background=palette["bg"])
    style.configure("TLabel", background=palette["bg"], foreground=palette["text"], font=font)
    style.configure("TLabelframe", background=palette["bg"], foreground=palette["text"])
    style.configure("TLabelframe.Label", background=palette["bg"], foreground=palette["text"], font=bold)
    style.configure("TButton", background=palette["primary"], foreground=palette["button_text"], font=bold, padding=(max(6,int(12*density)),max(4,int(9*density))))
    style.map("TButton", background=[("active", palette["accent"]), ("pressed", palette["accent"])])
    style.configure("TEntry", fieldbackground=palette["surface"], foreground=palette["text"], padding=max(3,int(6*density)))
    style.configure("TCombobox", fieldbackground=palette["surface"], foreground=palette["text"])
    style.configure("Treeview", background=palette["surface"], fieldbackground=palette["surface"], foreground=palette["text"], font=font, rowheight=max(24,int(34*density)))
    style.configure("Treeview.Heading", background=palette["primary"], foreground=palette["button_text"], font=bold)
    style.configure("TNotebook", background=palette["bg"])
    style.configure("TNotebook.Tab", background=palette["surface"], foreground=palette["text"], font=bold, padding=(max(8,int(14*density)),max(5,int(9*density))))
    style.map("TNotebook.Tab", background=[("selected", palette["accent"])], foreground=[("selected", palette["button_text"])])
    for name in ("Touch.TButton", "TouchPrimary.TButton", "Renew.TButton", "RenewPrimary.TButton", "Forfeit.TButton", "Danger.TButton", "Menu.TButton", "Login.TButton"):
        style.configure(name, background=palette["primary"], foreground=palette["button_text"], font=(palette["font"], 14, "bold"))
        style.map(name, background=[("active", palette["accent"]), ("pressed", palette["accent"])])
    style.configure("Selected.TButton", background=palette["accent"], foreground=palette["button_text"],
                    font=(palette["font"], 14, "bold"), relief="sunken", borderwidth=4)
    style.map("Selected.TButton", background=[("active", palette["accent"]), ("pressed", palette["accent"])])
    for name, size in (("Title.TLabel", 24), ("Touch.TLabel", 14), ("TouchValue.TLabel", 18), ("CardValue.TLabel", 22)):
        style.configure(name, background=palette["bg"], foreground=palette["text"], font=(palette["font"], size, "bold"))
    try: window.configure(bg=palette["bg"])
    except Exception: pass
    # Widget หลายจุดกำหนดขนาดฟอนต์เฉพาะไว้ ให้คงขนาดเดิมแต่เปลี่ยนตระกูล
    # ตาม Theme หลังจากหน้าสร้าง widget เสร็จแล้ว
    def refresh_widget_fonts(widget):
        try:
            options = widget.configure()
            if "font" in options:
                current = widget.cget("font")
                size, weight = 12, ""
                if isinstance(current, str) and current:
                    parts = widget.tk.splitlist(current)
                    if len(parts) > 1:
                        try: size = int(parts[1])
                        except Exception: pass
                    if len(parts) > 2: weight = parts[2]
                if isinstance(current, (tuple, list)) and len(current) > 1:
                    size = current[1]
                    if len(current) > 2: weight = current[2]
                widget.configure(font=(palette["font"], size, weight) if weight else (palette["font"], size))
        except Exception:
            pass
        try:
            for child in widget.winfo_children(): refresh_widget_fonts(child)
        except Exception:
            pass
    try: window.after_idle(lambda: refresh_widget_fonts(window))
    except Exception: pass
    install_treeview_sorting(window)
    return palette


THAI_MONTHS={"มกราคม":1,"กุมภาพันธ์":2,"มีนาคม":3,"เมษายน":4,"พฤษภาคม":5,"มิถุนายน":6,
             "กรกฎาคม":7,"สิงหาคม":8,"กันยายน":9,"ตุลาคม":10,"พฤศจิกายน":11,"ธันวาคม":12}

def _tree_sort_value(value):
    text=str(value or "").strip()
    match=re.search(r"(\d{1,2})\s+([ก-๙]+)\s+(\d{4})",text)
    if match and match.group(2) in THAI_MONTHS:
        return (0,datetime(int(match.group(3))-543,THAI_MONTHS[match.group(2)],int(match.group(1))).timestamp())
    cleaned=text.replace(",","").replace("บาท","").replace("%","").replace("วัน","").strip()
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?",cleaned):return (0,float(cleaned))
    return (1,text.casefold())

def install_treeview_sorting(window):
    """ดับเบิลคลิกหัวตารางเพื่อเรียง และสลับน้อย→มาก/มาก→น้อยทุกครั้ง"""
    try:
        root=window._root()
        if not getattr(root,"_goldshop_tree_sort_installed",False):
            root._goldshop_tree_sort_installed=True
            root.bind_class("Treeview","<Double-Button-1>",_sort_tree_heading,add="+")
        def attach(widget):
            if isinstance(widget,ttk.Treeview) and not getattr(widget,"_goldshop_sort_tag",None):
                # tag นี้อยู่ก่อน widget/class binding จึงทำงานได้แม้หน้าจอมีคำสั่ง double-click เดิม
                tag=f"GoldShopTreeSort{id(widget)}";widget._goldshop_sort_tag=tag
                widget.bind_class(tag,"<Double-Button-1>",_sort_tree_heading)
                widget.bindtags((tag,)+tuple(widget.bindtags()))
            for child in widget.winfo_children():attach(child)
        window.after_idle(lambda:attach(window))
    except Exception:pass

def _sort_tree_heading(event):
    tree=event.widget
    if not isinstance(tree,ttk.Treeview) or tree.identify_region(event.x,event.y)!="heading":return
    raw=tree.identify_column(event.x)
    try:
        index=int(raw[1:])-1
        displayed=tree["displaycolumns"]
        columns=tree["columns"]
        ordered=columns if displayed in ("#all",("#all",)) else displayed
        column=ordered[index]
    except (ValueError,IndexError,TypeError):return "break"
    state=getattr(tree,"_goldshop_sort_state",{});descending=not state.get(column,True)
    rows=list(tree.get_children(""));rows.sort(key=lambda iid:_tree_sort_value(tree.set(iid,column)),reverse=descending)
    for position,iid in enumerate(rows):tree.move(iid,"",position)
    state[column]=descending;tree._goldshop_sort_state=state
    return "break"


def responsive_factor(window):
    """คืนค่าความหนาแน่น UI ตามพื้นที่ใช้งานจริงของหน้าจอ"""
    try:
        width=int(window.winfo_screenwidth());height=int(window.winfo_screenheight())
    except Exception:return 1.0
    if height<760 or width<1100:return 0.72
    if height<900 or width<1350:return 0.80
    if height<1050 or width<1550:return 0.86
    if height<1200:return 0.93
    return 1.0


def open_fullscreen(window):
    """เปิดหน้าทำงานเต็มจอ รองรับทั้ง macOS/Windows/Linux"""
    # ลดสเกลทั้งโปรแกรมอัตโนมัติในจอที่มีพื้นที่แนวตั้งน้อย โดยเก็บค่าเริ่มต้น
    # เพียงครั้งเดียวเพื่อไม่ให้การเปิดหน้าต่างหลายครั้งย่อซ้ำสะสม
    try:
        root=window._root()
        if not hasattr(root,"_goldshop_base_scaling"):
            root._goldshop_base_scaling=float(window.tk.call("tk","scaling"))
            root._goldshop_auto_factor=responsive_factor(window)
            root._goldshop_ui_factor=root._goldshop_auto_factor
            def zoom(change=0,reset=False):
                root._goldshop_ui_factor=root._goldshop_auto_factor if reset else min(1.15,max(0.65,root._goldshop_ui_factor+change))
                window.tk.call("tk","scaling",root._goldshop_base_scaling*root._goldshop_ui_factor)
            for sequence in ("<Control-minus>","<Command-minus>"):root.bind_all(sequence,lambda _e:zoom(-0.05))
            for sequence in ("<Control-plus>","<Control-equal>","<Command-plus>","<Command-equal>"):root.bind_all(sequence,lambda _e:zoom(0.05))
            for sequence in ("<Control-0>","<Command-0>"):root.bind_all(sequence,lambda _e:zoom(reset=True))
        window.tk.call("tk","scaling",root._goldshop_base_scaling*root._goldshop_ui_factor)
    except Exception:pass
    try:
        window.attributes("-fullscreen", True)
    except Exception:
        try: window.state("zoomed")
        except Exception: pass


def back_to_dashboard(window):
    """ปิดหน้าลูกและคืนโฟกัส/โหมดเต็มจอให้ Dashboard โดยไม่ทิ้งจอดำ"""
    try: window.grab_release()
    except Exception: pass
    parent = getattr(window, "master", None)
    try: window.attributes("-fullscreen", False)
    except Exception: pass
    window.destroy()
    if parent and parent.winfo_exists():
        try: parent.deiconify()
        except Exception: pass
        def restore():
            try:
                open_fullscreen(parent)
                parent.lift()
                parent.focus_force()
                if hasattr(parent, "refresh_dashboard"):
                    parent.refresh_dashboard()
            except Exception:
                pass
        try: parent.after(80, restore)
        except Exception: restore()
