
import telebot
from telebot.types import Message

from logging import StreamHandler, getLogger


import settings
from datetime import datetime, date

from actioners import UserActioner
from clients.client_db import SQLiteClient
from clients.telegram_client import TelegramClient

logger = getLogger(__name__)
logger.addHandler(StreamHandler())
logger.setLevel("INFO")

BOT_TOKEN = settings.BOT_TOKEN
ADMIN_CHAT_ID = settings.ADMIN_CHAT_ID


class MyBot(telebot.TeleBot):
    def __init__(self, telegram_client: TelegramClient, user_actioner: UserActioner, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.telegram_client = telegram_client
        self.user_actioner = user_actioner

    def setup_resources(self):
        self.user_actioner.setup()

    def shutdown_resources(self):
        self.user_actioner.shutdown()

    def shutdown(self):
        self.shutdown_resources()


telegram_client = TelegramClient(token=BOT_TOKEN, base_url="https://api.telegram.org")
user_actioner = UserActioner(SQLiteClient("users.db"))
bot = MyBot(token=BOT_TOKEN, telegram_client=telegram_client, user_actioner=user_actioner)
bot.setup_resources()


@bot.message_handler(commands=["start"])
def start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    chat_id = message.chat.id
    create_new_user = True

    user = bot.user_actioner.get_user(user_id=str(user_id))
    if not user:
        bot.user_actioner.create_user(user_id=str(user_id), username=username, chat_id=chat_id)
        create_new_user = False
    bot.reply_to(message=message, text=f"Вы {'уже' if create_new_user else ''} зарегистрированы: {username}. "
                                       f" Ваш user_id: {user_id}")


def handle_about_day(message: Message):
    bot.user_actioner.update_date(user_id=str(message.from_user.id), updated_date=date.today())
    bot.send_message(chat_id=ADMIN_CHAT_ID, text=f'Пользователь {message.from_user.username} говорит: {message.text}')
    bot.reply_to(message, 'Отлично! Ты хорошо потрудился!')


@bot.message_handler(commands=["say_about_day"])
def say_about_day(message: Message):
    bot.reply_to(message, text='Привет! Чем сегодня занимался?')
    bot.register_next_step_handler(message, callback=handle_about_day)


def create_err_message(err: Exception) -> str:
    return f"{datetime.now()} ::: {err.__class__} ::: {err}"


while True:
    try:
        bot.setup_resources()
        bot.polling()
    except Exception as err:
        error_message = create_err_message(err)
        bot.telegram_client.post(method="sendMessage", params={"chat_id": ADMIN_CHAT_ID,
                                                               "text": error_message})
        logger.error(error_message)
        bot.shutdown()
