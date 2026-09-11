from pathlib import Path
import re
import time

from smartcard.System import readers
from smartcard.Exceptions import NoCardException


class ThaiIDCardError(Exception):
    pass


class ThaiIDCardReader:

    THAI_ID_AID = [
        0xA0, 0x00, 0x00, 0x00,
        0x54, 0x48, 0x00, 0x01
    ]

    # GoldShop_v1 root: modules/thai_id_card.py -> parent.parent
    BASE_DIR = Path(__file__).resolve().parent.parent
    PHOTO_DIR = BASE_DIR / "data" / "customer_photos"

    def __init__(self):
        self.reader = None
        self.connection = None

    def find_reader(self):
        available_readers = readers()
        if not available_readers:
            raise ThaiIDCardError("ไม่พบเครื่องอ่าน Smart Card")
        self.reader = available_readers[0]
        return str(self.reader)

    def connect(self):
        if self.reader is None:
            self.find_reader()
        try:
            self.connection = self.reader.createConnection()
            self.connection.connect()
            return self.connection.getProtocol()
        except NoCardException:
            raise ThaiIDCardError("ไม่พบบัตรประชาชน กรุณาเสียบบัตร")
        except Exception as error:
            raise ThaiIDCardError(f"เชื่อมต่อบัตรไม่สำเร็จ: {error}")

    def transmit(self, apdu):
        if self.connection is None:
            raise ThaiIDCardError("ยังไม่ได้เชื่อมต่อบัตร")
        try:
            return self.connection.transmit(apdu)
        except Exception as error:
            raise ThaiIDCardError(f"ส่งคำสั่งไปยังบัตรไม่สำเร็จ: {error}")

    def get_response(self, length):
        return self.transmit([0x00, 0xC0, 0x00, 0x00, length])

    def select_thai_id_application(self):
        apdu = [0x00, 0xA4, 0x04, 0x00, 0x08, *self.THAI_ID_AID]
        data, sw1, sw2 = self.transmit(apdu)
        if sw1 == 0x61:
            data, sw1, sw2 = self.get_response(sw2)
        if sw1 != 0x90 or sw2 != 0x00:
            raise ThaiIDCardError(
                "เลือก Thai ID Application ไม่สำเร็จ "
                f"Status: {sw1:02X}{sw2:02X}"
            )
        return data

    @staticmethod
    def _clean_card_text(value):
        """Thai ID text fields use # as a field separator/padding marker."""
        if not value:
            return ""
        value = value.replace("\x00", "")
        value = value.replace("#", " ")
        # Some cards contain repeated separators represented by spaces.
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    @staticmethod
    def _clean_date(value):
        value = (value or "").strip()
        if len(value) == 8 and value.isdigit():
            # Card stores Buddhist year as YYYYMMDD.
            return f"{value[6:8]}/{value[4:6]}/{value[0:4]}"
        return value

    def read_field(self, apdu, encoding="tis-620"):
        data, sw1, sw2 = self.transmit(apdu)
        if sw1 == 0x61:
            data, sw1, sw2 = self.get_response(sw2)
        if sw1 != 0x90 or sw2 != 0x00:
            raise ThaiIDCardError(
                "อ่านข้อมูลไม่สำเร็จ "
                f"Status: {sw1:02X}{sw2:02X}"
            )

        raw = bytes(data).rstrip(b"\x00 ")
        try:
            text = raw.decode(encoding, errors="replace")
        except Exception:
            text = raw.decode("utf-8", errors="replace")
        return self._clean_card_text(text)

    def read_citizen_id(self):
        apdu = [0x80, 0xB0, 0x00, 0x04, 0x02, 0x00, 0x0D]
        value = self.read_field(apdu, encoding="ascii").replace(" ", "")
        if len(value) != 13 or not value.isdigit():
            raise ThaiIDCardError("CID ที่อ่านได้ไม่ถูกต้อง")
        return value

    def read_thai_name(self):
        return self.read_field([
            0x80, 0xB0, 0x00, 0x11, 0x02, 0x00, 0x64
        ])

    def read_english_name(self):
        return self.read_field([
            0x80, 0xB0, 0x00, 0x75, 0x02, 0x00, 0x64
        ], encoding="ascii")

    def read_birth_date(self):
        return self._clean_date(self.read_field([
            0x80, 0xB0, 0x00, 0xD9, 0x02, 0x00, 0x08
        ], encoding="ascii"))

    def read_gender(self):
        value = self.read_field([
            0x80, 0xB0, 0x00, 0xE1, 0x02, 0x00, 0x01
        ], encoding="ascii")
        if value == "1":
            return "ชาย"
        if value == "2":
            return "หญิง"
        return value

    def read_issuer(self):
        return self.read_field([
            0x80, 0xB0, 0x00, 0xF6, 0x02, 0x00, 0x64
        ])

    def read_issue_date(self):
        return self._clean_date(self.read_field([
            0x80, 0xB0, 0x01, 0x67, 0x02, 0x00, 0x08
        ], encoding="ascii"))

    def read_expire_date(self):
        return self._clean_date(self.read_field([
            0x80, 0xB0, 0x01, 0x6F, 0x02, 0x00, 0x08
        ], encoding="ascii"))

    def read_address(self):
        return self.read_field([
            0x80, 0xB0, 0x15, 0x79, 0x02, 0x00, 0x64
        ])

    def read_photo(self):
        """อ่านรูปจาก Thai ID card ครบทั้ง 20 segments.

        รูปบนบัตรถูกแบ่งเป็น 20 ชุด ชุดละไม่เกิน 255 bytes
        โดย P1 = 1..20 และ P2 = 0x7C - segment.
        การอ่านเพียง 15 ชุดจะได้ประมาณ 3,825 bytes ซึ่งเป็นไฟล์ JPEG
        ที่ยังไม่ครบและ Pillow จะเปิดไม่ได้ (OSError)
        """
        photo_data = bytearray()

        # Standard Thai ID photo APDU: 20 chunks.
        for segment in range(1, 21):
            p1 = segment
            p2 = 0x7C - segment
            apdu = [0x80, 0xB0, p1, p2, 0x02, 0x00, 0xFF]

            print(f"กำลังอ่านรูป segment {segment}/20...")
            data, sw1, sw2 = self.transmit(apdu)

            if sw1 == 0x61:
                data, sw1, sw2 = self.get_response(sw2)

            if sw1 != 0x90 or sw2 != 0x00:
                raise ThaiIDCardError(
                    f"อ่านรูป segment {segment} ไม่สำเร็จ "
                    f"Status: {sw1:02X}{sw2:02X}"
                )

            photo_data.extend(data)
            print(f"  ได้ข้อมูล {len(data)} bytes")

        if not photo_data:
            raise ThaiIDCardError("ไม่พบข้อมูลรูปจากบัตร")

        raw = bytes(photo_data)

        # ตัดเฉพาะช่วง JPEG จริงออกมา เพื่อกัน padding จาก card reader
        # และทำให้ไฟล์ที่ส่งต่อให้ GUI เป็น JPEG ที่เปิดได้
        start = raw.find(b"\xFF\xD8")
        end = raw.rfind(b"\xFF\xD9")

        if start < 0 or end < 0 or end <= start:
            raise ThaiIDCardError(
                f"ข้อมูลรูปจากบัตรไม่ใช่ JPEG ที่สมบูรณ์ ({len(raw)} bytes)"
            )

        jpeg = raw[start:end + 2]
        print(f"JPEG photo: {len(jpeg)} bytes")
        return jpeg

    def save_photo(self, photo_data, citizen_id):
        self.PHOTO_DIR.mkdir(parents=True, exist_ok=True)
        photo_path = self.PHOTO_DIR / f"{citizen_id}.jpg"
        photo_path.write_bytes(photo_data)
        return str(photo_path)

    def read_card_once(self):
        result = {}
        try:
            result["reader"] = self.find_reader()
            result["protocol"] = self.connect()
            self.select_thai_id_application()
            print("Application: OK")

            result["citizen_id"] = self.read_citizen_id(); print("CID: OK")
            result["thai_name"] = self.read_thai_name(); print("Thai name: OK")
            result["english_name"] = self.read_english_name(); print("English name: OK")
            result["birth_date"] = self.read_birth_date(); print("Birth date: OK")
            result["gender"] = self.read_gender(); print("Gender: OK")
            result["issuer"] = self.read_issuer(); print("Issuer: OK")
            result["issue_date"] = self.read_issue_date(); print("Issue date: OK")
            result["expire_date"] = self.read_expire_date(); print("Expire date: OK")
            result["address"] = self.read_address(); print("Address: OK")

            photo_data = self.read_photo()
            print(f"Photo: {len(photo_data)} bytes")
            result["photo_path"] = self.save_photo(photo_data, result["citizen_id"])
            print("Photo: OK")
            result["success"] = True
            return result
        finally:
            self.disconnect()

    def disconnect(self):
        if self.connection is not None:
            try:
                self.connection.disconnect()
            except Exception:
                pass
            self.connection = None


def test_read_all():
    print("\n" + "=" * 60)
    print("THAI ID CARD - FULL DATA TEST")
    print("=" * 60)
    print("\nกรุณาเสียบบัตรประชาชน...\n")
    time.sleep(2)
    reader = ThaiIDCardReader()
    try:
        result = reader.read_card_once()
        print("\n" + "=" * 60)
        print("อ่านข้อมูลสำเร็จ")
        print("=" * 60)
        cid = result["citizen_id"]
        print("CID:", cid[:3] + "**********")
        for key, label in [
            ("thai_name", "Thai Name"), ("english_name", "English Name"),
            ("birth_date", "Birth Date"), ("gender", "Gender"),
            ("issuer", "Issuer"), ("issue_date", "Issue Date"),
            ("expire_date", "Expire Date"), ("address", "Address"),
            ("photo_path", "Photo")
        ]:
            print(f"{label}:", result.get(key, ""))
        print("\n✅ อ่านข้อมูลบัตรครบแล้ว")
        print("กรุณาถอดบัตรประชาชนออก")
    except ThaiIDCardError as error:
        print("\n❌", error)
    except Exception as error:
        print("\n❌ Unexpected Error:", type(error).__name__, error)
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_read_all()
