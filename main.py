from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os
import uvicorn

app = FastAPI()

# قراءة ملف الـ HTML مباشرة كصيغة نصية لتجنب أخطاء نظام القوالب
def get_html_content():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/", response_class=HTMLResponse)
async def home():
    try:
        content = get_html_content()
        return HTMLResponse(content=content)
    except Exception as e:
        return HTMLResponse(content=f"حدث خطأ أثناء قراءة الملف: {str(e)}", status_code=500)

@app.post("/api/login")
async def login():
    return {"success": True, "message": "تم تسجيل الدخول بنجاح"}

@app.post("/api/register")
async def register():
    return {"success": True, "message": "تم إنشاء الحساب بنجاح"}

@app.get("/api/current_user")
async def current_user():
    return {"success": False}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
