from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import uvicorn

app = FastAPI()

# تأكد أن ملف index.html في نفس مكان ملف main.py
templates = Jinja2Templates(directory=".")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # التعديل هنا: نمرر السلف كـ "context" بشكل صحيح لتجنب خطأ unhashable type
    context = {"request": request}
    return templates.TemplateResponse("index.html", context)

@app.post("/api/login")
async def login():
    return {"success": True, "message": "تم تسجيل الدخول بنجاح"}

@app.post("/api/register")
async def register():
    return {"success": True, "message": "تم إنشاء الحساب بنجاح"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
