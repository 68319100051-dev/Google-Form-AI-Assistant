# 🤖 AI Google Form Auto-Filler (Clean Build)

เครื่องมือช่วยกรอก Google Form อัตโนมัติด้วย AI (Gemini / Groq / OpenRouter) รองรับการตรวจจับคำถามส่วนตัวและคำถามข้อสอบ แยกกันได้อย่างแม่นยำ

## ✨ ฟีเจอร์หลัก
- **AI-Powered**: ใช้ AI วิเคราะห์คำถามและเลือกคำตอบที่เหมาะสมที่สุด
- **Smart Classification**: แยกแยะ "คำถามส่วนตัว" (ต้องกรอกเอง) และ "รายวิชา/แบบสอบถาม" (AI ตอบให้)
- **Multi-Provider**: รองรับ Google Gemini, Groq (Llama 3), และ OpenRouter
- **Activity Log**: แสดงสถานะการทำงานแบบ Real-time (SSE)
- **Docker Ready**: พร้อมสำหรับการ Deploy บน Cloud (Render, Railway)

---

## 🚀 การติดตั้งและใช้งาน (Local)

1. **ติดตั้ง dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **ตั้งค่า API Key**:
   สร้างไฟล์ `.env` และเพิ่มคีย์ของคุณ:
   ```env
   GEMINI_API_KEY=your_key_here
   GROQ_API_KEY=your_key_here
   ```

3. **รันโปรแกรม**:
   ```bash
   python app.py
   ```
   เข้าใช้งานที่: `http://localhost:5000`

---

## 🌐 การนำขึ้น Cloud (Render / Railway)

1. **GitHub**: สร้าง Repository ใหม่และ Push โค้ดทั้งหมดขึ้นไป
2. **Deploy**:
   - เลือก Runtime เป็น **Docker**
   - ตั้งค่า Environment Variables (`GEMINI_API_KEY`, ฯลฯ)
   - ตั้งค่า Port เป็น **5000** (หรือตามที่ระบบกำหนด)

---
*จัดทำโดย Antigravity AI Assistant*
