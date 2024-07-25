import requests
import json
import pandas as pd

TOKEN = '6170182394:AAEs8LaBL2Dl4iJV-alGfmIF0H8oKV1w_UU'
BASE_URL = f'https://api.telegram.org/bot{TOKEN}'
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

def get_updates(offset=None):
    url = f'{BASE_URL}/getUpdates'
    params = {'timeout': 100, 'offset': offset}
    response = requests.get(url, params=params)
    return response.json()

def send_message(chat_id, text, reply_markup=None):
    url = f'{BASE_URL}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text, 'reply_markup': reply_markup}
    response = requests.post(url, json=payload)
    return response.json()

def send_message_only_text(chat_id, text):
    url = f'{BASE_URL}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    response = requests.post(url, json=payload)
    return response.json()

def edit_message_reply_markup(chat_id, message_id, reply_markup):
    url = f'{BASE_URL}/editMessageReplyMarkup'
    payload = {'chat_id': chat_id, 'message_id': message_id, 'reply_markup': reply_markup}
    response = requests.post(url, json=payload)
    return response.json()

def edit_message(chat_id, message_id, text, reply_markup):
    url = f'{BASE_URL}/editMessageText'
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'reply_markup': reply_markup
    }
    response = requests.post(url, json=payload)
    return response.json()

def create_buttons_from_files(file1, file2, user_id):
    with open(file1, 'r', encoding='utf-8') as f1, open(file2, 'r', encoding='utf-8') as f2:
        buttons1 = [line.strip().split(':')[0] for line in f1.readlines()]
        buttons2 = [line.strip().split(':')[0] for line in f2.readlines()]

    inline_keyboard = []
    
    # Add buttons from the first file in rows of 2
    for i in range(0, len(buttons1), 2):
        row = []
        for button in buttons1[i:i+2]:
            button_text = button
            if not df.empty:
                if (df['user_id'] == user_id).any():
                    if button in df.columns and df.loc[(df['user_id'] == user_id) & (df[button] == True)].shape[0] > 0:
                        button_text = button + ' ✓'
            row.append({'text': button_text, 'callback_data': button})
        inline_keyboard.append(row)
    
    # Add buttons from the second file, one per row
    for button in buttons2:
        button_text = button
        if not df.empty:
            if (df['user_id'] == user_id).any():
                if button in df.columns and df.loc[(df['user_id'] == user_id) & (df[button] == True)].shape[0] > 0:
                    button_text = button + ' ✓'
        inline_keyboard.append([{'text': button_text, 'callback_data': button}])

    if not df.empty:
        button_text = 'Поиск выключен ❌'
        if (df['user_id'] == user_id).any():
            if df.loc[(df['user_id'] == user_id) & (df['notifications'] == True)].shape[0] > 0:
                button_text = 'Поиск включён ✅'
        inline_keyboard.append([{'text': button_text, 'callback_data': 'notifications'}])
    
    reply_markup = {'inline_keyboard': inline_keyboard}
    return json.dumps(reply_markup)

# Функция для формирования habr_url
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
        new_row = pd.Series([user_id] + [False] * (len(df.columns) - 1), index=df.columns)
        df = pd.concat([df, new_row.to_frame().T], ignore_index=True)
    
    if button_name not in df.columns:
        df[button_name] = False
    
    current_status = df.loc[df['user_id'] == user_id, button_name].values[0]
    df.loc[df['user_id'] == user_id, button_name] = not current_status
    # Применение функции для каждой строки DataFrame
    df['habr_url'] = df.apply(create_habr_url, axis=1)
    df.to_csv(CSV_FILE, index=False)

def handle_updates(updates):
    global df
    for update in updates['result']:
        if 'message' in update:
            chat_id = update['message']['chat']['id']
            user_id = update['message']['from']['id']
            text = update['message'].get('text', '')
            
            if text.lower() == '/start':
                # Save the message_id when sending the initial message
                if not df.empty and (df['user_id'] == user_id).any():
                    current_habr_url = df.loc[df['user_id'] == user_id, 'habr_url'].values[0]
                else:
                    current_habr_url = 'https://freelance.habr.com/tasks?'
                response = send_message(chat_id, f'Привет! Я бот, созданый, чтобы парсить Хабр фриланс по вашей индивидуальной ссылке. \n\nТекущая ссылка:{current_habr_url}\n\nВы можете выбрать нужные категории ниже, а я буду искать вакансии по ним и уведомлять, если найду новые.', create_buttons_from_files('categories.txt', 'dop.txt', user_id))
            else:
                send_message_only_text(chat_id, 'Такой команды нет! \nВоспользуйтесь => /start')

def handle_callback_query(update):
    global df
    user_id = update['callback_query']['from']['id']
    button_name = update['callback_query']['data']
    chat_id = update['callback_query']['message']['chat']['id']
    message_id = update['callback_query']['message']['message_id']

    # Обновление состояния кнопки
    update_button_status(user_id, button_name)
    
    if not df.empty and (df['user_id'] == user_id).any():
        current_habr_url = df.loc[df['user_id'] == user_id, 'habr_url'].values[0]
    else:
        current_habr_url = 'https://freelance.habr.com/tasks?'
        
    # Создание и отправка обновленной клавиатуры
    reply_markup = create_buttons_from_files('categories.txt', 'dop.txt', user_id)
    text = f'Привет! Я бот, созданый, чтобы парсить Хабр фриланс по вашей индивидуальной ссылке. \n\nТекущая ссылка: {current_habr_url}\n\nВы можете выбрать нужные категории ниже, а я буду искать вакансии по ним и уведомлять, если найду новые.'
    edit_message(chat_id, message_id, text, reply_markup)
    # edit_message_reply_markup(chat_id, message_id, reply_markup)

def main():
    offset = None
    while True:
        updates = get_updates(offset)
        
        if 'result' in updates and updates['result']:
            handle_updates(updates)
            for update in updates['result']:
                if 'callback_query' in update:
                    handle_callback_query(update)
            offset = updates['result'][-1]['update_id'] + 1

if __name__ == '__main__':
    main()
