import telebot
from telebot.types import CallbackQuery, Chat, InlineKeyboardMarkup, InlineKeyboardButton, Message, User
import os

REQUIRED_ENV = {'TOKEN', 'CHANNEL', 'ADMIN'}
# Not required: BOT_USERNAME
if not REQUIRED_ENV <= set(os.environ):
    raise RuntimeError("Some of these environment variables are missing: "+', '.join(REQUIRED_ENV))

TOKEN = os.environ.get('TOKEN') or ''

CHANNEL_ID = os.environ.get('CHANNEL') or ''
try: CHANNEL_ID = int(CHANNEL_ID)
except: CHANNEL_ID = CHANNEL_ID if CHANNEL_ID.startswith('@') else '@'+CHANNEL_ID

ADMIN_ID = os.environ.get('ADMIN') or ''
try: ADMIN_ID = int(ADMIN_ID)
except: ADMIN_ID = ADMIN_ID if ADMIN_ID.startswith('@') else '@'+ADMIN_ID

BOT_USERNAME_NOTICE = None
if 'BOT_USERNAME' in os.environ:
    user = os.environ['BOT_USERNAME']
    user = user if user.startswith('@') else '@'+user
    BOT_USERNAME_NOTICE = f"Отправить свою ЦУтату можно в боте {user}"
    del user

bot = telebot.TeleBot(TOKEN, parse_mode='markdown')

user_states = {}
pending_messages = {}

def format_username(user: Chat | User):
    return f'@{user.username} ({user.id})' if user.username else str(user.id)

@bot.message_handler(commands=['start'])
def start_command(message: Message):
    if message.chat.type == 'group': return
    chat_id = message.chat.id
    user_states[chat_id] = {'step': 1}
    bot.send_message(chat_id, "Привет! Отправь мне ЦУтату, которую хочешь опубликовать.")

@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    if message.chat.type in ('group', 'supergroup', 'channel'): return
    chat_id = message.chat.id
    user_states.pop(chat_id, None)
    pending_messages.pop(chat_id, None)
    bot.send_message(chat_id, "Операция отменена.")

@bot.message_handler(commands=['help'])
def help(m: Message):
    notices = ["Привет! Это бот для отправки ЦУтат."]
    if m.chat.type == 'private':
        notices.append("Для отправки используй команду /start")
        notices.append('''Поддерживаемые форматы автора:
- Автор1
- #Автор1
- Автор1 #Автор2
- #Автор1 #Автор2''')
        notices.append("Для отмены отправки используй команду /cancel")
    if m.chat.id == ADMIN_ID:
        if m.chat.type == 'private':
            notices.append("Ты являешься админом. Когда пользователь отправит ЦУтату, тебе нужно будет одобрить или отклонить её.")
        else:
            notices.append("Эта группа админов. Когда пользователь отправит ЦУтату, кому-то из её участников нужно будет одобрить или отклонить её.")
        if BOT_USERNAME_NOTICE:
            notices.append(BOT_USERNAME_NOTICE)
    elif m.chat.type in ('group', 'supergroup', 'channel'):
        return
    bot.send_message(m.chat.id, '\n\n'.join(notices))

@bot.message_handler(func=lambda message: True)
def handle_messages(message: Message):
    if message.chat.type == 'group': return
    chat_id = message.chat.id

    if not message.text:
        bot.send_message(chat_id, "Поддерживаются только текстовые ЦУтаты.")

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
        author = message.text.removeprefix('#')
        pending_messages[chat_id] = f'"{quote}"\n— #{author}'

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("Принять", callback_data=f"accept_{chat_id}"),
            InlineKeyboardButton("Отклонить", callback_data=f"reject_{chat_id}")
        )
        
        bot.send_message(ADMIN_ID, f"Новая цитата от пользователя {format_username(message.chat)}:\n\n{pending_messages[chat_id]}", reply_markup=markup)
        bot.send_message(chat_id, "Ваше сообщение отправлено на проверку администратору!")

        del user_states[chat_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_") or call.data.startswith("reject_"))
def callback_handler(call: CallbackQuery):
    data = call.data or ''

    try:
        user_id = int(data.split("_")[1])
    except (IndexError, ValueError):
        bot.answer_callback_query(call.id, "Не ломай бота! Пожалуйста, вводи правильные данные!")
        return

    if user_id in pending_messages:
        final_message = pending_messages.pop(user_id)
        result = '<неизвестно>'
        if data.startswith("accept_"):
            bot.send_message(CHANNEL_ID, final_message)
            bot.answer_callback_query(call.id, "Сообщение принято и отправлено в канал.")
            bot.send_message(user_id, "Твоя ЦУтата принята и опубликована!")
            result = 'принята'
        elif data.startswith("reject_"):
            bot.answer_callback_query(call.id, "ЦУтата отклонена.")
            bot.send_message(user_id, "Твоя ЦУтата была отклонена.")
            result = 'отклонена'
        bot.edit_message_reply_markup(call.message.chat.id, call.message.id)
        bot.edit_message_text((call.message.text or '')+f'\n\n_ЦУтата была {result} пользователем {format_username(call.from_user)}._', call.message.chat.id, call.message.id)
    else:
        bot.answer_callback_query(call.id, "ЦУтата не найдена или уже обработана.")

bot.polling()