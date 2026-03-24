"""
╔══════════════════════════════════════════════╗
║   OGI FEDYANSYAH — Trading Signal Bot        ║
║   Khusus: Sinyal otomatis dari TradingView   ║
║   Stack: python-telegram-bot v22.6 + aiohttp ║
╚══════════════════════════════════════════════╝
"""

import os
import json
import asyncio
import logging
import sqlite3
from datetime import datetime
from aiohttp import web
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

# ─────────────────────────────────────────────
# KONFIGURASI
# ─────────────────────────────────────────────
BOT_TOKEN       = os.environ.get("BOT_TOKEN", "8493835651:AAHRVdVOPT8HJhugOeNTMvYrF3GmICuIW0k")
SUPER_ADMIN_ID  = 7572944409          # Ogi Fedyansyah — akses penuh
GROUP_ID        = -1003823245991      # Grup trading
BOT_NAME        = "Ogi Fedyansyah"
WEBHOOK_SECRET  = os.environ.get("WEBHOOK_SECRET", "ogifedyansyah_signal_2024")
PORT            = int(os.environ.get("PORT", 8080))

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# DATABASE — simpan riwayat sinyal
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("trading.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sinyal (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            signal      TEXT,
            pair        TEXT,
            timeframe   TEXT,
            entry       TEXT,
            sl          TEXT,
            tp1         TEXT,
            tp2         TEXT,
            rr          TEXT,
            kondisi     TEXT,
            hasil       TEXT DEFAULT 'pending',
            created_at  TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS members (
            user_id     INTEGER PRIMARY KEY,
            first_name  TEXT,
            username    TEXT,
            joined_at   TEXT
        )
    """)
    conn.commit()
    conn.close()

def simpan_sinyal(data: dict):
    conn = sqlite3.connect("trading.db")
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT INTO sinyal (signal, pair, timeframe, entry, sl, tp1, tp2, rr, kondisi, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("signal"), data.get("pair"), data.get("timeframe"),
        data.get("entry"),  data.get("sl"),   data.get("tp1"),
        data.get("tp2"),    data.get("rr"),   data.get("kondisi"), now
    ))
    sinyal_id = c.lastrowid
    conn.commit()
    conn.close()
    return sinyal_id

def get_riwayat(limit=10):
    conn = sqlite3.connect("trading.db")
    c = conn.cursor()
    c.execute("""
        SELECT signal, pair, timeframe, entry, sl, tp1, hasil, created_at
        FROM sinyal ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def update_hasil_sinyal(sinyal_id, hasil):
    conn = sqlite3.connect("trading.db")
    c = conn.cursor()
    c.execute("UPDATE sinyal SET hasil=? WHERE id=?", (hasil, sinyal_id))
    conn.commit()
    conn.close()

def save_member(user):
    conn = sqlite3.connect("trading.db")
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT OR IGNORE INTO members (user_id, first_name, username, joined_at)
        VALUES (?, ?, ?, ?)
    """, (user.id, user.first_name, user.username, now))
    conn.commit()
    conn.close()

def get_total_members():
    conn = sqlite3.connect("trading.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM members")
    total = c.fetchone()[0]
    conn.close()
    return total

def get_stats_sinyal():
    conn = sqlite3.connect("trading.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM sinyal")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM sinyal WHERE hasil='TP'")
    tp = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM sinyal WHERE hasil='SL'")
    sl = c.fetchone()[0]
    conn.close()
    return total, tp, sl

# ─────────────────────────────────────────────
# FORMAT PESAN SINYAL
# ─────────────────────────────────────────────
def format_sinyal(data: dict, sinyal_id: int) -> str:
    signal   = data.get("signal",    "?").upper()
    pair     = data.get("pair",      "?").upper()
    tf       = data.get("timeframe", "?")
    entry    = data.get("entry",     "?")
    sl       = data.get("sl",        "?")
    tp1      = data.get("tp1",       "?")
    tp2      = data.get("tp2",       "-")
    rr       = data.get("rr",        "?")
    kondisi  = data.get("kondisi",   "Market Activity + OB + SAR")
    waktu    = datetime.now().strftime("%d/%m/%Y  %H:%M WIB")

    if signal == "LONG":
        icon  = "🟢"
        label = "LONG  (BUY)"
        chart = "📈"
    elif signal == "SHORT":
        icon  = "🔴"
        label = "SHORT  (SELL)"
        chart = "📉"
    else:
        icon  = "⚪"
        label = signal
        chart = "📊"

    return (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{chart}  *SINYAL TRADING*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{icon}  *{label}*\n"
        f"💱  Pair          :  `{pair}`\n"
        f"⏱  Timeframe  :  `{tf}`\n\n"
        f"*🎯 Level Harga:*\n"
        f"📍  Entry    :  `{entry}`\n"
        f"🛑  SL          :  `{sl}`\n"
        f"✅  TP1       :  `{tp1}`\n"
        f"✅  TP2       :  `{tp2}`\n"
        f"⚖️  RR           :  `{rr}`\n\n"
        f"*🔍 Konfirmasi:*\n"
        f"_{kondisi}_\n\n"
        f"🕐  {waktu}\n"
        f"🆔  Sinyal #{sinyal_id}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️  _Bukan ajakan investasi._\n"
        f"_Selalu kelola risiko dengan bijak._"
    )

# ─────────────────────────────────────────────
# TELEGRAM BOT — COMMAND HANDLERS
# ─────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_member(update.effective_user)
    nama = update.effective_user.first_name or "Trader"
    await update.message.reply_text(
        f"👋 Halo *{nama}!*\n\n"
        f"Selamat datang di *{BOT_NAME} Trading Bot* 📊\n\n"
        f"Bot ini mengirimkan sinyal trading otomatis dari TradingView "
        f"langsung ke grup.\n\n"
        f"📌 *Perintah tersedia:*\n"
        f"/sinyal — Kirim sinyal manual\n"
        f"/riwayat — Riwayat sinyal terakhir\n"
        f"/stats — Statistik sinyal\n"
        f"/status — Status bot\n\n"
        f"_Selalu kelola risiko dengan bijak._ 🙏",
        parse_mode="Markdown"
    )

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total, tp, sl = get_stats_sinyal()
    members = get_total_members()
    winrate = round((tp / total * 100), 1) if total > 0 else 0
    await update.message.reply_text(
        f"📊 *Status Bot — {BOT_NAME}*\n\n"
        f"🤖 Bot          : Online ✅\n"
        f"👥 Members  : {members} orang\n"
        f"📡 Webhook  : Aktif\n\n"
        f"*📈 Statistik Sinyal:*\n"
        f"Total sinyal  : {total}\n"
        f"✅ TP             : {tp}\n"
        f"❌ SL              : {sl}\n"
        f"🎯 Winrate    : {winrate}%\n\n"
        f"_Data dihitung dari sinyal yang sudah di-update hasilnya._",
        parse_mode="Markdown"
    )

async def cmd_riwayat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = get_riwayat(10)
    if not rows:
        await update.message.reply_text("📋 Belum ada sinyal yang tercatat.")
        return
    text = f"📋 *Riwayat Sinyal Terakhir — {BOT_NAME}*\n\n"
    for r in rows:
        signal, pair, tf, entry, sl, tp1, hasil, created = r
        icon = "🟢" if signal == "LONG" else "🔴"
        hasil_icon = {"TP": "✅", "SL": "❌", "pending": "⏳"}.get(hasil, "⏳")
        tgl = created[:16] if created else "-"
        text += (
            f"{icon} *{signal}* `{pair}` — {tf}\n"
            f"   Entry: `{entry}` | SL: `{sl}` | TP1: `{tp1}`\n"
            f"   {hasil_icon} {hasil.upper()}  ·  {tgl}\n\n"
        )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_sinyal_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin kirim sinyal manual: /sinyal BTCUSDT LONG 67450 66200 68700 1H"""
    if update.effective_user.id != SUPER_ADMIN_ID:
        await update.message.reply_text("⛔ Akses ditolak.")
        return

    args = context.args
    if len(args) < 5:
        await update.message.reply_text(
            "📌 *Format perintah:*\n"
            "`/sinyal PAIR SIGNAL ENTRY SL TP1 [TP2] [TF]`\n\n"
            "*Contoh:*\n"
            "`/sinyal BTCUSDT LONG 67450 66200 68700 70500 1H`\n"
            "`/sinyal XAUUSD SHORT 2340 2360 2310 2280 4H`",
            parse_mode="Markdown"
        )
        return

    pair   = args[0].upper()
    signal = args[1].upper()
    entry  = args[2]
    sl     = args[3]
    tp1    = args[4]
    tp2    = args[5] if len(args) > 5 else "-"
    tf     = args[6] if len(args) > 6 else "?"

    # Hitung RR otomatis
    try:
        risk   = abs(float(entry) - float(sl))
        reward = abs(float(tp1)   - float(entry))
        rr     = f"1:{round(reward/risk, 1)}" if risk > 0 else "?"
    except Exception:
        rr = "?"

    data = {
        "signal": signal, "pair": pair, "timeframe": tf,
        "entry": entry,   "sl": sl,     "tp1": tp1,
        "tp2": tp2,       "rr": rr,     "kondisi": "Manual — Admin"
    }

    sinyal_id = simpan_sinyal(data)
    pesan     = format_sinyal(data, sinyal_id)

    await context.bot.send_message(
        chat_id=GROUP_ID, text=pesan, parse_mode="Markdown"
    )
    await update.message.reply_text(
        f"✅ Sinyal #{sinyal_id} berhasil dikirim ke grup!", parse_mode="Markdown"
    )

async def cmd_update_hasil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update hasil sinyal: /hasil 12 TP atau /hasil 12 SL"""
    if update.effective_user.id != SUPER_ADMIN_ID:
        await update.message.reply_text("⛔ Akses ditolak.")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "📌 Format: `/hasil [ID_SINYAL] [TP/SL]`\n"
            "Contoh: `/hasil 12 TP`",
            parse_mode="Markdown"
        )
        return
    try:
        sinyal_id = int(args[0])
        hasil     = args[1].upper()
        if hasil not in ("TP", "SL"):
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Hasil harus TP atau SL.")
        return

    update_hasil_sinyal(sinyal_id, hasil)
    icon = "✅" if hasil == "TP" else "❌"
    await update.message.reply_text(
        f"{icon} Sinyal #{sinyal_id} diupdate → *{hasil}*",
        parse_mode="Markdown"
    )
    # Notif ke grup
    await context.bot.send_message(
        chat_id=GROUP_ID,
        text=(
            f"{icon} *Update Sinyal #{sinyal_id}*\n\n"
            f"Hasil: *{hasil}*\n"
            f"_Diupdate oleh admin._"
        ),
        parse_mode="Markdown"
    )

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        save_member(member)
        nama = member.first_name or "Trader"
        await update.message.reply_text(
            f"👋 Selamat datang *{nama}!*\n\n"
            f"Kamu sudah bergabung di channel sinyal trading *{BOT_NAME}*. 📊\n\n"
            f"Di sini kamu akan menerima sinyal trading otomatis dari TradingView.\n"
            f"Selalu kelola risiko dengan bijak ya! 🙏",
            parse_mode="Markdown"
        )

# ─────────────────────────────────────────────
# WEBHOOK SERVER — terima sinyal dari TradingView
# ─────────────────────────────────────────────
# Simpan referensi bot global
_bot: Bot = None

async def webhook_handler(request: web.Request) -> web.Response:
    # Validasi secret
    secret = request.rel_url.query.get("secret", "")
    if secret != WEBHOOK_SECRET:
        logger.warning("Webhook ditolak — secret salah")
        return web.Response(status=403, text="Forbidden")

    try:
        body = await request.text()
        data = json.loads(body)
        logger.info(f"Sinyal masuk: {data}")
    except Exception as e:
        logger.error(f"JSON error: {e}")
        return web.Response(status=400, text="Bad Request")

    try:
        sinyal_id = simpan_sinyal(data)
        pesan     = format_sinyal(data, sinyal_id)
        await _bot.send_message(
            chat_id=GROUP_ID, text=pesan, parse_mode="Markdown"
        )
        logger.info(f"✅ Sinyal #{sinyal_id} terkirim: {data.get('signal')} {data.get('pair')}")
        return web.Response(status=200, text="OK")
    except Exception as e:
        logger.error(f"Gagal kirim ke Telegram: {e}")
        return web.Response(status=500, text="Internal Server Error")

async def health_check(request: web.Request) -> web.Response:
    return web.Response(text=f"{BOT_NAME} Trading Bot — Online ✅")

# ─────────────────────────────────────────────
# MAIN — jalankan bot + webhook server bersamaan
# ─────────────────────────────────────────────
async def run_webhook_server():
    app = web.Application()
    app.router.add_post("/signal", webhook_handler)
    app.router.add_get("/",        health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"📡 Webhook server aktif di port {PORT}")
    logger.info(f"🔗 Endpoint: /signal?secret={WEBHOOK_SECRET}")

def main():
    global _bot

    logger.info(f"🤖 {BOT_NAME} Trading Bot mulai...")
    init_db()
    logger.info("✅ Database siap!")

    # Build Telegram app
    ptb_app = Application.builder().token(BOT_TOKEN).build()
    _bot    = ptb_app.bot

    # Daftarkan handlers
    ptb_app.add_handler(CommandHandler("start",   cmd_start))
    ptb_app.add_handler(CommandHandler("status",  cmd_status))
    ptb_app.add_handler(CommandHandler("riwayat", cmd_riwayat))
    ptb_app.add_handler(CommandHandler("sinyal",  cmd_sinyal_manual))
    ptb_app.add_handler(CommandHandler("hasil",   cmd_update_hasil))
    ptb_app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome
    ))

    # Jalankan webhook server di background
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_webhook_server())

    logger.info("✅ Bot aktif! Tekan Ctrl+C untuk berhenti.\n")
    ptb_app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
