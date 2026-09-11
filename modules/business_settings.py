from database.database import get_connection


DEFAULTS = {
    "business_name": "ร้านทอง",
    "business_address": "",
    "business_phone": "",
    "business_tax_id": "",
    "receipt_footer": "ขอบคุณที่ใช้บริการ",
    "receipt_paper": "9x5.5",
}


def ensure_business_settings():
    with get_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS app_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        for key, value in DEFAULTS.items():
            conn.execute("INSERT OR IGNORE INTO app_settings(setting_key,setting_value) VALUES (?,?)", (key, value))
        # ปรับฐานข้อมูลรุ่นเดิมให้เริ่มใช้กระดาษต่อเนื่อง 9x5.5 นิ้วเพียงครั้งเดียว
        migrated = conn.execute("SELECT 1 FROM app_settings WHERE setting_key='receipt_paper_default_9x5_5'").fetchone()
        if not migrated:
            conn.execute("UPDATE app_settings SET setting_value='9x5.5',updated_at=CURRENT_TIMESTAMP WHERE setting_key='receipt_paper'")
            conn.execute("INSERT INTO app_settings(setting_key,setting_value) VALUES ('receipt_paper_default_9x5_5','1')")
        conn.commit()


def get_business_settings():
    ensure_business_settings()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT setting_key,setting_value FROM app_settings WHERE setting_key IN (%s)" % ",".join("?" * len(DEFAULTS)),
            tuple(DEFAULTS),
        ).fetchall()
    values = dict(DEFAULTS)
    values.update({row["setting_key"]: row["setting_value"] for row in rows})
    if values["receipt_paper"] not in {"A4", "80mm", "9x5.5"}: values["receipt_paper"] = "9x5.5"
    return values


def save_business_settings(values):
    clean = {key: str(values.get(key, DEFAULTS[key]) or "").strip() for key in DEFAULTS}
    if not clean["business_name"]:
        raise ValueError("กรุณาระบุชื่อกิจการ")
    if clean["receipt_paper"] not in {"A4", "80mm", "9x5.5"}:
        raise ValueError("ขนาดกระดาษไม่ถูกต้อง")
    ensure_business_settings()
    with get_connection() as conn:
        for key, value in clean.items():
            conn.execute("""INSERT INTO app_settings(setting_key,setting_value,updated_at)
                VALUES (?,?,CURRENT_TIMESTAMP)
                ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value,
                updated_at=CURRENT_TIMESTAMP""", (key, value))
        conn.commit()
    return clean
