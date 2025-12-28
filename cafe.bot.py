from telebot import TeleBot
from telebot.types import (
    ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto
)
from io import BytesIO
import qrcode

# Твой токен и ID администратора
BOT_TOKEN = "8292431082:AAE6DxgeZU5gc1EvopKpnC0vkxgnnCSitzU"
ADMIN_ID = 2027162196

bot = TeleBot(BOT_TOKEN)

# Меню и корзины
MENU = {
    "☕ Капучино": {"price": 120, "photo": "https://i.imgur.com/2N1xOeO.jpeg"},
    "🍵 Матча латте": {"price": 180, "photo": "https://i.imgur.com/0JQ6m8P.jpeg"},
    "🥐 Круассан": {"price": 140, "photo": "https://i.imgur.com/fB1Zk8O.jpeg"},
    "🍰 Чизкейк": {"price": 220, "photo": "https://i.imgur.com/1uHq7Qp.jpeg"},
    "🥪 Сендвич": {"price": 200, "photo": "https://i.imgur.com/d2mQfQv.jpeg"},
}

carts = {}
subscribers = set()


def main_keyboard():
    mk = ReplyKeyboardMarkup(resize_keyboard=True)
    mk.add("📋 Меню", "🛒 Корзина")
    mk.add("🔥 Акции", "❓ Помощь")
    return mk


def menu_inline():
    mk = InlineKeyboardMarkup(row_width=2)
    for name, item in MENU.items():
        mk.add(
            InlineKeyboardButton(f"{name} — {item['price']} ₽", callback_data=f"add_{name}")
        )
    mk.add(InlineKeyboardButton("🛒 Открыть корзину", callback_data="open_cart"))
    return mk


def cart_inline(chat_id):
    mk = InlineKeyboardMarkup(row_width=2)
    cart = carts.get(chat_id, {})
    for name, qty in cart.items():
        mk.add(
            InlineKeyboardButton(f"➖ {name}", callback_data=f"dec_{name}"),
            InlineKeyboardButton(f"➕ {name}", callback_data=f"inc_{name}"),
        )
    if cart:
        mk.add(
            InlineKeyboardButton("🧹 Очистить", callback_data="clear_cart"),
            InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout"),
        )
    mk.add(InlineKeyboardButton("📋 Вернуться к меню", callback_data="back_menu"))
    return mk


def cart_total(chat_id):
    cart = carts.get(chat_id, {})
    return sum(MENU[name]["price"] * qty for name, qty in cart.items())


@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    subscribers.add(chat_id)
    bot.send_message(
        chat_id,
        "Добро пожаловать в кафе! ☕🍰\nВыбирай из меню, собирай корзину и оформляй заказ.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(func=lambda m: m.text == "📋 Меню")
def show_menu(message):
    chat_id = message.chat.id
    media = []
    for name, item in MENU.items():
        if item.get("photo"):
            media.append(InputMediaPhoto(item["photo"], caption=f"{name} — {item['price']} ₽"))
    if media:
        try:
            bot.send_media_group(chat_id, media)
        except Exception:
            pass
    bot.send_message(chat_id, "Выбирай позиции из меню:", reply_markup=menu_inline())


@bot.message_handler(func=lambda m: m.text == "🛒 Корзина")
def open_cart_msg(message):
    send_cart(message.chat.id)


def send_cart(chat_id):
    cart = carts.get(chat_id, {})
    if not cart:
        bot.send_message(chat_id, "Корзина пуста. Добавь позиции из меню 👇", reply_markup=menu_inline())
        return
    lines = [f"{name} × {qty} = {MENU[name]['price'] * qty} ₽" for name, qty in cart.items()]
    total = cart_total(chat_id)
    text = "🛒 Корзина:\n" + "\n".join(lines) + f"\n\nИтого: {total} ₽"
    bot.send_message(chat_id, text, reply_markup=cart_inline(chat_id))


@bot.message_handler(func=lambda m: m.text == "🔥 Акции")
def promo(message):
    bot.reply_to(message, "Сегодня: второй капучино за полцены ☕ -50% при покупке двух!")


@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def help_cmd(message):
    bot.reply_to(message, "Нажимай «Меню», добавляй позиции и оформляй заказ. Вопросы — пиши сюда.")


@bot.callback_query_handler(func=lambda c: True)
def cart_actions(call):
    chat_id = call.message.chat.id
    data = call.data

    if data.startswith("add_"):
        name = data[4:]
        carts.setdefault(chat_id, {})
        carts[chat_id][name] = carts[chat_id].get(name, 0) + 1
        send_cart(chat_id)

    elif data.startswith("inc_"):
        name = data[4:]
        carts[chat_id][name] += 1
        send_cart(chat_id)

    elif data.startswith("dec_"):
        name = data[4:]
        if carts[chat_id][name] > 1:
            carts[chat_id][name] -= 1
        else:
            carts[chat_id].pop(name)
        send_cart(chat_id)

    elif data == "clear_cart":
        carts[chat_id] = {}
        send_cart(chat_id)

    elif data == "back_menu":
        show_menu(call.message)

    elif data == "checkout":
        cart = carts.get(chat_id, {})
        if not cart:
            bot.answer_callback_query(call.id, text="Корзина пуста")
            return
        total = cart_total(chat_id)
        order_lines = [f"{name} × {qty} = {MENU[name]['price'] * qty} ₽" for name, qty in cart.items()]
        order_text = "Заказ:\n" + "\n".join(order_lines) + f"\nИтого: {total} ₽"

        qr_payload = f"КафеЗаказ | chat:{chat_id} | Итого {total} ₽"
        bio = BytesIO()
        qrcode.make(qr_payload).save(bio, 'PNG')
        bio.seek(0)

        bot.send_photo(chat_id, bio, caption=order_text + "\n\nПокажи QR на кассе.")
        bot.send_message(ADMIN_ID, f"🧾 Новый заказ\n{order_text}\nchat_id: {chat_id}")
        carts[chat_id] = {}


@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.send_message(message.chat.id, "Выбери действие 👇", reply_markup=main_keyboard())


print("Кафе-бот запущен!")
bot.infinity_polling(skip_pending=True)
