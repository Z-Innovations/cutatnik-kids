import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os

TOKEN = os.environ.get('TOKEN')
bot = telebot.TeleBot(TOKEN)

CHANNEL_ID = '@'+os.environ.get('CHANNEL')  
ADMIN_ID = int(os.environ.get('ADMIN'))


user_states = {}

pending_messages = {}

@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    user_states[chat_id] = {'step': 1}
    bot.send_message(chat_id, "Привет! Отправь мне ЦУтату, которую хочешь опубликовать.")

@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    chat_id = message.chat.id
    if chat_id in user_states:
        del user_states[chat_id]
    if chat_id in pending_messages:
        del pending_messages[chat_id]
    bot.send_message(chat_id, "Операция отменена.")

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    chat_id = message.chat.id


    if chat_id not in user_states:
        bot.send_message(chat_id, "Ой! Похоже, ты пытаешься стать Александром Шаховым! Начни с команды /start")
        return

    state = user_states[chat_id]
    if state['step'] == 1:
        
        user_states[chat_id]['quote'] = message.text
        user_states[chat_id]['step'] = 2
        bot.send_message(chat_id, "Теперь отправь имя автора ЦУтаты с хештегом.")
    elif state['step'] == 2:
        
        quote = user_states[chat_id]['quote']
        author = message.text
        final_message = f'"{quote}"\n— {author}'
        pending_messages[chat_id] = final_message

        
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("Принять", callback_data=f"accept_{chat_id}"),
            InlineKeyboardButton("Отклонить", callback_data=f"reject_{chat_id}")
        )
        
        bot.send_message(ADMIN_ID, f"Новая цитата от пользователя {chat_id}:\n\n{final_message}", reply_markup=markup)
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

    if data.startswith("accept_"):
        if user_id in pending_messages:
            final_message = pending_messages.pop(user_id)
            bot.send_message(CHANNEL_ID, final_message)
            bot.answer_callback_query(call.id, "Сообщение принято и отправлено в канал.")
            bot.send_message(user_id, "Твоя ЦУтата принята и опубликована!")
        else:
            bot.answer_callback_query(call.id, "ЦУтата не найдена или уже обработана.")
    elif data.startswith("reject_"):
        if user_id in pending_messages:
            pending_messages.pop(user_id)
            bot.answer_callback_query(call.id, "ЦУтата отклонена.")
            bot.send_message(user_id, "Твоя ЦУтата была отклонена.")
        else:
            bot.answer_callback_query(call.id, "ЦУтата не найдена или уже обработана.")

bot.polling()

