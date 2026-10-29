"""
Ayso · وسيط آمن  —  نسخة Enzonic / أي استضافة Python
================================================================
الوظيفة: المتصفح يكلّم هذا السيرفر، وهذا السيرفر يكلّم المزوّد.
المفتاح يعيش في متغيّر بيئة (Environment Variable) ولا يظهر أبداً في HTML.

التشغيل المحلي:
    export AYSO_KEY="sk-..."
    uvicorn app:app --host 0.0.0.0 --port 8000

على Enzonic: أمر التشغيل في اللوحة = uvicorn app:app --host 0.0.0.0 --port $PORT
"""

from __future__ import annotations

import os
import pathlib as _pl

# ── قارئ .env بسيط (بلا مكتبات) ──────────────────────────
# يسمح بضبط المفتاح من ملف .env بدل متغيّرات اللوحة
def _load_dotenv():
    f = _pl.Path(__file__).parent / ".env"
    if not f.exists():
        return
    try:
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    except Exception:
        pass

_load_dotenv()
import time
import json
import collections
import pathlib
from typing import Deque, Dict

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    StreamingResponse,
    Response,
)

from term import router as term_router

# ─────────────────────────── الإعدادات ───────────────────────────
VERSION   = "S1.0"
UPSTREAM  = os.getenv("AYSO_UPSTREAM", "https://anyrouter.dev/api/v1/chat/completions")
KEY       = os.getenv("AYSO_KEY", "").strip()
PASSWORD  = os.getenv("AYSO_PASS", "").strip()                 # فارغ = مفتوح للجميع
RPM       = int(os.getenv("AYSO_RPM", "30"))                   # طلبات / دقيقة / IP
DAILY     = int(os.getenv("AYSO_DAILY", "800"))                # طلبات / يوم / IP
MAX_TOK   = int(os.getenv("AYSO_MAXTOK", "4000"))              # سقف الرموز للطلب
ORIGIN    = os.getenv("AYSO_ORIGIN", "").strip()               # مثال: https://ayso.enzonic.cloud
TIMEOUT   = float(os.getenv("AYSO_TIMEOUT", "150"))
MODELS    = {m.strip() for m in os.getenv("AYSO_MODELS", "").split(",") if m.strip()}

ROOT = pathlib.Path(__file__).parent
INDEX = ROOT / "static" / "index.html"

# ─────────────────────────── الحدود ───────────────────────────
_hits: Dict[str, Deque[float]] = collections.defaultdict(collections.deque)
_daily: Dict[str, list] = collections.defaultdict(lambda: [0, time.time()])


def client_ip(req: Request) -> str:
    xff = req.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return req.client.host if req.client else "?"


def rate_ok(ip: str) -> tuple[bool, str, int]:
    now = time.time()

    # يومي
    day = _daily[ip]
    if now - day[1] > 86400:
        day[0], day[1] = 0, now
    if day[0] >= DAILY:
        return False, "تجاوزت الحدّ اليومي — جرّب بكرة", 429

    # دقيقة
    dq = _hits[ip]
    while dq and now - dq[0] > 60:
        dq.popleft()
    if len(dq) >= RPM:
        return False, "تمهّل شويّاً — طلبات كثيرة بسرعة", 429
    dq.append(now)
    day[0] += 1
    return True, "", 200


# ─────────────────────────── التطبيق ───────────────────────────
app = FastAPI(title="Ayso Proxy", version=VERSION, docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ORIGIN] if ORIGIN else ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["content-type", "x-ayso-pass", "authorization"],
)


app.include_router(term_router)


@app.get("/api/health")
async def health():
    return JSONResponse(
        {
            "ok": True,
            "version": VERSION,
            "key_loaded": bool(KEY),
            "password": bool(PASSWORD),
            "rpm": RPM,
            "daily": DAILY,
            "terminal": term_router is not None,
        }
    )


@app.post("/api/chat")
async def chat(req: Request):
    if not KEY:
        return JSONResponse({"error": {"message": "السيرفر بلا مفتاح — أضف AYSO_KEY"}}, 500)

    if PASSWORD:
        given = req.headers.get("x-ayso-pass", "")
        if given != PASSWORD:
            return JSONResponse({"error": {"message": "كلمة المرور غير صحيحة"}}, 401)

    ip = client_ip(req)
    ok, msg, code = rate_ok(ip)
    if not ok:
        return JSONResponse({"error": {"message": msg}}, code)

    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"error": {"message": "طلب غير صالح"}}, 400)

    model = str(body.get("model", "")).strip()
    if not model:
        return JSONResponse({"error": {"message": "بلا نموذج"}}, 400)
    if MODELS and model not in MODELS:
        return JSONResponse({"error": {"message": "نموذج غير مسموح"}}, 403)

    # سقف الرموز
    try:
        mt = int(body.get("max_tokens") or 0)
    except Exception:
        mt = 0
    if mt <= 0 or mt > MAX_TOK:
        body["max_tokens"] = MAX_TOK

    # حماية: البثّ فقط
    body["stream"] = True
    body.pop("provider", None)          # يُسبب خطأ عند المزوّد

    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {KEY}",
        "accept": "text/event-stream",
    }

    client = httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT, connect=20.0))

    async def passthrough():
        try:
            async with client.stream("POST", UPSTREAM, json=body, headers=headers) as r:
                if r.status_code != 200:
                    raw = await r.aread()
                    try:
                        j = json.loads(raw)
                        m = j.get("error", {}).get("message") or f"HTTP {r.status_code}"
                    except Exception:
                        m = f"HTTP {r.status_code}"
                    payload = json.dumps({"error": {"message": m}}, ensure_ascii=False)
                    yield f"data: {payload}\n\n".encode()
                    return
                async for chunk in r.aiter_raw():
                    if chunk:
                        yield chunk
        except httpx.TimeoutException:
            payload = json.dumps({"error": {"message": "تجاوز الوقت"}}, ensure_ascii=False)
            yield f"data: {payload}\n\n".encode()
        except Exception as e:
            payload = json.dumps({"error": {"message": f"خطأ: {type(e).__name__}"}}, ensure_ascii=False)
            yield f"data: {payload}\n\n".encode()
        finally:
            await client.aclose()

    return StreamingResponse(
        passthrough(),
        media_type="text/event-stream",
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )


@app.get("/")
async def root():
    if INDEX.exists():
        return FileResponse(INDEX, media_type="text/html; charset=utf-8")
    return JSONResponse({"ok": True, "version": VERSION, "note": "ضع الواجهة في static/index.html"})


@app.get("/manifest.webmanifest")
async def manifest():
    return JSONResponse(
        {
            "name": "Ayso",
            "short_name": "Ayso",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#0b0b0d",
            "theme_color": "#0b0b0d",
        }
    )


@app.get("/favicon.ico")
async def favicon():
    p = ROOT / "static" / "favicon.ico"
    if p.exists():
        return FileResponse(p)
    return Response(status_code=204)
