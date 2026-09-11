import re
import time
import urllib.request
from datetime import datetime

from bs4 import BeautifulSoup

from database.database import get_connection
from modules.thai_datetime import format_thai_date


GOLD_PRICE_URL = "https://newgta.goldtraders.or.th/dailyprices_print"

REQUEST_TIMEOUT = 15


def fetch_gold_page():
    """
    ดาวน์โหลดหน้าเว็บราคาทองจากสมาคมค้าทองคำ
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Cache-Control": "no-cache, no-store, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
        "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
    }

    # ใส่ค่าที่ไม่ซ้ำในทุก request เพื่อไม่ให้ proxy/CDN ส่งหน้าเก่าจาก cache
    separator = "&" if "?" in GOLD_PRICE_URL else "?"
    request_url = (
        f"{GOLD_PRICE_URL}{separator}"
        f"_={time.time_ns()}"
    )

    request = urllib.request.Request(
        request_url,
        headers=headers
    )

    with urllib.request.urlopen(
        request,
        timeout=REQUEST_TIMEOUT
    ) as response:

        return response.read().decode(
            "utf-8",
            errors="ignore"
        )


def clean_number(value):
    """
    แปลงข้อความตัวเลข เช่น
    68,750.00 -> 68750.0
    """

    if value is None:
        return None

    value = value.strip()

    value = value.replace(
        ",",
        ""
    )

    value = value.replace(
        "บาท",
        ""
    )

    value = value.strip()

    if not value:
        return None

    try:
        return float(value)

    except ValueError:
        return None


def parse_gold_price(html):
    """
    อ่านข้อมูลราคาทองจากหน้า dailyprices_print
    ของสมาคมค้าทองคำ
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    tables = soup.find_all("table")

    target_table = None

    # ตารางที่ 2 คือ ตารางประวัติราคาทอง
    for table in tables:

        rows = table.find_all("tr")

        if len(rows) < 3:
            continue

        table_text = table.get_text(
            " ",
            strip=True
        )

        if (
            "วันที่" in table_text
            and "เวลา" in table_text
            and "ครั้งที่" in table_text
            and "GOLD SPOT" in table_text
        ):
            target_table = table
            break

    if target_table is None:

        raise ValueError(
            "ไม่พบตารางประวัติราคาทอง"
        )

    rows = target_table.find_all("tr")

    # --------------------------------
    # แถวข้อมูลจริง
    # --------------------------------

    data_rows = []

    for row in rows:

        cells = row.find_all(
            ["td", "th"]
        )

        values = [
            cell.get_text(
                " ",
                strip=True
            )
            for cell in cells
        ]

        # รูปแบบข้อมูลจริง:
        #
        # 0 วันที่
        # 1 เวลา
        # 2 ครั้งที่
        # 3 ทองแท่งซื้อเข้า
        # 4 ทองแท่งขายออก
        # 5 รูปพรรณซื้อเข้า
        # 6 รูปพรรณขายออก
        # 7 GOLD SPOT
        # 8 THB
        # 9 การปรับเปลี่ยน

        if len(values) >= 10:

            if re.match(
                r"\d{1,2}/\d{1,2}/\d{4}",
                values[0]
            ):

                if re.match(
                    r"\d{1,2}:\d{2}",
                    values[1]
                ):

                    match = re.search(r"\d+", values[2].replace(",", ""))

                    if match:
                        data_rows.append((values, int(match.group())))

    if not data_rows:

        raise ValueError(
            "ไม่พบแถวราคาทองล่าสุด"
        )

    def date_key(date_text):
        try:
            return datetime.strptime(date_text, "%d/%m/%Y").date()
        except ValueError:
            return datetime.min.date()

    def time_key(time_text):
        match = re.search(r"(\d{1,2}):(\d{2})", time_text)
        if not match:
            return (-1, -1)
        return (int(match.group(1)), int(match.group(2)))

    # หน้าเว็บอาจมีหลายวันและเรียงแถวจากเก่าไปใหม่หรือใหม่ไปเก่าได้
    # จึงเลือกวันที่สูงสุดก่อน แล้วเลือกเลขประกาศสูงสุดของวันนั้นเสมอ
    latest_date = max(date_key(row[0][0]) for row in data_rows)
    latest_rows = [
        row for row in data_rows
        if date_key(row[0][0]) == latest_date
    ]
    data_row, parsed_announcement_no = max(
        latest_rows,
        key=lambda row: (row[1], time_key(row[0][1]))
    )

    print()
    print("=" * 60)
    print("ข้อมูลจากสมาคมค้าทองคำ")
    print("=" * 60)

    for index, value in enumerate(data_row):

        print(
            f"{index}: {value}"
        )

    print("=" * 60)

    # --------------------------------
    # แยกข้อมูล
    # --------------------------------

    price_date = data_row[0]

    price_time = data_row[1]

    announcement_no = parsed_announcement_no

    gold_bar_buy = clean_number(
        data_row[3]
    )

    gold_bar_sell = clean_number(
        data_row[4]
    )

    gold_jewelry_tax = clean_number(
        data_row[5]
    )

    gold_jewelry_sell = clean_number(
        data_row[6]
    )

    gold_spot = clean_number(
        data_row[7]
    )

    thai_baht = clean_number(
        data_row[8]
    )

    price_change = clean_number(
        data_row[9]
    )

    # --------------------------------
    # ตรวจสอบข้อมูล
    # --------------------------------

    if gold_bar_buy is None:

        raise ValueError(
            "ไม่สามารถอ่านราคาทองแท่งรับซื้อได้"
        )

    if gold_bar_sell is None:

        raise ValueError(
            "ไม่สามารถอ่านราคาทองแท่งขายออกได้"
        )

    if gold_bar_buy <= 0:

        raise ValueError(
            "ราคาทองแท่งรับซื้อต้องมากกว่า 0"
        )

    if gold_bar_sell <= 0:

        raise ValueError(
            "ราคาทองแท่งขายออกต้องมากกว่า 0"
        )

    return {

        "price_date": price_date,

        "price_time": price_time,

        "announcement_no": announcement_no,

        "gold_bar_buy": gold_bar_buy,

        "gold_bar_sell": gold_bar_sell,

        "gold_jewelry_tax": gold_jewelry_tax,

        "gold_jewelry_sell": gold_jewelry_sell,

        "gold_spot": gold_spot,

        "thai_baht": thai_baht,

        "price_change": price_change,

        "source": GOLD_PRICE_URL
    }


def save_gold_price(data):
    """
    บันทึกราคาทองลง SQLite
    และป้องกันข้อมูลซ้ำ
    """

    with get_connection() as conn:

        # ล็อกช่วงตรวจและบันทึกไว้ด้วยกัน เพื่อกันการ refresh สองชุด
        # ตรวจไม่เจอพร้อมกันแล้ว INSERT ข้อมูลประกาศเดียวกันซ้ำ
        conn.execute("BEGIN IMMEDIATE")

        existing = conn.execute("""
            SELECT id
            FROM gold_prices
            WHERE price_date = ?
              AND price_time = ?
              AND announcement_no = ?
        """, (
            data["price_date"],
            data["price_time"],
            data["announcement_no"]
        )).fetchone()

        if existing:

            return existing["id"], False

        cursor = conn.execute("""
            INSERT INTO gold_prices (
                price_date,
                price_time,
                announcement_no,

                gold_bar_buy,
                gold_bar_sell,

                gold_jewelry_tax,
                gold_jewelry_sell,

                gold_spot,
                thai_baht,

                price_change,

                source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["price_date"],
            data["price_time"],
            data["announcement_no"],

            data["gold_bar_buy"],
            data["gold_bar_sell"],

            data["gold_jewelry_tax"],
            data["gold_jewelry_sell"],

            data["gold_spot"],
            data["thai_baht"],

            data["price_change"],

            data["source"]
        ))

        conn.commit()

        return cursor.lastrowid, True


def get_latest_gold_price():

    with get_connection() as conn:

        row = conn.execute("""
            SELECT *
            FROM gold_prices
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        if row:
            return dict(row)

        return None


def update_gold_price():

    try:

        html = fetch_gold_page()

        data = parse_gold_price(
            html
        )

        record_id, inserted = save_gold_price(
            data
        )

        return {
            "success": True,
            "inserted": inserted,
            "data": data,
            "id": record_id
        }

    except Exception as error:

        latest = get_latest_gold_price()

        return {
            "success": False,
            "inserted": False,
            "data": latest,
            "error": str(error)
        }


if __name__ == "__main__":

    print()
    print("กำลังดึงราคาทองจากสมาคมค้าทองคำ...")
    print()

    result = update_gold_price()

    if result["success"]:

        print()
        print("✅ ดึงราคาทองสำเร็จ")
        print()

        data = result["data"]

        print(
            "วันที่:",
            format_thai_date(data["price_date"])
        )

        print(
            "เวลา:",
            data["price_time"]
        )

        print(
            "ครั้งที่:",
            data["announcement_no"]
        )

        print(
            "ทองแท่งรับซื้อ:",
            data["gold_bar_buy"]
        )

        print(
            "ทองแท่งขายออก:",
            data["gold_bar_sell"]
        )

        print(
            "ทองรูปพรรณ:",
            data["gold_jewelry_sell"]
        )

        if result["inserted"]:
            print()
            print("บันทึกข้อมูลใหม่ลง SQLite แล้ว")

        else:
            print()
            print("ข้อมูลนี้มีอยู่ใน SQLite แล้ว")

    else:

        print()
        print("❌ ดึงราคาทองไม่สำเร็จ")
        print(
            "สาเหตุ:",
            result["error"]
        )

        if result["data"]:

            print()
            print("ใช้ราคาล่าสุดจาก SQLite")

            print(
                "ทองแท่งขายออก:",
                result["data"]["gold_bar_sell"]
            )
