GoldShop - การติดตั้ง

macOS Apple Silicon
1. แตกไฟล์ GoldShop_macOS_AppleSilicon.zip
2. ลาก GoldShop.app ไปไว้ใน Applications
3. หาก macOS เตือนในครั้งแรก ให้คลิกขวาที่แอป เลือก Open แล้วกด Open อีกครั้ง

Windows 10/11 64-bit
1. เปิด GoldShop_Setup_Windows.exe
2. ทำตามขั้นตอนของตัวติดตั้ง
3. เปิด GoldShop จาก Desktop หรือ Start Menu

ข้อมูลโปรแกรม
- macOS: ~/Library/Application Support/GoldShop/gold_shop.db
- Windows: %APPDATA%\GoldShop\gold_shop.db
- การติดตั้งหรืออัปเดตโปรแกรมจะไม่เขียนทับฐานข้อมูลที่มีอยู่

บัญชีเริ่มต้นของฐานข้อมูลตัวอย่าง
Username: admin
Password: admin123
กรุณาเปลี่ยนรหัสผ่านก่อนใช้งานจริง

การสร้างแพ็กเกจใหม่จาก Source
- macOS: เปิด Terminal ในโฟลเดอร์โปรแกรมแล้วรัน ./build_macos.sh
- Windows: ติดตั้ง Python 3.12 แบบ 64-bit แล้วดับเบิลคลิก build_windows.bat
- หากติดตั้ง Inno Setup 6 ไว้ Windows จะสร้างไฟล์ Setup ให้อัตโนมัติ
