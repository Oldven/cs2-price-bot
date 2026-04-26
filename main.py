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

matplotlib.use('Agg')  # чтобы не открывать окно

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


# ... (функции get_all_prices, get_dynamics, send_daily_report — оставь как в последней версии)

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
    plt.plot(item_df["datetime"], item_df["price_num"], marker='o', linewidth=2)
    plt.title(f"Цена {item} за последние дни")
    plt.xlabel("Дата")
    plt.ylabel("Цена (руб)")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    filename = f"chart_{item.replace(' ', '_').replace('|', '')}.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    return filename


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
        bot.send_message(message.chat.id, "Такой предмет не найден. Доступные: " + ", ".join(items))
        return

    bot.send_message(message.chat.id, "⏳ Строю график...")
    filename = generate_chart(item_name)

    if filename and os.path.exists(filename):
        with open(filename, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=f"График {item_name}")
        os.remove(filename)
    else:
        bot.send_message(message.chat.id, "Недостаточно данных для графика (нужно минимум 3 записи)")


# ... остальной код (start, prices, scheduler и т.д.)

print("Бот с графиками запущен!")
bot.polling()