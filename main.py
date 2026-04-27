from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import os
import uvicorn

app = FastAPI()

# عرض الصفحة الجديدة
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# روابط الـ API التي يحتاجها الكود الجديد
@app.get("/api/current_user")
async def get_user():
    # نرسل بيانات تجريبية ليفتح الموقع لوحة التحكم مباشرة
    return {"username": "ALOOSH", "is_admin": False}

@app.get("/api/user_plan")
async def get_plan():
    return {"plan": "free", "status": "active"}

@app.get("/api/stats")
async def get_stats():
    return {"cpu": 12, "ram": 45, "storage": 30}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
