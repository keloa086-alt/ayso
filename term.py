"""
Ayso · تيرمنال حقيقي (bash) داخل الحاوية
================================================================
يفتح تيرمنال bash على السيرفر نفسه — من أي متصفح.

⚠️ أمان: هذا التيرمنال يعمل **داخل حاويتك أنت**.
   لا يُعطى للزوار. يُقفل بكلمة سر إلزامية.

المتغيّرات:
    AYSO_TERM_PASS   كلمة سر التيرمنال (إن لم توجد، يأخذ AYSO_PASS)
    AYSO_TERM_DIR    مجلد البداية (افتراضي /tmp/ayso-ws)
    AYSO_TERM_IDLE   مهلة الخمول بالثواني (افتراضي 900)
"""

from __future__ import annotations

import os
import pty
import asyncio
import fcntl
import struct
import termios
import pathlib
import secrets
import select

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

TERM_PASS = os.getenv("AYSO_TERM_PASS", "").strip() or os.getenv("AYSO_PASS", "").strip()
TERM_DIR = os.getenv("AYSO_TERM_DIR", "/tmp/ayso-ws")
IDLE = int(os.getenv("AYSO_TERM_IDLE", "900"))

ROOT = pathlib.Path(__file__).parent
PAGE = ROOT / "static" / "term.html"

router = APIRouter()
_active: dict[str, int] = {}          # ip -> sessions


@router.get("/term")
async def term_page():
    if not PAGE.exists():
        return JSONResponse({"error": {"message": "term.html غير موجود"}}, 404)
    return FileResponse(PAGE, media_type="text/html; charset=utf-8")


def _ip(ws: WebSocket) -> str:
    xff = ws.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return ws.client.host if ws.client else "?"


@router.websocket("/api/term")
async def term_ws(ws: WebSocket):
    await ws.accept()

    if not TERM_PASS:
        await ws.send_text("\x1b[31mالتيرمنال مقفول — اضبط AYSO_TERM_PASS في السيرفر\x1b[0m\r\n")
        await ws.close()
        return

    ip = _ip(ws)
    given = ws.query_params.get("p", "")
    if not secrets.compare_digest(given, TERM_PASS):
        await ws.send_text("\x1b[31mكلمة المرور غير صحيحة\x1b[0m\r\n")
        await ws.close()
        return

    if _active.get(ip, 0) >= 1:
        await ws.send_text("\x1b[33mعندك جلسة مفتوحة بالفعل\x1b[0m\r\n")
        await ws.close()
        return

    os.makedirs(TERM_DIR, exist_ok=True)

    # ── افتح pty ──
    master, slave = pty.openpty()
    try:
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
    except Exception:
        pass

    env = dict(os.environ)
    env.update({"TERM": "xterm-256color", "PS1": r"\u@ayso:\w$ ", "LANG": "C.UTF-8"})
    shell = os.getenv("SHELL") or "/bin/bash"

    try:
        proc = await asyncio.create_subprocess_exec(
            shell, "-i",
            stdin=slave, stdout=slave, stderr=slave,
            start_new_session=True,
            cwd=TERM_DIR, env=env,
        )
    except Exception as e:
        await ws.send_text(f"\x1b[31mتعذّر تشغيل bash: {type(e).__name__}\x1b[0m\r\n")
        os.close(master); os.close(slave)
        await ws.close()
        return

    os.close(slave)
    _active[ip] = _active.get(ip, 0) + 1

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    async def pump():
        try:
            while not stop.is_set():
                try:
                    r, _, _ = await loop.run_in_executor(None, select.select, [master], [], [], 1.0)
                except (OSError, ValueError):
                    break
                if not r:
                    continue
                try:
                    data = os.read(master, 4096)
                except OSError:
                    break
                if not data:
                    break
                await ws.send_bytes(data)
        except Exception:
            pass
        finally:
            stop.set()

    task = asyncio.create_task(pump())

    try:
        while True:
            msg = await asyncio.wait_for(ws.receive(), timeout=IDLE)
            if msg.get("type") == "websocket.disconnect":
                break
            if msg.get("bytes") is not None:
                os.write(master, msg["bytes"])
            elif msg.get("text"):
                os.write(master, msg["text"].encode())
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    except Exception:
        pass
    finally:
        stop.set()
        task.cancel()
        try:
            proc.kill()
        except Exception:
            pass
        try:
            os.close(master)
        except Exception:
            pass
        _active[ip] = max(0, _active.get(ip, 1) - 1)
        try:
            await ws.close()
        except Exception:
            pass
