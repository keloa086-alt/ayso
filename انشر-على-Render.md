# نشر Ayso على Render — ٦ دقائق، بلا فيزا

> **ليش Render؟** الوحيد اللي يعطيك سيرفر دائم مجاناً، بلا بطاقة، ويدعم Docker + WebSocket + التيرمنال.

---

## الخطوة ٠ — جهّز الملف

عندك `ayso-deploy.zip` — فيه كل شي جاهز (Dockerfile · render.yaml · السيرفر · الواجهة).

---

## الخطوة ١ — GitHub (٢ دقيقة)

1. سجّل: https://github.com/signup — إيميل فقط
2. اضغط **New repository** → الاسم: `ayso` → **Public** → Create
3. في صفحة المستودع: **Add file → Upload files**
4. اسحب **محتويات** `ayso-deploy.zip` بعد فكّها (مو المجلد نفسه — الملفات)
5. **Commit changes**

> **مهم:** لازم تشوف `Dockerfile` و `app.py` في **جذر** المستودع، مو داخل مجلد.

---

## الخطوة ٢ — Render (دقيقتين)

1. سجّل: https://dashboard.render.com/register → **GitHub** (أسهل، بلا فيزا)
2. **New +** → **Blueprint**
3. اختر مستودع `ayso` → **Connect**
4. Render يقرأ `render.yaml` تلقائياً → يطلب ٣ أسرار:

| المفتاح | القيمة |
|---|---|
| `AYSO_KEY` | `sk-ar-v1-...` (مفتاحك) |
| `AYSO_PASS` | كلمة مرور الموقع (أو اتركها فاضية) |
| `AYSO_TERM_PASS` | كلمة سر التيرمنال |

5. **Apply** → انتظر ٣–٥ دقائق (يبني الصورة)

---

## الخطوة ٣ — اختبر

Render يعطيك رابط مثل:

```
https://ayso-xxxx.onrender.com
```

### فحص

```
https://ayso-xxxx.onrender.com/api/health
```

لازم ترجع:

```json
{"ok":true,"version":"S1.0","key_loaded":true,"password":true,"terminal":true}
```

| الحقل | لو غلط |
|---|---|
| `key_loaded: false` | متغيّر `AYSO_KEY` مو مضبوط → Environment → Edit |
| `password: false` | `AYSO_PASS` فاضي (طبيعي لو تركته) |
| `terminal: false` | عادي — `term.py` ما تحمّل |

### الواجهة والتيرمنال

```
https://ayso-xxxx.onrender.com/       ← الشات
https://ayso-xxxx.onrender.com/term   ← bash حقيقي
```

---

## شنو يشتغل على Render

| | |
|---|---|
| ✅ الشات + البثّ | يعمل |
| ✅ التيرمنال bash | **يعمل** (صورة لينكس كاملة) |
| ✅ python3 · pip · git | متوفرة |
| ✅ WebSocket | مدعوم |
| ✅ HTTPS | تلقائي |
| ⚠️ ينام بعد ١٥ دقيقة خمول | أول طلب بعدها ياخذ ~٣٠ ثانية |
| ⚠️ القرص مؤقّت | أي ملف تكتبه بالتيرمنال يضيع عند إعادة النشر |

---

## لو تريد ما ينام

**الخطة المجانية تنام.** الحلول:

| | |
|---|---|
| **UptimeRobot** | مجاني — يزور موقعك كل ٥ دقائق فيبقى صاحي |
| **Railway** | $1/شهر — ما ينام |
| **Enzonic** | $0 — ما ينام |

**أسهل:** UptimeRobot → New Monitor → HTTP(s) → الرابط `/api/health` → كل ٥ دقائق.

---

## التحديث لاحقاً

```
GitHub → افتح الملف → ✏️ → عدّل → Commit
        ↓
Render ينشر تلقائياً (autoDeploy: true)
```

**بس. بلا أوامر.**

---

## حلّ المشاكل

| المشكلة | الحل |
|---|---|
| `Build failed` | Logs → شوف السطر الأحمر، أرسله لي |
| `Application failed to respond` | تأكّد `start.sh` موجود في الجذر |
| صفحة بيضاء | افتح `/api/health` أول — إذا زين، المشكلة بالواجهة |
| `key_loaded: false` | Environment → أضف `AYSO_KEY` → Save (يعيد النشر) |
| التيرمنال ما يفتح | `AYSO_TERM_PASS` ناقص |
| الشات: «All upstream providers failed» | مشكلة مؤقتة عند المزوّد — جرّب بعد دقيقة |

---

## ملاحظات أمان

```
✅ المفتاح في متغيّر بيئة على Render — ما يوصل المتصفح
✅ .env مستثنى من .gitignore
⚠️ المستودع Public — تأكّد ما فيه مفتاح بأي ملف
⚠️ بدّل مفتاحك الحالي لأنه ظهر بالمحادثة
```

---

## بعد النشر — نسخ احتياطي

```
Env: AYSO_KEY       = مفتاحك الجديد
Env: AYSO_TERM_PASS = كلمة سر قوية
Env: AYSO_PASS      = (اختياري) قفل الموقع للجميع
Env: AYSO_ORIGIN    = https://ayso-xxxx.onrender.com  ← يقفل CORS
Env: AYSO_MODELS    = (اختياري) الموديلات المسموحة فقط
```
