import telebot
import requests
from urllib.parse import quote
import pandas as pd
from datetime import datetime, timedelta
import os
import time
import schedule
import threading
import json
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

TOKEN = "8797601950:AAFdHH1XfBA-Mcp3QgWJseMi1u4dVbJU8Rw"
bot = telebot.TeleBot(TOKEN)

FILE = "prices_history.csv"
USER_ITEMS_FILE = "user_items.json"
user_chat_id = None
cache = {}
cache_time = None

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

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def load_user_items():
    if os.path.exists(USER_ITEMS_FILE):
        with open(USER_ITEMS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_user_items(items):
    with open(USER_ITEMS_FILE, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


user_items = load_user_items()


def get_steam_price(item):
    encoded = quote(item)
    url = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=5&market_hash_name={encoded}"
    try:
        return requests.get(url, timeout=15).json().get("lowest_price", "Нет")
    except:
        return "Ошибка"


def get_all_prices(use_cache=True):
    global cache, cache_time
    now = datetime.now()

    if use_cache and cache and cache_time and (now - cache_time).total_seconds() < 600:
        return cache

    items_to_check = user_items if user_items else [
        "Fever Case",
        "M4A1-S | Fade (Factory New)",
        "Glock-18 | AXIA (Factory New)"
    ]

    results = []
    for item in items_to_check:
        price = get_steam_price(item)
        results.append((item, price))
        time.sleep(1.5)

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


@bot.message_handler(commands=['start'])
def start(message):
    global user_chat_id
    user_chat_id = message.chat.id
    bot.send_message(message.chat.id, "Привет! Бот готов.\n\n"
                                      "Команды:\n"
                                      "/prices — цены твоих предметов\n"
                                      "/add Название предмета — добавить\n"
                                      "/remove Название предмета — удалить\n"
                                      "/mylist — твой список")


@bot.message_handler(commands=['add'])
def add_item(message):
    global user_items
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(message.chat.id, "Используй: /add AK-47 | Redline (Field-Tested)")
        return

    item = args[1]
    if item in user_items:
        bot.send_message(message.chat.id, "Этот предмет уже есть в списке.")
        return

    user_items.append(item)
    save_user_items(user_items)
    bot.send_message(message.chat.id, f"✅ Добавлен: {item}")


@bot.message_handler(commands=['remove'])
def remove_item(message):
    global user_items
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(message.chat.id, "Используй: /remove AK-47 | Redline (Field-Tested)")
        return

    item = args[1]
    if item not in user_items:
        bot.send_message(message.chat.id, "Этого предмета нет в списке.")
        return

    user_items.remove(item)
    save_user_items(user_items)
    bot.send_message(message.chat.id, f"❌ Удалён: {item}")


@bot.message_handler(commands=['mylist'])
def mylist(message):
    if not user_items:
        bot.send_message(message.chat.id, "Твой список пуст. Добавь предметы командой /add")
        return

    text = "📋 **Твой список предметов:**\n\n"
    for i, item in enumerate(user_items, 1):
        text += f"{i}. {item}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=['prices'])
def prices(message):
    global user_chat_id
    user_chat_id = message.chat.id

    if not user_items:
        bot.send_message(message.chat.id, "Сначала добавь предметы командой /add")
        return

    bot.send_message(message.chat.id, "⏳ Собираю цены...")
    results = get_all_prices(use_cache=True)

    text = "📊 **Твои цены**\n\n"
    for item, price in results:
        dyn7 = get_dynamics(item, 7)
        dyn30 = get_dynamics(item, 30)
        text += f"**{item}**\n"
        text += f"   Цена: {price}\n"
        text += f"   7д: {dyn7} | 30д: {dyn30}\n\n"

    bot.send_message(message.chat.id, text, parse_mode="Markdown")


schedule.every().day.at("08:00").do(lambda: None)  # можно добавить авто-отчёт позже


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)


threading.Thread(target=run_scheduler, daemon=True).start()

print("Бот с добавлением предметов запущен!")
bot.polling()