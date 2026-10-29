# Ayso

مساعد ذكي بواجهة عربية — شات + تيرمنال bash حقيقي.

## النشر
| المنصة | دليل |
|---|---|
| **Render** (مستحسن) | [انشر-على-Render.md](./انشر-على-Render.md) |
| Enzonic / Pterodactyl | [كيف-ترفع.md](./كيف-ترفع.md) |

## التشغيل المحلي
```bash
pip install -r requirements.txt
AYSO_KEY=sk-... PORT=8000 bash start.sh
```

## المتغيّرات
| الاسم | الوظيفة |
|---|---|
| `AYSO_KEY` | مفتاح المزوّد (إلزامي) |
| `AYSO_PASS` | كلمة مرور الموقع (اختياري) |
| `AYSO_TERM_PASS` | كلمة سر التيرمنال |
| `AYSO_RPM` / `AYSO_DAILY` | حدود الطلبات |
| `AYSO_ORIGIN` | أصل CORS المسموح |
| `AYSO_MODELS` | موديلات مسموحة (فارغ = الكل) |

## المسارات
- `/` — الواجهة
- `/term` — تيرمنال bash
- `/api/chat` — الوسيط
- `/api/health` — الفحص

## البنية
```
app.py      الوسيط + الواجهة
term.py     تيرمنال WebSocket + pty
static/     index.html · term.html
Dockerfile  صورة النشر
render.yaml إعداد Render
start.sh    أمر التشغيل
```
