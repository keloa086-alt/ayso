# Ayso · صورة جاهزة للنشر على Render / Railway / أي منصة Docker
FROM python:3.12-slim

# ── أدوات أساسية للتيرمنال ──
RUN apt-get update && apt-get install -y --no-install-recommends \
        bash git curl ca-certificates procps nano less \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── المكتبات أولاً (طبقة مخزّنة) ──
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── الملفات ──
COPY app.py term.py ./
COPY static/ ./static/
COPY start.sh ./
RUN chmod +x start.sh && mkdir -p /tmp/ayso-ws

# ── مستخدم غير جذري (أمان) ──
RUN useradd -m -u 1000 ayso && chown -R ayso:ayso /app /tmp/ayso-ws
USER ayso

ENV PYTHONUNBUFFERED=1 \
    TERM=xterm-256color \
    AYSO_TERM_DIR=/tmp/ayso-ws

EXPOSE 10000

CMD ["bash", "start.sh"]
