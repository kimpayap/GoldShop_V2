from datetime import date, datetime


THAI_MONTHS = (
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม",
    "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม",
    "พฤศจิกายน", "ธันวาคม",
)


def _parse_datetime(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    text = str(value).strip().replace("Z", "")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass

    for pattern in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return None


def format_thai_date(value, fallback="-"):
    """แสดงวันที่แบบ 01 มกราคม 2569 โดยไม่เปลี่ยนค่าที่เก็บในฐานข้อมูล"""
    parsed = _parse_datetime(value)
    if parsed is None:
        return fallback if value in (None, "") else str(value)
    buddhist_year = parsed.year if parsed.year >= 2400 else parsed.year + 543
    return f"{parsed.day:02d} {THAI_MONTHS[parsed.month]} {buddhist_year}"


def format_thai_datetime(value, include_seconds=False, fallback="-"):
    parsed = _parse_datetime(value)
    if parsed is None:
        return fallback if value in (None, "") else str(value)
    time_format = "%H:%M:%S" if include_seconds else "%H:%M"
    return f"{format_thai_date(parsed)} เวลา {parsed.strftime(time_format)} น."


def current_thai_datetime(include_seconds=True):
    return format_thai_datetime(datetime.now(), include_seconds=include_seconds)


def parse_thai_date_to_iso(value):
    """รับ 21/08/2569, 21 สิงหาคม 2569 หรือ ISO แล้วคืน YYYY-MM-DD"""
    if isinstance(value, (date, datetime)):
        parsed = value.date() if isinstance(value, datetime) else value
        return parsed.isoformat()
    text = str(value or "").strip()
    if not text: return ""
    try: return date.fromisoformat(text).isoformat()
    except ValueError: pass
    parts = text.replace("-", "/").split("/")
    if len(parts) == 3:
        day, month, year = map(int, parts)
        if year >= 2400: year -= 543
        return date(year, month, day).isoformat()
    words = text.split()
    if len(words) == 3 and words[1] in THAI_MONTHS:
        day, month, year = int(words[0]), THAI_MONTHS.index(words[1]), int(words[2])
        if year >= 2400: year -= 543
        return date(year, month, day).isoformat()
    raise ValueError("รูปแบบวันที่ไม่ถูกต้อง กรุณาใช้ เช่น 21 สิงหาคม 2569")
