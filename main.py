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


def generate_chart(item):
    if not os.path.exists(FILE):
        return None
    df = pd.read_csv(FILE)
    if "datetime" not in df.columns:
        return None
    df["datetime"] = pd.to_datetime(df["datetime"])
    item_df = df[df["item"] == item].copy()
    if len(item_df) < 3:
        return None
    item_df = item_df.sort_values("datetime")
    item_df["price_num"] = item_df["price_rub"].apply(
        lambda x: float(str(x).replace(" ", "").replace(",", ".").replace("руб.", ""))
    )
    plt.figure(figsize=(10, 5))
    plt.plot(item_df["datetime"], item_df["price_num"], marker='o', linewidth=2, color='#2E86AB')
    plt.title(f"Цена {item} за последние дни", fontsize=14)
    plt.xlabel("Дата")
    plt.ylabel("Цена (руб)")
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    filename = f"chart_{item.replace(' ', '_').replace('|', '')}.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    return filename


@bot.message_handler(commands=['start'])
def start(message):
    global user_chat_id
    user_chat_id = message.chat.id
    bot.send_message(message.chat.id, "Привет! Бот готов.\nНапиши /prices или /chart Fever Case")


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
        text += f"**{item}**\n   🇷🇺 {rub} | 🇺🇸 {usd}\n   7д: {dyn7} | 30д: {dyn30}\n\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=['chart'])
def chart(message):
    global user_chat_id
    user_chat_id = message.chat.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(message.chat.id, "Используй: /chart Fever Case")
        return
    item_name = args[1]
    if item_name not in items:
        bot.send_message(message.chat.id, "Такой предмет не найден.")
        return
    bot.send_message(message.chat.id, "⏳ Строю график...")
    filename = generate_chart(item_name)
    if filename and os.path.exists(filename):
        with open(filename, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=f"График {item_name}")
        os.remove(filename)
    else:
        bot.send_message(message.chat.id, "Недостаточно данных для графика.")


schedule.every().day.at("08:00").do(send_daily_report)


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)


threading.Thread(target=run_scheduler, daemon=True).start()

print("Бот с графиками запущен!")
bot.polling()