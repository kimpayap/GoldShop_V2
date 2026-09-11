QR_PREFIX = "GOLDSHOP:ITEM:"
PAWN_QR_PREFIX = "GOLDSHOP:PAWN:"


def qr_payload(item_code):
    """QR เก็บเฉพาะรหัสสินค้า ส่วนราคา/น้ำหนักอ่านจากฐานข้อมูลล่าสุด"""
    code = str(item_code or "").strip().upper()
    if not code: raise ValueError("รหัสสินค้าว่าง")
    return QR_PREFIX + code


def item_code_from_qr(payload):
    text = str(payload or "").strip()
    if not text.startswith(QR_PREFIX): raise ValueError("QR Code นี้ไม่ใช่สินค้าของ GoldShop")
    code = text[len(QR_PREFIX):].strip().upper()
    if not code: raise ValueError("QR Code ไม่มีรหัสสินค้า")
    return code


def pawn_qr_payload(ticket_no):
    ticket = str(ticket_no or "").strip().upper()
    if not ticket: raise ValueError("เลขที่ตั๋วขายฝากว่าง")
    return PAWN_QR_PREFIX + ticket


def ticket_no_from_qr(payload):
    text = str(payload or "").strip()
    if not text.startswith(PAWN_QR_PREFIX): raise ValueError("QR Code นี้ไม่ใช่ใบขายฝากของ GoldShop")
    ticket = text[len(PAWN_QR_PREFIX):].strip().upper()
    if not ticket: raise ValueError("QR Code ไม่มีเลขที่ตั๋วขายฝาก")
    return ticket


def qr_data_uri(payload, box_size=5, border=2):
    """สร้าง QR เป็น PNG data URI สำหรับฝังในใบพิมพ์ HTML"""
    import base64
    import io
    import qrcode
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=int(box_size), border=int(border))
    qr.add_data(str(payload)); qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    stream = io.BytesIO(); image.save(stream, format="PNG")
    return "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode("ascii")
