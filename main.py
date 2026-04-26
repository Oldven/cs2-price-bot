import telebot
import requests
from urllib.parse import quote
import pandas as pd
from datetime import datetime, timedelta
import os
import time
import schedule
import threading

TOKEN = "8797601950:AAFdHH1XfBA-Mcp3QgWJseMi1u4dVbJU8Rw"
bot = telebot.TeleBot(TOKEN)

# === УМЕНЬШИЛ ДО 5 ПРЕДМЕТОВ ДЛЯ СТАБИЛЬНОСТИ ===
items = [
    "Fever Case",
    "M4A1-S | Fade (Factory New)",
    "Glock-18 | AXIA (Factory New)",
    "USP-S | Alpine Camo (Factory New)",
    "SSG 08 | Zeno (Factory New)"
]

FILE = "prices_history.csv"
user_chat_id = None
cache = {}
cache_time = None


def get_all_prices(use_cache=True):
    global cache, cache_time
    now = datetime.now()

    if use_cache and cache and cache_time and (now - cache_time).total_seconds() < 600:
        return cache

    results = []
    for item in items:
        encoded = quote(item)
        url_rub = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=5&market_hash_name={encoded}"
        url_usd = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=1&market_hash_name={encoded}"

        try:
            rub = requests.get(url_rub, timeout=15).json().get("lowest_price", "Нет")
            usd = requests.get(url_usd, timeout=15).json().get("lowest_price", "Нет")
            results.append((item, rub, usd))
        except:
            results.append((item, "Ошибка", "Ошибка"))

        time.sleep(1.5)  # пауза между запросами (важно!)

    cache = results
    cache_time = now
    return results


def get_dynamics(item, days):
    if not os.path.exists(FILE):
        return "Нет данных"
    df = pd.read_csv(FILE)
    df["datetime"] = pd.to_datetime(df["datetime"])
    target = datetime.now() - timedelta(days=days)
    past = df[(df["item"] == item) & (df["datetime"] <= target)]
    if past.empty:
        return "Нет данных"
    try:
        past_price = float(str(past.iloc[-1]["price_rub"]).replace(" ", "").replace(",", ".").replace("руб.", ""))
        current = df[(df["item"] == item) & (df["datetime"] == df["datetime"].max())].iloc[0]["price_rub"]
        current_price = float(str(current).replace(" ", "").replace(",", ".").replace("руб.", ""))
        change = ((current_price - past_price) / past_price) * 100
        sign = "📈" if change > 0 else "📉"
        return f"{sign} {change:+.1f}%"
    except:
        return "Нет данных"


def send_daily_report():
    global user_chat_id
    if not user_chat_id:
        return
    results = get_all_prices(use_cache=False)
    # ... (код отчёта такой же, как раньше)
    text = "📊 **Ежедневный отчёт** (8:00)\n\n"
    for item, rub, usd in results:
        dyn7 = get_dynamics(item, 7)
        dyn30 = get_dynamics(item, 30)
        text += f"**{item}**\n   🇷🇺 {rub} | 🇺🇸 {usd}\n   7д: {dyn7} | 30д: {dyn30}\n\n"
    bot.send_message(user_chat_id, text, parse_mode="Markdown")


@bot.message_handler(commands=['start'])
def start(message):
    global user_chat_id
    user_chat_id = message.chat.id
    bot.send_message(message.chat.id, "Привет! Бот готов (облегчённая версия).")


@bot.message_handler(commands=['prices'])
def prices(message):
    global user_chat_id
    user_chat_id = message.chat.id
    bot.send_message(message.chat.id, "⏳ Собираю цены (5–8 секунд)...")
    results = get_all_prices(use_cache=True)
    text = "📊 **Цены + Динамика**\n\n"
    for item, rub, usd in results:
        dyn7 = get_dynamics(item, 7)
        dyn30 = get_dynamics(item, 30)
        text += f"**{item}**\n   🇷🇺 {rub} | 🇺🇸 {usd}\n   7д: {dyn7} | 30д: {dyn30}\n\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


schedule.every().day.at("08:00").do(send_daily_report)
threading.Thread(target=lambda: schedule.run_continuously(), daemon=True).start()

print("Облегчённый бот запущен!")
bot.polling()