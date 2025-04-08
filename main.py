import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import os

if not {'TOKEN', 'CHANNEL', 'ADMIN'} <= set(os.environ):
    print("Token, channel or adminis missing")

TOKEN = os.environ.get('TOKEN') or ''
bot = telebot.TeleBot(TOKEN)

CHANNEL_ID = os.environ.get('CHANNEL') or ''
try: CHANNEL_ID = int(CHANNEL_ID)
except: CHANNEL_ID = '@'+CHANNEL_ID

ADMIN_ID = os.environ.get('ADMIN') or ''
try: ADMIN_ID = int(ADMIN_ID)
except: ADMIN_ID = '@'+ADMIN_ID

user_states = {}
pending_messages = {}

@bot.message_handler(commands=['start'])
def start_command(message: Message):
    if message.chat.type == 'group': return
    chat_id = message.chat.id
    user_states[chat_id] = {'step': 1}
    bot.send_message(chat_id, "Привет! Отправь мне ЦУтату, которую хочешь опубликовать.")

@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    if message.chat.type == 'group': return
    chat_id = message.chat.id
    user_states.pop(chat_id, None)
    pending_messages.pop(chat_id, None)
    bot.send_message(chat_id, "Операция отменена.")

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    if message.chat.type == 'group': return
    chat_id = message.chat.id

    if chat_id not in user_states:
        bot.send_message(chat_id, "Ой! Похоже, ты пытаешься стать Александром Шаховым! Начни с команды /start")
        return

    step = user_states[chat_id]['step']
    if step == 1:
        user_states[chat_id] = {
            'quote': message.text,
            'step': 2,
        }
        bot.send_message(chat_id, "Теперь отправь имя автора ЦУтаты.")
    elif step == 2:
        quote = user_states[chat_id]['quote']
        author = message.text
        pending_messages[chat_id] = f'"{quote}"\n— #{author}'

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("Принять", callback_data=f"accept_{chat_id}"),
            InlineKeyboardButton("Отклонить", callback_data=f"reject_{chat_id}")
        )
        
        bot.send_message(ADMIN_ID, f"Новая цитата от пользователя @{message.chat.username or '<no username>'} ({chat_id}):\n\n{pending_messages[chat_id]}", reply_markup=markup)
        bot.send_message(chat_id, "Ваше сообщение отправлено на проверку администратору!")

        del user_states[chat_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_") or call.data.startswith("reject_"))
def callback_handler(call):
    data = call.data

    try:
        user_id = int(data.split("_")[1])
    except (IndexError, ValueError):
        bot.answer_callback_query(call.id, "Не ломай бота! Пожалуйста, вводи правильные данные!")
        return

    if user_id in pending_messages:
        final_message = pending_messages.pop(user_id)
        if data.startswith("accept_"):
            bot.send_message(CHANNEL_ID, final_message)
            bot.answer_callback_query(call.id, "Сообщение принято и отправлено в канал.")
            bot.send_message(user_id, "Твоя ЦУтата принята и опубликована!")
        elif data.startswith("reject_"):
            bot.answer_callback_query(call.id, "ЦУтата отклонена.")
            bot.send_message(user_id, "Твоя ЦУтата была отклонена.")
    else:
        bot.answer_callback_query(call.id, "ЦУтата не найдена или уже обработана.")

bot.polling()

