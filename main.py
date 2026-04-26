import telebot
import requests
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
import time

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


def get_prices_for_item(item):
    """Получает цену в рублях и долларах для одного предмета"""
    encoded = quote(item)

    # RUB
    url_rub = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=5&market_hash_name={encoded}"
    # USD
    url_usd = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=1&market_hash_name={encoded}"

    try:
        rub = requests.get(url_rub, timeout=10).json().get("lowest_price", "Нет")
        usd = requests.get(url_usd, timeout=10).json().get("lowest_price", "Нет")
        return item, rub, usd
    except:
        return item, "Ошибка", "Ошибка"


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Бот готов.\nНапиши /prices")


@bot.message_handler(commands=['prices'])
def prices(message):
    bot.send_message(message.chat.id, "⏳ Собираю цены (параллельно)...")

    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(get_prices_for_item, items))

    text = "📊 **Цены на Steam Market**\n\n"
    for item, rub, usd in results:
        text += f"**{item}**\n"
        text += f"   🇷🇺 {rub}\n"
        text += f"   🇺🇸 {usd}\n\n"

    bot.send_message(message.chat.id, text, parse_mode="Markdown")


print("Бот запущен (ускоренная версия)!")
bot.polling()