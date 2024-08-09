import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time

CSV_FILE = 'user_button_selections.csv'
TOKEN = '6170182394:AAEs8LaBL2Dl4iJV-alGfmIF0H8oKV1w_UU'
BASE_URL = f'https://api.telegram.org/bot{TOKEN}'

def send_message_only_text(chat_id, text):
    url = f'{BASE_URL}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    response = requests.post(url, json=payload)
    return response.json()

def fetch_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as err:
        return None

def parse_tasks(html):
    soup = BeautifulSoup(html, 'html.parser')
    tasks = soup.find_all('li', class_='content-list__item')

    task_data = []

    for task in tasks:
        title = task.find('div', class_='task__title').text.strip() if task.find('div', class_='task__title') else 'Название не найдено'
        responses = task.find('span', class_='params__responses').text.strip() if task.find('span', class_='params__responses') else 'Нет откликов'
        views = task.find('span', class_='params__views').text.strip() if task.find('span', class_='params__views') else 'Нет просмотров'
        time_posted = task.find('span', class_='params__published-at').text.strip() if task.find('span', class_='params__published-at') else 'Неизвестное время'
        price = task.find('div', class_='task__price').text.strip() if task.find('div', class_='task__price') else 'Цена не указана'
        link = task.find('a',)['href'] if task.find('a') else 'Ссылка не найдена'
        full_link = f"https://freelance.habr.com{link}" if link != 'Ссылка не найдена' else link

        task_data.append({
            'title': title,
            'responses': responses,
            'views': views,
            'time_posted': time_posted,
            'price': price,
            'link': full_link
        })

    return task_data

def sort_tasks(user_id, tasks):
    file_path = f'users_link/{user_id}.txt'
    with open(file_path, 'r') as f:
        existing_strings = f.readlines()
        existing_strings = [s.strip() for s in existing_strings]

    texts = []
    for task in tasks:
        nl = task['link']
        if nl not in existing_strings:
            with open(file_path, 'a') as f:
                f.write(nl + "\n")
            text = f"Название: {task['title']}\nОтклики: {task['responses']}\nПросмотры: {task['views']}\nВремя размещения: {task['time_posted']}\nЦена: {task['price']}\nСсылка: {task['link']}"
            texts.append(text)

    return texts

def main():
    df = pd.read_csv(CSV_FILE)
    # print(df['habr_url'])
    users_ids = df['user_id'].tolist()
    for i in users_ids:
        filename = f'users_link/{i}.txt'
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                pass  # Создаем пустой файл
        else:
            pass

    for i in users_ids:
        user_id = i

        notificaations_status = df.loc[df['user_id'] == int(user_id), 'notifications']
        if notificaations_status.iloc[0] == True:
            filtered_df = df.loc[df['user_id'] == int(user_id), 'habr_url']
            if not filtered_df.empty:
                habr_url = filtered_df.iloc[0]
            else:
                habr_url = ''

            if habr_url:
                content = fetch_url(habr_url)
                if not content:
                    return
                
                tasks = parse_tasks(content)
                if not tasks:
                    return
                tasks.reverse()
                if len(tasks) >= 5:
                    texts = sort_tasks(int(user_id), tasks)
                    for i in texts:  
                        send_message_only_text(int(user_id), i)
                        time.sleep(1)
                else:
                    texts = sort_tasks(int(user_id))
                    for i in texts:  
                        send_message_only_text(int(user_id), i)         
        else:
            pass


while True:
    main()
    time.sleep(10)
