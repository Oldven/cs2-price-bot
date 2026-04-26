import telebot
import requests
from urllib.parse import quote
import pandas as pd
from datetime import datetime, timedelta
import os
import time
import schedule
import threading
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use('Agg')

TOKEN = "8797601950:AAFdHH1XfBA-Mcp3QgWJseMi1u4dVbJU8Rw"
bot = telebot.TeleBot(TOKEN)

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


def get_steam_price(item):
    encoded = quote(item)
    url = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=5&market_hash_name={encoded}"
    try:
        return requests.get(url, timeout=15).json().get("lowest_price", "Нет")
    except:
        return "Ошибка"


def get_csfloat_price(item):
    encoded = quote(item)
    url = f"https://api.csfloat.com/v1/listings?market_hash_name={encoded}&limit=1&sort_by=price&order=asc"
    try:
        data = requests.get(url, timeout=15).json()
        if data.get("listings"):
            return f"${data['listings'][0]['price']}"
        return "Нет"
    except:
        return "Ошибка"


def get_lisskins_price(item):
    encoded = quote(item)
    url = f"https://api.lisskins.com/api/v1/market/search?q={encoded}&limit=1"
    try:
        data = requests.get(url, timeout=15).json()
        if data.get("items"):
            return data["items"][0].get("price", "Нет")
        return "Нет"
    except:
        return "Ошибка"


def get_all_prices(use_cache=True):
    global cache, cache_time
    now = datetime.now()

    if use_cache and cache and cache_time and (now - cache_time).total_seconds() < 600:
        return cache

    results = []
    for item in items:
        steam = get_steam_price(item)
        csfloat = get_csfloat_price(item)
        liss = get_lisskins_price(item)
        results.append((item, steam, csfloat, liss))
        time.sleep(1.8)

    cache = results
    cache_time = now
    return results


def get_dynamics(item, days):
    if not os.path.exists(FILE):
        return "Нет данных"
    df = pd.read_csv(FILE)
    if "datetime" not in df.columns:
        return "Нет данных"
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
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    data = [{"datetime": today, "item": item, "price_rub": rub, "price_usd": usd}
            for item, rub, usd in results]
    df_new = pd.DataFrame(data)
    if os.path.exists(FILE):
        df_old = pd.read_csv(FILE)
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new
    df.to_csv(FILE, index=False)

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
    bot.send_message(message.chat.id, "Привет! Бот готов.\nНапиши /prices чтобы увидеть сравнение цен")


@bot.message_handler(commands=['prices'])
def prices(message):
    global user_chat_id
    user_chat_id = message.chat.id
    bot.send_message(message.chat.id, "⏳ Собираю цены со Steam, CSFloat и LisSkins...")

    results = get_all_prices(use_cache=True)

    text = "📊 **Сравнение цен**\n\n"
    for item, steam, csfloat, liss in results:
        text += f"**{item}**\n"
        text += f"   Steam:     {steam}\n"
        text += f"   CSFloat:   {csfloat}\n"
        text += f"   LisSkins:  {liss}\n\n"

    bot.send_message(message.chat.id, text, parse_mode="Markdown")


schedule.every().day.at("08:00").do(send_daily_report)


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)


threading.Thread(target=run_scheduler, daemon=True).start()

print("Бот с CSFloat + LisSkins запущен!")
bot.polling()