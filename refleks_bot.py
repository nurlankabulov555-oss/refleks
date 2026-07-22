# -*- coding: utf-8 -*-
"""
⚡ REFLEKS — Mini App o'yinni ochuvchi Telegram bot

Bot /start buyrug'ida chiroyli tugma yuboradi.
Tugma bosilganda to'liq ekranli REFLEKS o'yini (Mini App) ochiladi.

O'rnatish:
  pip install aiogram

Sozlash:
  1. BOT_TOKEN  — @BotFather dan olingan token
  2. WEBAPP_URL — refleks.html joylashtirilgan HTTPS manzil
                  (masalan GitHub Pages: https://username.github.io/refleks/)
"""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)

# ================= SOZLAMALAR =================
BOT_TOKEN = "BU_YERGA_TOKEN_QOYING"
WEBAPP_URL = "https://SIZNING_USERNAME.github.io/refleks/"  # HTTPS bo'lishi SHART!

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def play_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎮 O'YINNI BOSHLASH",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ],
        ]
    )


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "⚡ <b>REFLEKS</b>\n"
        "<i>15 ta sinov. Nerv signalingiz qancha tez?</i>\n\n"
        "⚡ <b>REAKSIYA</b>\n"
        "Tez bos · Emojini top · Tartib bilan (1→12) · Farqni top · Bos/Bosma · Yon ko'rish\n\n"
        "🧠 <b>XOTIRA</b>\n"
        "Sonni eslab qol · Naqsh xotirasi · Ketma-ketlik · Juftlik topish · Dual N-Back\n\n"
        "🎓 <b>MIYA</b>\n"
        "Stroop test · Tez hisob · Vaqt sezgisi · 24 o'yini\n\n"
        "Rekordlaringiz bulutda saqlanadi. Tugmani bosing 👇",
        reply_markup=play_keyboard(),
        parse_mode="HTML",
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🎮 O'ynash uchun /start ni bosing va «O'YINNI BOSHLASH» tugmasini tanlang.\n\n"
        "Savol yoki takliflar bo'lsa — o'yin egasiga yozing 🙂",
    )


async def main():
    print("⚡ REFLEKS bot ishga tushdi...")
    print(f"🌐 O'yin manzili: {WEBAPP_URL}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
