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

items = [
    "Fever Case",
    "M4A1-S | Fade (Factory New)",
    "Glock-18 | AXIA (Factory New)",
    "USP-S | Alpine Camo (Factory New)",
    "SSG 08 | Zeno (Factory New)",
    "Nova | Yorkshire (Factory New)",
    "P250 | Small Game (Factory New)",
    "USP-S | Whiteout (Field-Tested)",
    "Budapest 2025 Contenders Sticker Capsule"
]

FILE = "prices_history.csv"
user_chat_id = None

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

def send_daily_report():
    global user_chat_id
    if not user_chat_id:
        return
    
    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(get_prices_for_item, items))
    
    # Сохраняем цены
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
    
    # Формируем красивый отчёт
    text = "📊 **Ежедневный отчёт по ценам** (8:00)\n\n"
    for item, rub, usd in results:
        dyn7 = get_dynamics(item, 7)
        dyn30 = get_dynamics(item, 30)
        text += f"**{item}**\n"
        text += f"   🇷🇺 {rub}   |   🇺🇸 {usd}\n"
        text += f"   7д: {dyn7}  |  30д: {dyn30}\n\n"
    
    bot.send_message(user_chat_id, text, parse_mode="Markdown")

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

@bot.message_handler(commands=['start'])
def start(message):
    global user_chat_id
    user_chat_id = message.chat.id
    bot.send_message(message.chat.id, "Привет! Бот готов.\nНапиши /prices или жди утренний отчёт в 8:00")

@bot.message_handler(commands=['prices'])
def prices(message):
    global user_chat_id
    user_chat_id = message.chat.id
    bot.send_message(message.chat.id, "⏳ Собираю цены...")
    
    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(get_prices_for_item, items))
    
    text = "📊 **Цены + Динамика**\n\n"
    for item, rub, usd in results:
        dyn7 = get_dynamics(item, 7)
        dyn30 = get_dynamics(item, 30)
        text += f"**{item}**\n"
        text += f"   🇷🇺 {rub}   |   🇺🇸 {usd}\n"
        text += f"   7 дней: {dyn7}   |   30 дней: {dyn30}\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# === АВТОМАТИЧЕСКИЙ ОТЧЁТ В 8:00 ===
schedule.every().day.at("08:00").do(send_daily_report)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

threading.Thread(target=run_scheduler, daemon=True).start()

print("Бот с автоматическим отчётом запущен!")
bot.polling()

    bot.send_message(message.chat.id, text, parse_mode="Markdown")


print("Бот запущен (ускоренная версия)!")
bot.polling()
