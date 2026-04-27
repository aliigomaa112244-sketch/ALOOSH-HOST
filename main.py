from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import os
import uvicorn

app = FastAPI()

# صفحة الدخول الأساسية
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# صفحة لوحة التحكم (Dashboard) - دي اللي هتظهر بعد الدخول
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
        <head><title>Dashboard | ALOOSH HOST</title></head>
        <body style="background:#000; color:#FFD700; font-family:sans-serif; text-align:center; padding:50px;">
            <h1>مرحباً بك في لوحة تحكم ALOOSH HOST</h1>
            <p>هنا ستتمكن قريباً من رفع ملفات البايثون الخاصة بك.</p>
            <div style="border:2px dashed #FFD700; padding:20px; margin-top:20px;">
                <input type="file" id="fileInput">
                <button onclick="alert('جاري تجهيز نظام الرفع...')">رفع ملف</button>
            </div>
            <br><a href="/" style="color:#fff;">تسجيل الخروج</a>
        </body>
    </html>
    """

# تعديل رابط تسجيل الدخول ليحولك للـ Dashboard
@app.post("/api/login")
async def login(data: dict):
    # حالياً يقبل أي بريد وكلمة مرور للتجربة
    return {"success": True, "message": "تم الدخول بنجاح", "redirect": "/dashboard"}

@app.post("/api/register")
async def register(data: dict):
    return {"success": True, "message": "تم إنشاء الحساب بنجاح"}

@app.get("/api/current_user")
async def current_user():
    return {"success": False}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
