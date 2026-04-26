import telebot
import requests
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from datetime import datetime, timedelta
import os
import time
import schedule
import threading

TOKEN = "8797601950:AAFdHH1XfBA-Mcp3QgWJseMi1u4dVbJU8Rw"
bot = telebot.TeleBot(TOKEN)

items = ["Fever Case",
    "M4A1-S | Fade (Factory New)",
    "Glock-18 | AXIA (Factory New)",
    "USP-S | Alpine Camo (Factory New)",
    "SSG 08 | Zeno (Factory New)",
    "Nova | Yorkshire (Factory New)",
    "P250 | Small Game (Factory New)",
    "USP-S | Whiteout (Field-Tested)",
    "Budapest 2025 Contenders Sticker Capsule"
        ]  # оставь свой список

FILE = "prices_history.csv"
user_chat_id = None
cache = {}  # кэш
cache_time = {}  # время кэша


def get_prices_for_item(item):
    encoded = quote(item)
    url_rub = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=5&market_hash_name={encoded}"
    url_usd = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=1&market_hash_name={encoded}"
    try:
        rub = requests.get(url_rub, timeout=10).json().get("lowest_price", "Нет")
        usd = requests.get(url_usd, timeout=10).json().get("lowest_price", "Нет")
        return item, rub, usd
    except:
        return item, "Ошибка", "Ошибка"


def get_all_prices(use_cache=True):
    global cache, cache_time
    now = datetime.now()

    # Если есть свежий кэш (меньше 5 минут) — используем его
    if use_cache and cache and (now - cache_time).total_seconds() < 300:
        return cache

    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(get_prices_for_item, items))

    cache = results
    cache_time = now
    return results


# ... остальной код без изменений (start, prices, send_daily_report и т.д.)

@bot.message_handler(commands=['prices'])
def prices(message):
    global user_chat_id
    user_chat_id = message.chat.id
    bot.send_message(message.chat.id, "⏳ Собираю цены...")

    results = get_all_prices(use_cache=True)

    text = "📊 **Цены + Динамика**\n\n"
    for item, rub, usd in results:
        dyn7 = get_dynamics(item, 7)
        dyn30 = get_dynamics(item, 30)
        text += f"**{item}**\n"
        text += f"   🇷🇺 {rub}   |   🇺🇸 {usd}\n"
        text += f"   7 дней: {dyn7}   |   30 дней: {dyn30}\n\n"

    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ... остальной код (schedule и т.д.)