def display_terms(value):
    """แปลงคำศัพท์เดิมเมื่อแสดงข้อมูลย้อนหลัง โดยไม่แก้คีย์/โครงสร้างฐานข้อมูล"""
    text="" if value is None else str(value)
    return text.replace("จำนำ","ขายฝาก").replace("ดอกเบี้ย","ผลตอบแทน")
