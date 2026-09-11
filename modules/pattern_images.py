from pathlib import Path
import os
import shutil
import sys

from database.database import get_connection
from modules.pawn import ensure_pawn_schema


ALLOWED_EXTENSIONS={".jpg",".jpeg",".png",".webp",".gif",".bmp"}


def _image_folder():
    if getattr(sys,"frozen",False):
        if sys.platform=="darwin":root=Path.home()/"Library"/"Application Support"/"GoldShop"
        elif os.name=="nt":root=Path(os.environ.get("APPDATA",Path.home()))/"GoldShop"
        else:root=Path.home()/".local"/"share"/"GoldShop"
    else:root=Path(__file__).resolve().parent.parent/"data"
    folder=root/"pattern_images";folder.mkdir(parents=True,exist_ok=True);return folder


def save_pattern_image(detail_id,source_path):
    ensure_pawn_schema();source=Path(source_path)
    if not source.is_file():raise ValueError("ไม่พบไฟล์รูปที่เลือก")
    suffix=source.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:raise ValueError("รองรับไฟล์ JPG, PNG, WEBP, GIF และ BMP")
    target=_image_folder()/f"gold_detail_{int(detail_id)}{suffix}"
    with get_connection() as conn:
        row=conn.execute("SELECT image_path FROM gold_details WHERE id=?",(int(detail_id),)).fetchone()
        if not row:raise ValueError("ไม่พบลายทองที่ต้องการเพิ่มรูป")
        old=Path(row["image_path"]) if row["image_path"] else None
        shutil.copy2(source,target)
        conn.execute("UPDATE gold_details SET image_path=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(str(target),int(detail_id)))
        conn.commit()
    if old and old!=target and old.parent==_image_folder() and old.exists():
        try:old.unlink()
        except OSError:pass
    return str(target)


def remove_pattern_image(detail_id):
    ensure_pawn_schema()
    with get_connection() as conn:
        row=conn.execute("SELECT image_path FROM gold_details WHERE id=?",(int(detail_id),)).fetchone()
        if not row:raise ValueError("ไม่พบลายทอง")
        path=Path(row["image_path"]) if row["image_path"] else None
        conn.execute("UPDATE gold_details SET image_path=NULL,updated_at=CURRENT_TIMESTAMP WHERE id=?",(int(detail_id),));conn.commit()
    if path and path.parent==_image_folder() and path.exists():
        try:path.unlink()
        except OSError:pass
