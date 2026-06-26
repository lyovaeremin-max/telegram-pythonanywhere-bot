import os
import random
import telebot
from telebot.types import Message
import threading
# from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton  # Добавлено
from bot.clients import bot, BOT_INFO, store
from bot.config import COMMIT_SHA, HF_SPACE_ID, HOSTING_LABEL, MODEL, RATE_LIMIT
from bot.ai import ask_ai
from bot.helpers import is_allowed, keep_typing, send_reply, should_respond
from bot.history import clear_history
from bot.preferences import get_provider, set_provider
from bot.rate_limit import is_rate_limited

# Verbose console logging for local dev and teaching. Enabled by
# BOT_VERBOSE_LOG=1 (run_local.py sets this automatically). Prints one
# line per inbound/outbound message so kids and teachers can see the
# conversation flow in their terminal while the bot is running.
VERBOSE_LOG = os.environ.get("BOT_VERBOSE_LOG", "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


def _log(message, direction: str, text: str) -> None:
    """Print a one-line trace of a message in verbose mode.

    direction is "in" (user → bot) or "out" (bot → user). Text is
    truncated to 500 characters so long AI replies don't flood the
    terminal. Newlines are collapsed for single-line readability.
    """
    if not VERBOSE_LOG:
        return
    user = message.from_user
    user_name = (
        f"@{user.username}" if user.username else (user.first_name or f"user:{user.id}")
    )
    bot_name = f"@{BOT_INFO.username}"
    snippet = (text or "").replace("\n", " ").replace("\r", " ")
    if len(snippet) > 500:
        snippet = snippet[:500] + "..."
    if direction == "in":
        sender, receiver = user_name, bot_name
    else:
        sender, receiver = bot_name, user_name
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {sender} → {receiver}: {snippet}", flush=True)

# launge

# user_lang = {}

# def get_text(user_id, key):
#     lang = user_lang.get(user_id, "ru")  # по умолчанию русский
#     return LANGS[lang][key]

# @bot.message_handler(commands=["lang"])
# def change_lang(message):
#     markup = InlineKeyboardMarkup()
#     markup.add(
#         InlineKeyboardButton("Русский", callback_data="lang_ru"),
#         InlineKeyboardButton("English", callback_data="lang_en")
#     )
#     bot.send_message(message.chat.id, "Выберите язык / Choose language:", reply_markup=markup)

# @bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
# def set_lang(call):
#     lang = call.data.split("_")[1]
#     user_lang[call.from_user.id] = lang
#     bot.send_message(call.message.chat.id, f"Язык установлен: {lang}")

# @bot.message_handler(commands=["story"])
# def start_story(message):
#     player_health[message.chat.id] = 3
#     markup = InlineKeyboardMarkup()
#     markup.add(
#         InlineKeyboardButton(get_text(message.chat.id, "open_door"), callback_data="story_open"),
#         InlineKeyboardButton(get_text(message.chat.id, "hide"), callback_data="story_hide")
#     )
#     bot.send_message(message.chat.id, get_text(message.chat.id, "story_intro"), reply_markup=markup)


# LANGS = {
#     "ru": {
#         "start": "Добро пожаловать! Выберите действие:",
#         "games": "Игры",
#         "help": "Помощь",
#         "story_intro": "🌙 3 часа ночи. Ты проснулся от стука в двери...",
#         "open_door": "Открыть дверь",
#         "hide": "Не открывать",
#         "restart": "🔄 Начать заново",
#         "menu": "🏠 Выйти в меню",
#         "game_over": "💀 Ты погиб. Игра окончена.",
#         "win": "🎉 Ты выжил!"
#     },
#     "en": {
#         "start": "Welcome! Choose an action:",
#         "games": "Games",
#         "help": "Help",
#         "story_intro": "🌙 It's 3 AM. You woke up from knocking at the door...",
#         "open_door": "Open the door",
#         "hide": "Do not open",
#         "restart": "🔄 Restart",
#         "menu": "🏠 Back to menu",
#         "game_over": "💀 You died. Game over.",
#         "win": "🎉 You survived!"
#     }
# }


#text container

JOKES = [
    "Почему программисты любят кофе? Потому что без него код не компилируется!",
    "Баг — это не ошибка, это скрытая фича.",
    "Оптимист видит стакан наполовину полным, пессимист — наполовину пустым, а программист — объект класса Стакан.",
    "Почему Python такой дружелюбный? Потому что у него нет скобок, только улыбки :)",
    "Компьютер — это устройство, которое решает все проблемы, которых у вас не было до его покупки."
]


FACTS = [
    "У акулы нет костей — её скелет состоит из хрящей 🦈",
    "Самая высокая гора в Солнечной системе — Олимп на Марсе, высотой около 21 км 🌋",
    "Мёд никогда не портится — археологи находили съедобный мёд в гробницах фараонов 🍯",
    "У улитки может быть до 25 000 зубов 🐌",
    "В космосе нет звуков — звук не распространяется в вакууме 🚀"
]

MOODS = [
    "Сегодня я в отличном настроении 🚀",
    "Немного устал, но держусь 💪",
    "Настроение супер, спасибо что спросил 😎",
    "норм у тя как?",
    "нет ну в целом пойдет спс что спросил",
    "утсал хватит этих а нормально стало легче хаха шутка без обид",
    "ну норм поговорим о играх?",
    "целый день не спросил и сейчас спрашиваешь нормально ты как?"
]

#bot

#start command

@bot.message_handler(commands=["start"], func=is_allowed)
def cmd_start(message):
    # Создаем главное меню с кнопками
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Игры", callback_data="menu_games"),
        InlineKeyboardButton("Помощь", callback_data="menu_help"),
        InlineKeyboardButton("запомнить", callback_data="remember_start"),
        InlineKeyboardButton("напомнить", callback_data="viewnote_start"),
        InlineKeyboardButton("напоминание по времени", callback_data="remind_start"),
        InlineKeyboardButton("удалить заметку", callback_data="deletenote_start"),
        # InlineKeyboardButton("Язык🌎", callback_data="lang"),
    )
    markup.add(
        InlineKeyboardButton("Начать заново", callback_data="help_start"),
        InlineKeyboardButton("Сбросить", callback_data="help_reset"),
    )
    markup.add(
        InlineKeyboardButton("Шутка", callback_data="help_joke"),
        InlineKeyboardButton("Факт", callback_data="help_fact"),
    )
    
    # Отправляем сообщение с главным меню
    bot.send_message(
        message.chat.id,
        "Добро пожаловать! Выберите действие из меню ниже:" \
        "Вы так же можете общятся с ботом:" \
        "ВНИМАНИЕ не передовайте боту личные данные поскольку это может быть не безопасно",
        reply_markup=markup,
    )

# Обработчик для кнопки "Игры"
@bot.callback_query_handler(func=lambda call: call.data == "menu_games")
def menu_games(call):
    # Создаем меню игр
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Викторина", callback_data="help_quiz"),
        InlineKeyboardButton("Угадай число", callback_data="help_gamenumber"),
        InlineKeyboardButton("Камень ножници бумага", callback_data="help_rps"),
        InlineKeyboardButton("Математика", callback_data="help_math"),
        InlineKeyboardButton("сюжет (Хоррор рекомендуется играть с хоррор музыкой)", callback_data="story"),
    )
    markup.add(
        InlineKeyboardButton("Назад", callback_data="menu_main"),
    )
    
    # Отправляем сообщение с меню игр
    bot.send_message(
        call.message.chat.id,
        "Выберите игру:",
        reply_markup=markup,
    )

# Обработчик для кнопки "Помощь"
@bot.callback_query_handler(func=lambda call: call.data == "menu_help")
def menu_help(call):
    # Создаем меню помощи
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Начать заново", callback_data="help_start"),
        InlineKeyboardButton("запомнить", callback_data="remember_start"),
        InlineKeyboardButton("напомнить", callback_data="viewnote_start"),
        InlineKeyboardButton("напоминание по времени", callback_data="remind_start"),
        InlineKeyboardButton("удалить заметку", callback_data="deletenote_start"),
        InlineKeyboardButton("Сбросить", callback_data="help_reset"),
        # InlineKeyboardButton("Язык🌎", callback_data="lang"),
    )
    markup.add(
        InlineKeyboardButton("Шутка", callback_data="help_joke"),
        InlineKeyboardButton("Факт", callback_data="help_fact"),
    )
    markup.add(
        InlineKeyboardButton("Назад", callback_data="menu_main"),
    )
    
    # Отправляем сообщение с меню помощи
    bot.send_message(
        call.message.chat.id,
        "Выберите действие из меню помощи:",
        reply_markup=markup,
    )

# Обработчик для кнопки "Назад" (возврат в главное меню)
@bot.callback_query_handler(func=lambda call: call.data == "menu_main")
def menu_main(call):
    cmd_start(call.message)



    # remind

# Обработчик команды "напомнить через время "версия 2" "

@bot.callback_query_handler(func=lambda call: call.data == "remind_start")
def handle_remind_start(call):
    bot.send_message(
        call.message.chat.id,
        "Чтобы установить напоминание, напиши команду:\n"
        "/remind [время в секундах] [текст]\n"
        "Пример: /remind 10 Выпить воды"
    )


# Обработчик команды "напомнить через время"

@bot.message_handler(commands=["remind"], func=is_allowed)
def remind_after_time(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.send_message(
            message.chat.id,
            "❌ Неверный формат. Используйте: /remind [время в секундах] [текст напоминания].\n"
            "Пример: /remind 10 Выпить воды"
        )
        return

    try:
        delay = int(parts[1])  # Время в секундах
        reminder_text = parts[2]  # Текст напоминания
    except ValueError:
        bot.send_message(message.chat.id, "❌ Время должно быть числом. Попробуйте снова.")
        return

    bot.send_message(message.chat.id, f"⏳ Напоминание установлено через {delay} секунд.")

    # Запускаем таймер
    threading.Timer(delay, send_reminder, args=(message.chat.id, reminder_text)).start()

def send_reminder(chat_id, text):
    """Функция для отправки напоминания."""
    bot.send_message(chat_id, f"🔔 Напоминание: {text}")


def save_note(user_id, note):
    """Сохраняет заметку для пользователя."""
    store.set(f"note:{user_id}", note)

def get_note(user_id):
    """Получает заметку пользователя."""
    return store.get(f"note:{user_id}")

def delete_note(user_id):
    """Удаляет заметку пользователя."""
    store.delete(f"note:{user_id}")



# Обработчик для кнопки "запомнить"
@bot.callback_query_handler(func=lambda call: call.data == "remember_start")
def handle_remember_start(call):
    bot.send_message(
        call.message.chat.id,
        "Введите заметку в формате: /remember [текст заметки]. Пример: /remember купить хлеб"
    )

# Обработчик для кнопки "упоминуть"
@bot.callback_query_handler(func=lambda call: call.data == "viewnote_start")
def handle_viewnote_start(call):
    note = store.get(f"note:{call.from_user.id}")
    if note:
        bot.send_message(call.message.chat.id, f"📝 Твоя заметка: {note}")
    else:
        bot.send_message(call.message.chat.id, "❌ У тебя пока нет сохранённых заметок.")

# Обработчик для кнопки "удалить заметку"
@bot.callback_query_handler(func=lambda call: call.data == "deletenote_start")
def handle_deletenote_start(call):
    store.delete(f"note:{call.from_user.id}")
    bot.send_message(call.message.chat.id, "🗑️ Заметка удалена.")

    #remember

@bot.message_handler(commands=["remember"], func=is_allowed)
def cmd_remember(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) == 1:
        bot.send_message(message.chat.id, "❌ Нужно написать заметку после команды. Пример: /remember купить хлеб")
        return
    note = parts[1]
    store.set(f"note:{message.from_user.id}", note)
    bot.send_message(message.chat.id, f"✅ Заметка сохранена: {note}")

@bot.message_handler(commands=["viewnote"], func=is_allowed)
def cmd_viewnote(message):
    note = store.get(f"note:{message.from_user.id}")
    if note:
        bot.send_message(message.chat.id, f"📝 Твоя заметка: {note}")
    else:
        bot.send_message(message.chat.id, "❌ У тебя пока нет сохранённых заметок.")

@bot.message_handler(commands=["deletenote"], func=is_allowed)
def cmd_deletenote(message):
    store.delete(f"note:{message.from_user.id}")
    bot.send_message(message.chat.id, "🗑️ Заметка удалена.")

#fact command

# bot = telebot.TeleBot("YOUR_TOKEN")

@bot.message_handler(commands=["fact"])
def send_fact(message):
    fact = random.choice(FACTS)
    bot.send_message(message.chat.id, random.choice(FACTS))

# joke command

@bot.message_handler(commands=["joke"], func=is_allowed)
def cmd_joke(message):
    joke = random.choice(JOKES)
    bot.send_message(message.chat.id, joke)

# help command

@bot.message_handler(commands=["help"], func=is_allowed)
def cmd_help(message):
    # Создаем inline-кнопки для всех доступных команд
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Начать заново", callback_data="help_start"),
        InlineKeyboardButton("запомнить", callback_data="help_remember"),
        InlineKeyboardButton("напомнить", callback_data="help_viewnote"),
        InlineKeyboardButton("напоминание по времени", callback_data="remind_start"),
        InlineKeyboardButton("удалить заметку", callback_data="help_deletenote"),

        InlineKeyboardButton("Помощь", callback_data="help_help"),
    )
    markup.add(
        InlineKeyboardButton("Сбросить", callback_data="help_reset"),
        InlineKeyboardButton("О боте", callback_data="help_about"),
        # InlineKeyboardButton("Язык🌎", callback_data="lang"),
    )
    markup.add(
        InlineKeyboardButton("Шутка", callback_data="help_joke"),
        InlineKeyboardButton("Факт", callback_data="help_fact"),
    )
    markup.add(
        InlineKeyboardButton("Игра: Угадай число", callback_data="help_gamenumber"),
        InlineKeyboardButton("Викторина", callback_data="help_quiz"),
        InlineKeyboardButton("камень ножници бумага", callback_data="help_rps"),
        InlineKeyboardButton("Математика", callback_data="help_math"),
        InlineKeyboardButton("сюжет (Хоррор рекомендуется играть с хоррор музыкой)", callback_data="story"),
    )
    
    # Отправляем сообщение с inline-кнопками
    bot.send_message(
        message.chat.id,
        "Выберите действие из меню ниже:",
        reply_markup=markup,
    )

# Обработчик для inline-кнопок из меню помощи
@bot.callback_query_handler(func=lambda call: call.data.startswith("help_"))
def handle_help_callback(call):
    action = call.data.split("_")[1]
    
    if action == "start":
        cmd_start(call.message)
    elif action == "help":
        bot.send_message(call.message.chat.id, "Это меню помощи. Выберите команду для выполнения.")
    elif action == "reset":
        cmd_reset(call.message)
    elif action == "about":
        cmd_about(call.message)
    elif action == "joke":
        cmd_joke(call.message)
    elif action == "fact":
        send_fact(call.message)
    elif action == "gamenumber":
        start_game(call.message)
    elif action == "quiz":
        start_quiz(call.message)
    elif action == "rps":
        start_rps(call.message)
    elif action == "math":
        start_math(call.message)
    # elif action == "remember":
    #     cmd_remember(call.message)
    # elif action == "viewnote":
    #     cmd_viewnote(call.message)
    # elif action == "deletenote":
    #     cmd_deletenote(call.message)


    #game container

#Game 1

SECRET_NUMBER = random.randint(1, 10)

@bot.message_handler(commands=["gamenumber"])
def start_game(message):
    bot.send_message(message.chat.id, "Я загадал число от 1 до 10. Попробуй угадать!")

@bot.message_handler(func=lambda msg: msg.text.isdigit())
def guess_number(message):
    guess = int(message.text)
    if guess == SECRET_NUMBER:
        bot.send_message(message.chat.id, "🎉 Верно! Ты угадал!")
    else:
        bot.send_message(message.chat.id, "Нет, попробуй ещё!")

#Game2

QUIZ = {
    "Столица Франции?": {
        "correct": "Париж",
        "options": ["Париж", "Лондон", "Берлин", "Мадрид"]
    },
    "Сколько будет 2+2?": {
        "correct": "4",
        "options": ["3", "4", "5", "6"]
    },
    "Самая большая страна по площади?": {
    "correct": "Россия",
    "options": ["Россия", "Канада", "Китай", "США"]
    },
    "Кто был первым президентом США?": {
    "correct": "Джордж Вашингтон",
    "options": ["Авраам Линкольн", "Джордж Вашингтон", "Томас Джефферсон", "Бенджамин Франклин"]
    },
    "Какая планета ближе всего к Солнцу?": {
    "correct": "Меркурий",
    "options": ["Меркурий", "Венера", "Земля", "Марс"]
    },
    "Кто написал 'Войну и мир'?": {
    "correct": "Лев Толстой",
    "options": ["Фёдор Достоевский", "Лев Толстой", "Александр Пушкин", "Иван Тургенев"]
    },
    "Какой язык программирования используется для Telegram‑ботов чаще всего?": {
    "correct": "Python",
    "options": ["Python", "Java", "C++", "Go"]
    },
}

@bot.message_handler(commands=["quiz"])
def start_quiz(message):
    question, data = random.choice(list(QUIZ.items()))
    correct_answer = data["correct"]
    options = data["options"]
    
    # Создаем кнопки с уникальными вариантами ответов
    markup = InlineKeyboardMarkup()
    random.shuffle(options)  # Перемешиваем варианты
    for option in options:
        markup.add(InlineKeyboardButton(option, callback_data=f"quiz:{option}:{correct_answer}"))
    
    # Добавляем кнопку "Остановить викторину"
    markup.add(InlineKeyboardButton("Остановить викторину", callback_data="quiz_stop"))
    
    bot.send_message(message.chat.id, f"Вопрос: {question}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("quiz:") or call.data == "quiz_stop")
def check_quiz_answer(call):
    if call.data == "quiz_stop":
        # Показываем меню с выбором "Остановить викторину" или "Продолжить"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Продолжить викторину", callback_data="continue_quiz"))
        markup.add(InlineKeyboardButton("Остановить викторину", callback_data="stop_quiz"))
        bot.send_message(call.message.chat.id, "Вы хотите продолжить или остановить викторину?", reply_markup=markup)
        return
    
    # Проверяем ответ пользователя
    _, user_answer, correct_answer = call.data.split(":")
    if user_answer == correct_answer:
        bot.send_message(call.message.chat.id, "✅ Правильно!")
    else:
        bot.send_message(call.message.chat.id, f"❌ Неправильно. Правильный ответ: {correct_answer}")
    
    # Задаем следующий вопрос автоматически
    continue_quiz(call)

@bot.callback_query_handler(func=lambda call: call.data == "continue_quiz")
def continue_quiz(call):
    # Задаем следующий вопрос
    question, data = random.choice(list(QUIZ.items()))
    correct_answer = data["correct"]
    options = data["options"]
    
    # Создаем кнопки для следующего вопроса
    markup = InlineKeyboardMarkup()
    random.shuffle(options)
    for option in options:
        markup.add(InlineKeyboardButton(option, callback_data=f"quiz:{option}:{correct_answer}"))
    
    # Добавляем кнопку "Остановить викторину"
    markup.add(InlineKeyboardButton("Остановить викторину", callback_data="quiz_stop"))
    
    bot.send_message(call.message.chat.id, f"Следующий вопрос: {question}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "stop_quiz")
def stop_quiz(call):
    # Автоматически вызываем команду /start
    cmd_start(call.message)


# Game 3

CHOICES = ["камень", "ножницы", "бумага"]

@bot.message_handler(commands=["rps"])
def start_rps(message):
    # создаём кнопки для выбора
    markup = telebot.types.InlineKeyboardMarkup()
    for choice in CHOICES:
        markup.add(telebot.types.InlineKeyboardButton(choice.capitalize(), callback_data=f"rps:{choice}"))
    bot.send_message(message.chat.id, "Выбери вариант:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rps:"))
def rps_result(call):
    user_choice = call.data.split(":")[1]
    bot_choice = random.choice(CHOICES)
    if user_choice == bot_choice:
        result = "🤝 Ничья!"
    elif (user_choice == "камень" and bot_choice == "ножницы") or \
         (user_choice == "ножницы" and bot_choice == "бумага") or \
         (user_choice == "бумага" and bot_choice == "камень"):
        result = "🎉 Ты выиграл!"
    else:
        result = "😅 Я выиграл!"

    # кнопки "Начать заново" и "Вернуться в меню"
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🔄 Начать заново", callback_data="rps_restart"))
    markup.add(telebot.types.InlineKeyboardButton("🏠 Вернуться в меню", callback_data="menu_main"))

    bot.send_message(
        call.message.chat.id,
        f"Ты выбрал: {user_choice}, я выбрал: {bot_choice}. {result}",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "rps_restart")
def restart_rps(call):
    start_rps(call.message)


# Game 4

@bot.message_handler(commands=["math"])
def start_math(message):
    a, b = random.randint(1, 10), random.randint(1, 10)
    correct = a + b
    markup = InlineKeyboardMarkup()
    options = [correct, correct+1, correct-1, correct+2]
    random.shuffle(options)
    for opt in options:
        markup.add(InlineKeyboardButton(str(opt), callback_data=f"math:{opt}:{correct}"))
    markup.add(InlineKeyboardButton("🏠 Вернуться в меню", callback_data="menu_main"))
    bot.send_message(message.chat.id, f"Сколько будет {a}+{b}?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("math:"))
def check_math(call):
    _, user_answer, correct = call.data.split(":")
    if user_answer == correct:
        bot.send_message(call.message.chat.id, "✅ Правильно!")
    else:
        bot.send_message(call.message.chat.id, f"❌ Неправильно. Правильный ответ: {correct}")
    start_math(call.message)



# Game 5


player_health = {}

def lose_health(chat_id):
    if chat_id in player_health:
        player_health[chat_id] -= 1
        bot.send_message(chat_id, f"⏳ Время вышло! Ты потерял 1 здоровье. Осталось: {player_health[chat_id]}")
        if player_health[chat_id] <= 0:
            bot.send_message(chat_id, "💀 Ты погиб. Игра окончена.")
            return

@bot.message_handler(commands=["story"])
def start_story(message):
    player_health[message.chat.id] = 3
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Открыть дверь", callback_data="story_open"),
        InlineKeyboardButton("Не открывать", callback_data="story_hide")
    )
    bot.send_message(message.chat.id, "🌙 3 часа ночи. Ты проснулся от стука в двери не просто стук а жуткий как будто дверь ломают. У тебя 70 секунд, чтобы решить что делать:", reply_markup=markup)
    threading.Timer(70, lose_health, args=(message.chat.id,)).start()


@bot.callback_query_handler(func=lambda call: call.data in [
    "story_open", "story_hide", "story_jump", "story_hide2",
    "story_GoToCar", "story_go", "story_car_theft", "story_onfoot"
])
def story_step(call):
    if call.data == "story_open":
        game_over(call.message.chat.id, "Ты открыл дверь... там пусто. Но стены стали красными, появился монстр, и он напал на тебя. 💀 Ты погиб.")

    elif call.data == "story_hide":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("Спрыгнуть с окна", callback_data="story_jump"),
            InlineKeyboardButton("Прятаться", callback_data="story_hide2")
        )
        bot.send_message(call.message.chat.id, "Ты сделал вид, что дома никого нет.и у тебя снова 70 секунд! чтобы решить Стук продолжается... ключ повернулся в замке. что будешь делать?", reply_markup=markup)
        threading.Timer(70, lose_health, args=(call.message.chat.id,)).start()

    elif call.data == "story_hide2":
        game_over(call.message.chat.id, "Ты спрятался дома... монстр сломал дверь и нашёл тебя. 💀")

    elif call.data == "story_jump":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("идти к машине", callback_data="story_GoToCar"),
            InlineKeyboardButton("Прогуляться", callback_data="story_go")
        )
        bot.send_message(call.message.chat.id, "Ты спрыгнул с окна и у тебя снова 70 секунд ты попал в аномалию. 🌌 Всё вокруг странное, людей нет... но в дали замечаешь машину в нем никого нет но двигатель работает ты слишишь звук фары тоже работают что ты сделаешь?", reply_markup=markup)
        threading.Timer(70, lose_health, args=(call.message.chat.id,)).start()

    elif call.data == "story_GoToCar":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("угнать машину", callback_data="story_car_theft"),
            InlineKeyboardButton("остаться пешком", callback_data="story_onfoot")
        )
        bot.send_message(call.message.chat.id, "Ты подошёл к машине. У тебя снова 70 секунд чтобы решить магина щаведена в нем никого нет ключи в машине что сделаешь?", reply_markup=markup)
        threading.Timer(70, lose_health, args=(call.message.chat.id,)).start()

    elif call.data == "story_car_theft":
        markup = InlineKeyboardMarkup()
        markup.add(
        InlineKeyboardButton("🔄 Начать заново", callback_data="story_restart"),
        InlineKeyboardButton("🏠 Выйти в меню", callback_data="menu_main")
    )
        bot.send_message(call.message.chat.id, "Ты угнал машину и уехал в безопасное место. 🎉 Ты выжил!", reply_markup=markup)


    elif call.data == "story_onfoot":
        game_over(call.message.chat.id, "Ты решил остаться пешком, но тебя нашли монстры. 💀")

    elif call.data == "story_go":
        game_over(call.message.chat.id, "Ты решил прогуляться... но аномалия усилилась, и ты потерял сознание. 💀")






@bot.message_handler(commands=["story"])
def start_story(message: Message):
    ...




timers = {}

t = threading.Timer(70, lose_health, args=(Message.chat.id,))
t.start()
timers[Message.chat.id] = t


def game_over(chat_id, text="💀 Ты погиб. Игра окончена."):
    # Останавливаем таймер, если он есть
    if chat_id in timers:
        timers[chat_id].cancel()
        del timers[chat_id]

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🔄 Начать заново", callback_data="story_restart"),
        InlineKeyboardButton("🏠 Выйти в меню", callback_data="menu_main")
    )
    bot.send_message(chat_id, text, reply_markup=markup)




# def game_over(chat_id, text="💀 Ты погиб. Игра окончена."):
#     markup = InlineKeyboardMarkup()
#     markup.add(
#         InlineKeyboardButton("🔄 Начать заново", callback_data="story_restart"),
#         InlineKeyboardButton("🏠 Выйти в меню", callback_data="menu_main")
#     )
#     bot.send_message(chat_id, text, reply_markup=markup)

# @bot.callback_query_handler(func=lambda call: call.data == "story_restart")
# def restart_story(call):
#     start_story(call.message)  # перезапуск игры




@bot.callback_query_handler(func=lambda call: call.data == "story")
def start_story_callback(call):
    start_story(call.message)  # вызываем ту же функцию, что и при команде /story




        #messegs container

@bot.message_handler(func=lambda msg: "как дела" in msg.text.lower())
def mood_reply(message):
    bot.send_message(message.chat.id, random.choice(MOODS))


@bot.message_handler(commands=["reset"], func=is_allowed)
def cmd_reset(message):
    clear_history(message.from_user.id)
    bot.send_message(message.chat.id, "Conversation cleared. Starting fresh!")


@bot.message_handler(commands=["about"], func=is_allowed)
def cmd_about(message):
    if HF_SPACE_ID:
        provider = get_provider(message.from_user.id)
        model_line = f"{MODEL} (main)" if provider == "main" else f"{HF_SPACE_ID} (hf)"
    else:
        model_line = MODEL
    storage_line = "SQLite" if store is not None else "stateless (no memory)"
    lines = [
        f"Model  : {model_line}",
        f"Storage: {storage_line}",
        f"Hosting: {HOSTING_LABEL}",
        "",
        "Личность: Я дружелюбный бот 🤖, люблю делиться фактами, шутками, болтать, говорить обо всем и помогать в учёбе!"
    ]
    if COMMIT_SHA:
        lines.append(f"Version: {COMMIT_SHA}")
    # отправляем только один раз
    bot.send_message(message.chat.id, "\n".join(lines))


# if else container

if HF_SPACE_ID:

    @bot.message_handler(commands=["model"], func=is_allowed)
    def cmd_model(message):
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) == 1:
            current = get_provider(message.from_user.id)
            bot.send_message(
                message.chat.id,
                f"Current provider: {current}\n\n"
                "Options:\n"
                "/model main — Cerebras (fast, multilingual, with memory)\n"
                "/model hf — ArmGPT (Armenian only, slow, no memory)",
            )
            return
        choice = parts[1].strip().lower()
        if choice not in ("main", "hf"):
            bot.send_message(
                message.chat.id, "Invalid choice. Use: /model main or /model hf"
            )
            return
        if not set_provider(message.from_user.id, choice):
            bot.send_message(
                message.chat.id, "Could not save preference. Try again later."
            )
            return
        if choice == "hf":
            bot.send_message(
                message.chat.id,
                "Switched to hf (ArmGPT).\n\n"
                "Note: this is a tiny base completion model trained only on Armenian text. "
                "It will continue whatever you write rather than answer questions, "
                "and it does not understand English. Replies take ~30-60s and there is no memory.",
            )
        else:
            bot.send_message(message.chat.id, "Switched to Main Provider.")


@bot.message_handler(content_types=["text"], func=is_allowed)
def handle_message(message):
    if not should_respond(message):
        return
    text = (message.text or "").replace(f"@{BOT_INFO.username}", "").strip()
    if not text:
        # Edited messages, forwards, or stickers-with-empty-caption can
        # arrive with no usable text. Don't burn rate-limit / AI calls on them.
        return
    _log(message, "in", text)
    if is_rate_limited(message.from_user.id):
        limit_msg = f"You've reached the daily limit of {RATE_LIMIT} messages. Try again tomorrow."
        bot.send_message(message.chat.id, limit_msg)
        _log(message, "out", f"[rate limited] {limit_msg}")
        return
    try:
        with keep_typing(message.chat.id):
            reply = ask_ai(message.from_user.id, text)
        send_reply(message, reply)
        _log(message, "out", reply)
    except Exception as e:
        print(f"Error in handle_message: {e}")
        bot.send_message(message.chat.id, "Something went wrong. Please try again.")
        _log(message, "out", f"[error] {e}")
