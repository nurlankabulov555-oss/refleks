# -*- coding: utf-8 -*-
"""
⚡ REFLEKS SERVER — bot + global reyting bitta faylda
PythonAnywhere (bepul tarif) uchun mo'ljallangan.

Nima qiladi:
  1. Telegram botni webhook orqali boshqaradi (/start → o'yin tugmasi)
  2. Global reyting API:
       POST /api/score  — natijani qabul qiladi (Telegram imzosi tekshiriladi!)
       GET  /api/top    — TOP-20 + foydalanuvchi o'rni
  3. Natijalar SQLite bazasida saqlanadi (refleks.db)

Xavfsizlik: har bir so'rovdagi initData Telegramning HMAC imzosi bilan
tekshiriladi — soxta natija yuborib bo'lmaydi.

O'rnatish (PythonAnywhere konsolida):
  pip3 install --user flask

Sozlash: pastdagi BOT_TOKEN, WEBAPP_URL, WEBHOOK_SECRET ni to'ldiring.
"""

import hashlib
import hmac
import json
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path

from flask import Flask, request, jsonify

# ================= SOZLAMALAR =================
BOT_TOKEN = "BU_YERGA_TOKEN_QOYING"
WEBAPP_URL = "https://SIZNING_USERNAME.github.io/refleks/"   # O'yin manzili
WEBHOOK_SECRET = "refleks_maxfiy_2026"  # Istalgan maxfiy so'z (webhook URL uchun)

DB_PATH = Path(__file__).parent / "refleks.db"

# O'yinlar: qaysi yo'nalishda yaxshi (min = kichik yaxshi, max = katta yaxshi)
GAMES = {
    "tap": "min", "emoji": "min", "ascend": "min", "odd": "min",
    "gonogo": "min", "periph": "max",
    "memory": "max", "pattern": "max", "seq": "max", "cards": "min", "nback": "max",
    "stroop": "min", "math": "min", "timeest": "min", "game24": "min",
}

app = Flask(__name__)


# ================= BAZA =================
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS scores(
        user_id INTEGER, name TEXT, game TEXT, score INTEGER,
        PRIMARY KEY(user_id, game))""")
    return conn


# ================= TELEGRAM IMZOSINI TEKSHIRISH =================
def verify_init_data(init_data: str):
    """initData ning HMAC imzosini tekshiradi.
    To'g'ri bo'lsa user dict qaytaradi, aks holda None."""
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        their_hash = parsed.pop("hash", None)
        if not their_hash:
            return None
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        my_hash = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(my_hash, their_hash):
            return None
        return json.loads(parsed.get("user", "{}"))
    except Exception:
        return None


# ================= REYTING API =================
@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


@app.route("/api/score", methods=["POST", "OPTIONS"])
def api_score():
    if request.method == "OPTIONS":
        return "", 204
    data = request.get_json(silent=True) or {}
    game = data.get("game")
    score = data.get("score")
    user = verify_init_data(data.get("initData", ""))

    if not user or game not in GAMES or not isinstance(score, int):
        return jsonify({"ok": False}), 400
    # Aql bovar qilmas natijalarni rad etish (oddiy himoya)
    if score < 0 or score > 10_000_000:
        return jsonify({"ok": False}), 400

    name = (user.get("first_name") or "O'yinchi")[:30]
    uid = user["id"]
    better = GAMES[game]

    conn = db()
    cur = conn.execute(
        "SELECT score FROM scores WHERE user_id=? AND game=?", (uid, game)
    ).fetchone()
    is_record = cur is None or (score < cur[0] if better == "min" else score > cur[0])
    if is_record:
        conn.execute(
            "INSERT INTO scores(user_id,name,game,score) VALUES(?,?,?,?) "
            "ON CONFLICT(user_id,game) DO UPDATE SET score=excluded.score, name=excluded.name",
            (uid, name, game, score),
        )
        conn.commit()
    else:
        # Ism yangilangan bo'lishi mumkin
        conn.execute("UPDATE scores SET name=? WHERE user_id=? AND game=?", (name, uid, game))
        conn.commit()
    conn.close()
    return jsonify({"ok": True, "record": is_record})


@app.route("/api/top")
def api_top():
    game = request.args.get("game", "")
    user = verify_init_data(request.args.get("initData", ""))
    if game not in GAMES:
        return jsonify({"ok": False}), 400

    order = "ASC" if GAMES[game] == "min" else "DESC"
    conn = db()
    top = conn.execute(
        f"SELECT user_id, name, score FROM scores WHERE game=? ORDER BY score {order} LIMIT 20",
        (game,),
    ).fetchall()

    my_rank, my_score = None, None
    if user:
        row = conn.execute(
            "SELECT score FROM scores WHERE user_id=? AND game=?", (user["id"], game)
        ).fetchone()
        if row:
            my_score = row[0]
            cmp = "<" if GAMES[game] == "min" else ">"
            my_rank = conn.execute(
                f"SELECT COUNT(*)+1 FROM scores WHERE game=? AND score {cmp} ?",
                (game, my_score),
            ).fetchone()[0]
    conn.close()

    return jsonify({
        "ok": True,
        "top": [{"user_id": r[0], "name": r[1], "score": r[2]} for r in top],
        "my_rank": my_rank,
        "my_score": my_score,
    })


# ================= TELEGRAM BOT (WEBHOOK) =================
def tg_api(method: str, payload: dict):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}
    msg = update.get("message")
    if not msg:
        return "ok"
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")

    if text.startswith("/start"):
        tg_api("sendMessage", {
            "chat_id": chat_id,
            "text": (
                "⚡ <b>REFLEKS</b>\n"
                "<i>15 ta sinov. Nerv signalingiz qancha tez?</i>\n\n"
                "⚡ <b>REAKSIYA</b> — Tez bos · Emojini top · Tartib bilan · "
                "Farqni top · Bos/Bosma · Yon ko'rish\n\n"
                "🧠 <b>XOTIRA</b> — Sonni eslab qol · Naqsh · Ketma-ketlik · "
                "Juftlik · Dual N-Back\n\n"
                "🎓 <b>MIYA</b> — Stroop · Tez hisob · Vaqt sezgisi · 24 o'yini\n\n"
                "🏆 Endi <b>global reyting</b> bor — dunyodagi barcha "
                "o'yinchilar bilan bellashing!\n\nTugmani bosing 👇"
            ),
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "🎮 O'YINNI BOSHLASH", "web_app": {"url": WEBAPP_URL}}
                ]]
            },
        })
    elif text.startswith("/top"):
        # Tezkor TOP-5 (Tez bos bo'yicha) chatda ko'rsatish
        conn = db()
        rows = conn.execute(
            "SELECT name, score FROM scores WHERE game='tap' ORDER BY score ASC LIMIT 5"
        ).fetchall()
        conn.close()
        medals = ["🥇", "🥈", "🥉", "4.", "5."]
        lines = [f"{medals[i]} {r[0]} — {r[1]} ms" for i, r in enumerate(rows)]
        tg_api("sendMessage", {
            "chat_id": chat_id,
            "text": "🏆 <b>TOP-5 · ⚡ Tez bos</b>\n\n" +
                    ("\n".join(lines) if lines else "Hali natijalar yo'q.") +
                    "\n\nTo'liq reyting o'yin ichida!",
            "parse_mode": "HTML",
        })
    return "ok"


@app.route("/")
def home():
    return "⚡ REFLEKS server ishlayapti!"


if __name__ == "__main__":
    # Lokal test uchun (PythonAnywhere'da WSGI orqali ishga tushadi)
    app.run(port=5000, debug=True)
