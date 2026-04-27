from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os

app = FastAPI()

# إعداد المجلدات
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    # عرض ملف index.html الذي أرسلته
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/login")
async def login(data: dict):
    # هنا تضع منطق تسجيل الدخول
    return {"success": True, "message": "تم تسجيل الدخول بنجاح"}

@app.post("/api/register")
async def register(data: dict):
    # هنا تضع منطق إنشاء الحساب
    return {"success": True, "message": "تم إنشاء الحساب بنجاح"}

# تشغيل السيرفر على المنفذ الذي تحدده Railway
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
