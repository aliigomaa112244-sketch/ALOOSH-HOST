from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import uvicorn

app = FastAPI()

# إعداد القوالب للبحث في المجلد الحالي
templates = Jinja2Templates(directory=".")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        # محاولة عرض الصفحة الأساسية
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        return HTMLResponse(content=f"Error: {str(e)}", status_code=500)

# روابط الـ API التي يطلبها ملف index.html لمنع الأخطاء
@app.post("/api/login")
async def login():
    return {"success": True, "message": "تم تسجيل الدخول بنجاح", "redirect": "/dashboard"}

@app.post("/api/register")
async def register():
    return {"success": True, "message": "تم إنشاء الحساب بنجاح"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
