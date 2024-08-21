import telebot
import pandas as pd

TOKEN = '6170182394:AAEs8LaBL2Dl4iJV-alGfmIF0H8oKV1w_UU'
bot = telebot.TeleBot(TOKEN)

CSV_FILE = 'user_button_selections.csv'

# Считывание файла categories.txt в словарь
categories = {}
dop = {}
with open('categories.txt', 'r', encoding='utf-8') as file:
    for line in file:
        key, value = line.strip().split(':')
        categories[key] = value

with open('dop.txt', 'r', encoding='utf-8') as file:
    for line in file:
        key, value = line.strip().split(':')
        dop[key] = value

# Создание DataFrame для хранения данных о нажатых кнопках
try:
    df = pd.read_csv(CSV_FILE)
except FileNotFoundError:
    with open('categories.txt', 'r', encoding='utf-8') as f1, open('dop.txt', 'r', encoding='utf-8') as f2:
        buttons1 = [line.strip().split(':')[0] for line in f1.readlines()]
        buttons2 = [line.strip().split(':')[0] for line in f2.readlines()]
    
    # Создаем DataFrame с колонками для каждой кнопки из файлов
    columns = ['user_id'] + ['notifications'] + buttons1 + buttons2
    df = pd.DataFrame(columns=columns)

def create_buttons_from_files(file1, file2, user_id):
    with open(file1, 'r', encoding='utf-8') as f1, open(file2, 'r', encoding='utf-8') as f2:
        buttons1 = [line.strip().split(':')[0] for line in f1.readlines()]
        buttons2 = [line.strip().split(':')[0] for line in f2.readlines()]

    markup = telebot.types.InlineKeyboardMarkup()
    
    # Add buttons from the first file in rows of 2
    for i in range(0, len(buttons1), 2):
        row = []
        for button in buttons1[i:i+2]:
            button_text = button
            if not df.empty:
                if (df['user_id'] == user_id).any():
                    if button in df.columns and df.loc[(df['user_id'] == user_id) & (df[button] == True)].shape[0] > 0:
                        button_text = button + ' ✓'
            row.append(telebot.types.InlineKeyboardButton(button_text, callback_data=button))
        markup.row(*row)
    
    # Add buttons from the second file, one per row
    for button in buttons2:
        button_text = button
        if not df.empty:
            if (df['user_id'] == user_id).any():
                if button in df.columns and df.loc[(df['user_id'] == user_id) & (df[button] == True)].shape[0] > 0:
                    button_text = button + ' ✓'
        markup.row(telebot.types.InlineKeyboardButton(button_text, callback_data=button))

    button_text = 'Поиск выключен ❌'
    if not df.empty:
        if (df['user_id'] == user_id).any():
            if df.loc[(df['user_id'] == user_id) & (df['notifications'] == True)].shape[0] > 0:
                button_text = 'Поиск включён ✅'
    markup.row(telebot.types.InlineKeyboardButton(button_text, callback_data='notifications'))
    
    return markup

def create_habr_url(row):
    global categories, dop
    base_url = "https://freelance.habr.com/tasks?"
    params = []
    params_dop = []
    
    for column in categories.keys():
        if row[column] == True:
            params.append(categories[column])

    for column in dop.keys():
        if row[column] == True:
            params_dop.append(dop[column])

    if params_dop:
        base_url += "".join(params_dop)
    
    if params:
        return base_url + "&categories=" + ",".join(params)
    else:
        return base_url

def update_button_status(user_id, button_name):
    global df
    
    if user_id not in df['user_id'].values:
        new_row = pd.Series([user_id] + [False] * (len(df.columns) - 1), index=df.columns).to_frame().T
        df = pd.concat([df, new_row], ignore_index=True)
    
    if button_name not in df.columns:
        df[button_name] = False
    
    current_status = df.loc[df['user_id'] == user_id, button_name].values[0]
    df.loc[df['user_id'] == user_id, button_name] = not current_status
    # Применение функции для каждой строки DataFrame
    df['habr_url'] = df.apply(create_habr_url, axis=1)
    df.to_csv(CSV_FILE, index=False)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    if not df.empty and (df['user_id'] == user_id).any():
        current_habr_url = df.loc[df['user_id'] == user_id, 'habr_url'].values[0]
    else:
        current_habr_url = 'https://freelance.habr.com/tasks?'
    reply_markup = create_buttons_from_files('categories.txt', 'dop.txt', user_id)
    bot.send_message(message.chat.id, f'Привет! Я бот, созданый, чтобы парсить Хабр фриланс по вашей индивидуальной ссылке. \n\nТекущая ссылка:{current_habr_url}\n\nВы можете выбрать нужные категории ниже, а я буду искать вакансии по ним и уведомлять, если найду новые.', reply_markup=reply_markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    user_id = call.from_user.id
    button_name = call.data
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    update_button_status(user_id, button_name)
    
    if button_name == 'notifications':
        if df.loc[df['user_id'] == user_id, 'notifications'].values[0]:
            bot.answer_callback_query(call.id, 'Уведомления включены')
        else:
            bot.answer_callback_query(call.id, 'Уведомления выключены')
    else:
        bot.answer_callback_query(call.id, 'Категория обновлена')
    
    reply_markup = create_buttons_from_files('categories.txt', 'dop.txt', user_id)
    bot.edit_message_text(chat_id=chat_id, message_id=message_id, text='Привет! Я бот, созданый, чтобы парсить Хабр фриланс по вашей индивидуальной ссылке.\n\nТекущая ссылка:' + df.loc[df['user_id'] == user_id, 'habr_url'].values[0] + '\n\nВы можете выбрать нужные категории ниже, а я буду искать вакансии по ним и уведомлять, если найду новые.', reply_markup=reply_markup)

bot.polling(none_stop=True)